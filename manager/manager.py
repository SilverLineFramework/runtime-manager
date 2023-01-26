"""Node manager."""

import logging
import uuid
from threading import Semaphore

import paho.mqtt.client as mqtt

from .runtimes import RuntimeManager
from .mqtt import MQTTClient
from .types import MQTTServer


class Manager(MQTTClient):
    """Silverline node manager.

    NOTE: blocks on initialization until the client connects, and all runtimes
    are registered.

    Parameters
    ----------
    runtimes: runtimes to manage.
    name: manager short name.
    mgr_id: manager UUID.
    realm: SilverLine realm.
    timeout: Timeout duration (seconds).
    server: MQTT server parameters.
    """

    def __init__(
        self, runtimes: list[RuntimeManager], name: str = "manager",
        mgr_id: str = None, realm: str = "realm", timeout: float = 5.
    ) -> None:
        self.log = logging.getLogger('manager')
        self.realm = realm
        self.runtimes = runtimes
        self.timeout = timeout

        self.uuid = str(uuid.uuid4()) if mgr_id is None else mgr_id
        self.name = name

        # Append a UUID here since client_id must be unique.
        # If this is not added, MQTT will disconnect with rc=7
        # (Connection Refused: unknown reason.)
        super().__init__(client_id="{}:{}".format(self.name, self.uuid))
        self.log = logging.getLogger('mqtt')

        self.matcher = mqtt.MQTTMatcher()
        self.channels = {}

        super().__init__()

    def start(
        self, server: MQTTServer = MQTTServer(
            host="localhost", port=1883, user="cli", pwd="", ssl=False)
    ) -> None:
        """Connect manager."""
        metadata = {"type": "manager", "uuid": self.uuid, "name": self.name}
        self.will_set(
            self.control_topic("reg", self.uuid), qos=2,
            payload=self.control_message("delete", metadata))
        self.connect(server)

        self.log.info("Registering manager...")
        self.register(
            self.control_topic("reg", self.uuid),
            self.control_message("create", metadata), timeout=self.timeout)
        self.log.info("Manager registered.")

        self.log.info("Registering {} runtimes.".format(len(self.runtimes)))
        for i, rt in enumerate(self.runtimes):
            rt.bind_manager(self, i)
            self.subscribe_callback(
                rt.control_topic("control"),
                rt.handle_orchestrator_message, decode_json=True)
            self.register(
                rt.control_topic("reg"),
                self.control_message("create", rt.start()),
                timeout=self.timeout)
            rt.loop_start()
            self.log.info("Registered: {}:{}".format(rt.name, rt.rtid))

        self.log.info("Done registering runtimes.")

    def stop(self):
        """Stop manager."""
        for rt in self.runtimes:
            rt.loop_stop()

        self.loop_stop()
        self.disconnect()
