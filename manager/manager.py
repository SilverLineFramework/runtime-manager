"""Node manager."""

import logging
from threading import Semaphore, Thread
import uuid
import ssl
import json

import paho.mqtt.client as mqtt

from beartype.typing import NamedTuple

from .runtime import BaseRuntime


class MQTTServer(NamedTuple):
    """MQTT login."""

    host: str
    port: int
    user: str
    pwd: str
    ssl: bool


class Manager(mqtt.Client):
    """Silverline node manager.

    NOTE: blocks on initialization until the client connects, and all runtimes
    are registered.
    """

    def __init__(
        self, runtimes: dict[str, BaseRuntime], name: str = "manager",
        realm: str = "realm", server: MQTTServer = MQTTServer(
            host="localhost", port=1883, user="cli", pwd="", ssl=False),
        registration_timeout=5.
    ) -> None:
        self.log = logging.getLogger('manager')
        self.realm = realm
        self.runtimes = runtimes

        # Append a UUID here since client_id must be unique.
        # If this is not added, MQTT will disconnect with rc=7
        # (Connection Refused: unknown reason.)
        self.name = "{}:{}".format(name, uuid.uuid4())
        super().__init__(client_id=self.name)

        # TODO: need to set the will.
        self.will_set(self.control_topic("mgr"), payload={"todo": None}, qos=2)

        self.connect(server)
        self.register_runtimes(runtimes, timeout=registration_timeout)

    def register(self, rtid: str, rt: BaseRuntime):
        """Register runtime with orchestrator."""
        reg_topic = self.control_topic("reg", rtid)
        self.subscribe(reg_topic)

        sem = Semaphore()
        sem.acquire()

        def _handler(client, userdata, msg, sem=sem, reg_topic=reg_topic):
            sem.release()
            self.unsubscribe(reg_topic)

        self.message_callback_add(reg_topic, _handler)
        msg = rt.start()
        self.control_message("reg", rtid, "create", msg)
        sem.acquire()

    def register_runtimes(self, runtimes, timeout=5.):
        """Register runtimes."""
        self.log.info("Registering {} runtimes...".format(len(runtimes)))
        threads = {
            rtid: Thread(target=self.register, args=[rtid, rt])
            for rtid, rt in runtimes.items()}
        for t in threads.values():
            t.start()
        for rtid, thread in threads.items():
            thread.join(timeout=timeout)
            if thread.is_alive():
                self.log.error("Timeout on registration: {}".format(rtid))
            else:
                self.log.info("Registered: {}".format(rtid))
        self.log.info("Done registering.")

    def connect(self, server: MQTTServer) -> None:
        """Connect to MQTT server; blocks until connected."""
        self.semaphore = Semaphore()
        self.semaphore.acquire()

        # We handle loopback internally.
        self.enable_bridge_mode()

        self.log.info("Connecting with MQTT client: {}".format(self.name))
        self.log.info("SSL: {}".format(server.ssl))
        self.log.info("Username: {}".format(server.user))
        try:
            self.log.info("Password file: {}".format(server.pwd))
            with open(server.pwd, 'r') as f:
                passwd = f.read().rstrip('\n')
        except FileNotFoundError:
            passwd = ""
            self.log.warn("No password supplied; using an empty password.")

        self.username_pw_set(server.user, passwd)
        if server.ssl:
            self.tls_set(cert_reqs=ssl.CERT_NONE)
        super().connect(server.host, server.port, 60)

        # Waiting for on_connect to release
        self.loop_start()
        self.semaphore.acquire()

    def on_connect(self, mqttc, obj, flags, rc):
        """On connect callback: register handlers, release main thread."""
        if self.semaphore is not None:
            self.semaphore.release()
        self.log.info("Connected to MQTT server.")

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.log.error("Disconnected: rc={} ({})".format(
            rc, mqtt.connack_string(rc)))

    def on_message(self, client, userdata, message):
        """Subscribed message handler."""
        self.log.warn(
            "Message arrived topic without handler (should be "
            "impossible!): {}".format(message.topic))

    def control_message(
            self, topic: str, rtid: str, action: str, payload: dict) -> None:
        """Send control message to the orchestrator."""
        self.publish(self.control_topic(topic, rtid), json.dumps({
            "object_id": str(uuid.uuid4()),
            "action": action,
            "type": "arts_req",
            "data": payload
        }))

    def control_topic(self, topic: str, rtid: str) -> None:
        """Format control topic."""
        # Todo: add .../* to the orchestrator.
        # return "{}/proc/{}/{}".format(self.realm, topic, rtid)
        return "{}/proc/{}".format(self.realm, topic)
