"""MQTT client wrapper."""

import logging
import ssl
import json
import uuid
import os
from threading import Semaphore
import argparse

import paho.mqtt.client as mqtt

from beartype import beartype
from beartype.typing import NamedTuple, Optional, Union


@beartype
class MQTTServer(NamedTuple):
    """MQTT server and login information.

    Attributes
    ----------
    host: MQTT server web address.
    port: Server port number (usually 1883 or 8883 if using SSL).
    user: Username.
    pwd: Password.
    ssl: Whether server has TLS/SSL enabled.
    realm: MQTT topic realm prefix.
    """

    host: str
    port: int
    user: str
    pwd: str
    ssl: bool
    realm: str

    @classmethod
    def from_config(cls, cfg: Union[str, dict]):
        """Load settings from configuration file or dict."""
        if isinstance(cfg, str):
            with open(cfg) as f:
                cfg = json.load(f)
        return cls(
            host=cfg.get("mqtt", "localhost"),
            port=cfg.get("mqtt_port", 1883),
            user=cfg.get("mqtt_username", "cli"),
            pwd=cfg.get("pwd", ""),
            ssl=cfg.get("use_ssl", False),
            realm=cfg.get("realm", "realm"))

    @staticmethod
    def make_args(p: argparse.ArgumentParser) -> None:
        """Add MQTTServer to argument parser."""
        g = p.add_argument_group(title="MQTT")
        g.add_argument(
            "--mqtt", default="localhost",
            help="MQTT server address and port.")
        g.add_argument(
            "--mqtt_pwd", default="../mqtt_pwd.txt",
            help="Path to MQTT password file.")
        g.add_argument("--mqtt_user", default="cli", help="MQTT username.")
        g.add_argument("--realm", default="realm", help="Realm topic prefix.")

    @staticmethod
    def make_config(args: argparse.Namespace) -> dict:
        """Get config from argparse parsed args."""
        return {
            "mqtt": args.mqtt.split(":")[-1],
            "mqtt_port": 8883 if args.mqtt.startswith("ssl:") else 1883,
            "use_ssl": args.mqtt.startswith("ssl:"),
            "mqtt_username": args.mqtt_user,
            "pwd": os.path.abspath(os.path.expanduser((args.mqtt_pwd))),
            "realm": args.realm
        }


@beartype
class MQTTClient(mqtt.Client):
    """MQTT Client wrapper.

    Parameters
    ----------
    client_id: client ID.
    server: MQTT broker information. Uses default (localhost:1883, no security)
        if None.
    bridge: whether MQTT client should be in bridge mode (bridge mode: broker
        doesn't return messages sent by this client even if subscribed)
    """

    def __init__(
        self, client_id: str = "client", server: Optional[MQTTServer] = None,
        bridge: bool = False
    ) -> None:
        super().__init__(client_id=client_id)
        self.__log = logging.getLogger('mq')
        self.client_id = client_id
        self.server = MQTTServer.from_config({}) if server is None else server

        if bridge:
            self.enable_bridge_mode()

    def start(self) -> "MQTTClient":
        """Connect to MQTT server; blocks until connected."""
        semaphore = Semaphore()
        semaphore.acquire()

        def _on_connect(mqttc, obj, flags, rc):
            semaphore.release()

        self.on_connect = _on_connect

        self.__log.info("Connecting MQTT client: {}".format(self.client_id))
        self.__log.info("Server: {}:{} (ssl={})".format(
            self.server.host, self.server.port, self.server.ssl))
        self.__log.debug("Username: {}".format(self.server.user))
        try:
            self.__log.debug("Password file: {}".format(self.server.pwd))
            with open(self.server.pwd, 'r') as f:
                passwd = f.read().rstrip('\n')
        except FileNotFoundError:
            passwd = ""
            self.__log.warn("No password provided; using an empty password.")

        self.username_pw_set(self.server.user, passwd)
        if self.server.ssl:
            self.tls_set(cert_reqs=ssl.CERT_NONE)
        self.connect(self.server.host, self.server.port, 60)

        # Waiting for on_connect to release
        self.loop_start()
        semaphore.acquire()
        self.__log.info("Connected to MQTT server.")

        return self

    def stop(self) -> "MQTTClient":
        """Disconnect and stop main loop."""
        self.loop_stop()
        self.disconnect()

        return self

    @staticmethod
    def control_message(action: str, payload: dict) -> str:
        """Format control message to the orchestrator."""
        return json.dumps({
            "object_id": str(uuid.uuid4()),
            "action": action,
            "type": "req",
            "data": payload
        })

    def control_topic(self, *topic: str) -> str:
        """Format control topic in the form ``{realm}/proc/{...}``."""
        return "{}/proc/{}".format(self.server.realm, "/".join(topic))

    def run_until_stop(self) -> None:
        """Wait for KeyboardInterrupt or `q`/`quit` to trigger exit."""
        try:
            while True:
                if input() in {'q', 'quit', 'exit'}:
                    break
        except KeyboardInterrupt:
            print("  Exiting due to KeyboardInterrupt.\n")

        self.stop()
