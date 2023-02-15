"""Node manager."""

import logging
import uuid
import json
from threading import Semaphore

import paho.mqtt.client as mqtt

from beartype import beartype
from beartype.typing import Optional

from common.mqtt import MQTTClient, MQTTServer
from .runtime import RuntimeManager
from .channels import ChannelManager
from . import exceptions


@beartype
class Manager(MQTTClient):
    """Silverline node manager (Cirrus).

    The node manager is a thin layer that operates at a high level -- just like
    a cirrus cloud.

    Parameters
    ----------
    runtimes: runtimes to manage.
    name: manager short name.
    mgr_id: manager UUID.
    realm: Silverline realm.
    timeout: Timeout duration (seconds).
    """

    _BANNER = r"""
      ___ _
     / __(_)_ _ _ _ _  _ ___
    | (__| | '_| '_| || (_-<
     \___|_|_| |_|  \_,_/__/
    Silverline: Node Manager
    """

    def __init__(
        self, runtimes: list[RuntimeManager], name: str = "manager",
        mgr_id: str = None, realm: str = "realm", timeout: float = 5.
    ) -> None:
        self.log = logging.getLogger('mgr')

        self.realm = realm
        self.runtimes = runtimes
        self.timeout = timeout

        self.uuid = str(uuid.uuid4()) if mgr_id is None else mgr_id
        self.name = name
        self.metadata = {
            "type": "manager", "uuid": self.uuid, "name": self.name}
        self.channels = ChannelManager(self)

        # Append a UUID here since client_id must be unique.
        # If this is not added, MQTT will disconnect with rc=7
        # (Connection Refused: unknown reason.)
        super().__init__(client_id="{}:{}".format(self.name, self.uuid))

    def start(
        self, server: Optional[MQTTServer] = None
    ) -> None:
        """Connect manager."""
        print(self._BANNER)

        # We handle loopback internally; must be called before connect!
        self.enable_bridge_mode()

        self.will_set(
            self.control_topic("reg", self.uuid), qos=2,
            payload=self.control_message("delete", self.metadata))
        self.connect(server)

        self.log.info("Registering manager...")
        self._register(
            self.control_topic("reg", self.uuid),
            self.control_message("create", self.metadata))
        self.log.info("Manager registered.")

        self.log.info("Registering {} runtimes.".format(len(self.runtimes)))
        for i, rt in enumerate(self.runtimes):
            rt._start(self, i)

        self.log.info("Initialization complete.")
        print()  # empty line after initialization

    def stop(self):
        """Stop manager."""
        self.log.info("Stopping runtimes...")
        for rt in self.runtimes:
            rt.stop()
            rt.loop_stop()

        self.publish(
            self.control_topic("reg", self.uuid),
            self.control_message("delete", self.metadata), qos=2)
        self.loop_stop()
        self.disconnect()
        self.log.info("Manager and runtime(s) stopped.")

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.log.info("Disconnected: rc={} ({})".format(
            rc, mqtt.connack_string(rc)))

    def on_message(self, client, userdata, msg):
        """Handle message.

        Messages are dispatched to runtimes with corresponding open channels.
        """
        self.log.debug("Handling message @ {}".format(msg.topic))
        try:
            self.channels.handle_message(msg.topic, msg.payload)
        except Exception as e:
            exceptions.handle_error(e, self.log, msg.topic)

    def control_message(self, action: str, payload: dict) -> str:
        """Format control message to the orchestrator."""
        return json.dumps({
            "object_id": str(uuid.uuid4()),
            "action": action,
            "type": "req",
            "data": payload
        })

    def control_topic(self, topic: str, *ids: str) -> str:
        """Format control topic."""
        return "{}/proc/{}/{}".format(self.realm, topic, "/".join(ids))

    def _register(self, topic: str, msg: str) -> None:
        """Blocking registration.

        Parameters
        ----------
        topic: MQTT topic.
        msg: Message payload in final encoded form.
        """
        self.subscribe(topic)

        sem = Semaphore()
        sem.acquire()

        def _handler(client, userdata, msg, sem=sem, topic=topic):
            sem.release()

        self.message_callback_add(topic, _handler)
        self.publish(topic, msg)

        if not sem.acquire(timeout=self.timeout):
            self.log.error("Registration timed out on {}.".format(topic))
        self.message_callback_remove(topic)
        self.unsubscribe(topic)
