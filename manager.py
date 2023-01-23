"""Node manager."""

import logging
from threading import Semaphore
import uuid
import ssl
import paho.mqtt.client as mqtt
import json

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
    """Silverline node manager."""

    def __init__(
        self, runtimes: dict[str, BaseRuntime], name: str = "manager",
        realm: str = "realm", server: MQTTServer = MQTTServer(
            host="localhost", port=1883, user="cli", pwd="", ssl=False)
    ) -> None:
        self.log = logging.getLogger('manager')
        self.realm = realm

        # Append a UUID here since client_id must be unique.
        # If this is not added, MQTT will disconnect with rc=7
        # (Connection Refused: unknown reason.)
        self.name = "{}:{}".format(name, uuid.uuid4())
        super().__init__(client_id=self.name)

        self.connect(server)

        for rtid, rt in self.runtimes.items():
            self.control_message("reg/{}".format(rtid), "create", rt.start())

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
        self.connect(server.host, server.port, 60)

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

    def control_message(self, topic: str, action: str, payload: dict) -> None:
        """Send control message to the orchestrator."""
        self.publish("{}/proc/{}".format(self.realm, topic), json.dumps({
            "object_id": str(uuid.uuid4()),
            "action": action,
            "type": "arts_req",
            "data": payload
        }))
