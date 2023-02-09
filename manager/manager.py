"""Node manager."""

import logging
import uuid
import ssl
import json
from threading import Semaphore

import paho.mqtt.client as mqtt

from beartype import beartype

from .runtime import RuntimeManager
from .types import MQTTServer
from .channels import ChannelManager
from . import exceptions


@beartype
class Manager(mqtt.Client):
    """Silverline node manager.

    Parameters
    ----------
    runtimes: runtimes to manage.
    name: manager short name.
    mgr_id: manager UUID.
    realm: SilverLine realm.
    timeout: Timeout duration (seconds).
    server: MQTT server parameters.
    """

    _BANNER = r"""
      ___ _                 
     / __(_)_ _ _ _ _  _ ___
    | (__| | '_| '_| || (_-<
     \___|_|_| |_|  \_,_/__/
    SilverLine  Node Manager
    """

    def __init__(
        self, runtimes: list[RuntimeManager], name: str = "manager",
        mgr_id: str = None, realm: str = "realm", timeout: float = 5.
    ) -> None:
        self.log = logging.getLogger('mgr')
        self.log_mq = logging.getLogger('mq')
        self.realm = realm
        self.runtimes = runtimes
        self.timeout = timeout

        self.uuid = str(uuid.uuid4()) if mgr_id is None else mgr_id
        self.name = name

        # Append a UUID here since client_id must be unique.
        # If this is not added, MQTT will disconnect with rc=7
        # (Connection Refused: unknown reason.)
        super().__init__(client_id="{}:{}".format(self.name, self.uuid))

        self.channels = ChannelManager(self)

        super().__init__()

    def start(
        self, server: MQTTServer = MQTTServer(
            host="localhost", port=1883, user="cli", pwd="", ssl=False)
    ) -> None:
        """Connect manager."""
        print(self._BANNER)

        metadata = {"type": "manager", "uuid": self.uuid, "name": self.name}
        self.will_set(
            self.control_topic("reg", self.uuid), qos=2,
            payload=self.control_message("delete", metadata))
        self.connect(server)

        self.log.info("Registering manager...")
        self._register(
            self.control_topic("reg", self.uuid),
            self.control_message("create", metadata), timeout=self.timeout)
        self.log.info("Manager registered.")

        self.log.info("Registering {} runtimes.".format(len(self.runtimes)))
        for i, rt in enumerate(self.runtimes):
            rt.bind_manager(self, i)
            topic = rt.control_topic("control")
            self.subscribe(topic)
            self.message_callback_add(topic, rt.on_mqtt_message)
            metadata = rt.start()
            metadata["parent"] = self.uuid
            self._register(
                rt.control_topic("reg"),
                self.control_message("create", metadata), timeout=self.timeout)
            rt.loop_start()
            self.log.info("Registered: {}:{}".format(rt.name, rt.rtid))

        self.log.info("Done registering runtimes.")

    def stop(self):
        """Stop manager."""
        for rt in self.runtimes:
            rt.loop_stop()

        self.loop_stop()
        self.disconnect()

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.log_mq.info("Disconnected: rc={} ({})".format(
            rc, mqtt.connack_string(rc)))

    def connect(self, server: MQTTServer) -> None:
        """Connect to MQTT server."""
        semaphore = Semaphore()
        semaphore.acquire()

        def _on_connect(mqttc, obj, flags, rc):
            semaphore.release()

        self.on_connect = _on_connect

        # We handle loopback internally.
        self.enable_bridge_mode()

        self.log_mq.info(
            "Connecting MQTT client: {}:{}".format(self.name, self.uuid))
        self.log_mq.info("SSL: {}".format(server.ssl))
        self.log_mq.info("Username: {}".format(server.user))
        try:
            self.log_mq.info("Password file: {}".format(server.pwd))
            with open(server.pwd, 'r') as f:
                passwd = f.read().rstrip('\n')
        except FileNotFoundError:
            passwd = ""
            self.log_mq.warn("No password supplied; using an empty password.")

        self.username_pw_set(server.user, passwd)
        if server.ssl:
            self.tls_set(cert_reqs=ssl.CERT_NONE)
        super().connect(server.host, server.port, 60)

        # Waiting for on_connect to release
        self.loop_start()
        semaphore.acquire()
        self.log_mq.info("Connected to MQTT server.")

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
            "type": "arts_req",
            "data": payload
        })

    def control_topic(self, topic: str, *ids: str) -> str:
        """Format control topic."""
        return "{}/proc/{}/{}".format(self.realm, topic, "/".join(ids))

    def _register(self, topic: str, msg: str, timeout: float = 5.) -> None:
        """Blocking registration.

        Parameters
        ----------
        topic: MQTT topic.
        msg: Message payload in final encoded form.
        timeout: Registration timeout.
        """
        self.subscribe(topic)

        sem = Semaphore()
        sem.acquire()

        def _handler(client, userdata, msg, sem=sem, topic=topic):
            sem.release()

        self.message_callback_add(topic, _handler)
        self.publish(topic, msg)

        if not sem.acquire(timeout=timeout):
            self.log.error("Registration timed out on {}.".format(topic))
        self.message_callback_remove(topic)
        self.unsubscribe(topic)
