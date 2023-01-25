"""Node manager."""

import logging
import uuid
import json
import paho.mqtt.client as mqtt


from .runtime import RuntimeManager, Message
from .mqtt import MQTTServer, MQTTClient


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

    def connect(
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
        for rt in self.runtimes:
            self.subscribe_callback(
                self.control_topic("control", rt.rtid),
                rt.handle_control_message, decode_json=True)
            self.register(
                self.control_topic("reg", rt.rtid),
                self.control_message("create", rt.start()),
                timeout=self.timeout)
            self.log.info("Registered: {}".format(rt.rtid))
        self.log.info("Done registering runtimes.")

    def disconnect(self):
        """Disconnect manager."""
        self.disconnect()
        self.loop_stop()

    def control_message(self, action: str, payload: dict) -> None:
        """Format control message to the orchestrator."""
        return json.dumps({
            "object_id": str(uuid.uuid4()),
            "action": action,
            "type": "arts_req",
            "data": payload
        })

    def control_topic(self, topic: str, *ids: list[str]) -> None:
        """Format control topic."""
        return "{}/proc/{}/{}".format(self.realm, topic, "/".join(ids))

    def handle_runtime_message(self, rt: RuntimeManager, msg: Message) -> None:
        """Handle message for a single runtime."""
        # Module Exited
        if msg.h1 == 0x80:
            self.publish(
                self.control_topic("control", rt.rtid),
                self.control_message("delete", {
                    "type": "module", "uuid": rt.rtid,
                    "reason": json.load(msg.payload)}))
        # Runtime Keepalive
        elif msg.h1 == 0x81:
            self.publish(
                self.control_topic("keepalive", rt.rtid),
                self.control_message("update", {
                    "type": "runtime", "uuid": rt.rtid,
                    "name": rt.name, **json.load(msg.payload)
                }))
        # Runtime Log
        elif msg.h1 == 0x82:
            self.publish(self.control_topic("log", rt.rtid), msg.payload)
        # Module related
        else:
            # Open Channel
            if msg.h2 == 0x80:
                self.channel_open(
                    rt.index, msg.h1, int(msg.payload[0]), msg.payload[1:])
            # Close Channel
            elif msg.h2 == 0x81:
                self.channel_close(rt.index, msg.h1, int(msg.payload[0]))
            # Logging Message
            elif msg.h2 == 0x82:
                self.publish(
                    self.control_topic(
                        "log", rt.rtid, rt.modules[msg.h1]['uuid']),
                    msg.payload)
            elif msg.h2 == 0x83:
                self.publish(
                    self.control_topic(
                        "profile", rt.rtid, rt.modules[msg.h1]['uuid']),
                    msg.payload)
            else:
                self.mqtt.channel_publish(
                    rt.index, msg.h1, msg.h2, msg.payload)

    def loop_runtime(self, rt_idx, rt: RuntimeManager) -> None:
        """Loop for a single runtime."""
        while True:
            msg = rt.receive(timeout=self.timeout)
            if msg is not None:
                self.handle_runtime_message(rt, msg)

    def loop(self) -> None:
        """Main loop."""
        pass
