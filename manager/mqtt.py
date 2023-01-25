"""MQTT Client Interface."""

import ssl
import logging
from threading import Semaphore
import paho.mqtt.client as mqtt

from beartype.typing import NamedTuple

from .runtime import BaseRuntime, Message


class MQTTServer(NamedTuple):
    """MQTT login."""

    host: str
    port: int
    user: str
    pwd: str
    ssl: bool


class Channel(NamedTuple):
    """Channel."""

    runtime: int
    module: int
    fd: int
    topic: str


class RegistrationTimeout(Exception):
    """Error raised when registration times out."""

    pass


class MQTTClient(mqtt.Client):
    """Silverline MQTT Client and channels interface.

    Parameters
    ----------
    runtimes: input runtimes to forward messages to.
    client_id: ID to use for MQTTClient; must be unique.
    """

    def __init__(
        self, runtimes: list[BaseRuntime], client_id: str = "manager"
    ) -> None:
        super().__init__(client_id=client_id)
        self.log = logging.getLogger('mqtt')

        self.runtimes = runtimes

        self.matcher = mqtt.MQTTMatcher()
        self.channels = {}

    def connect(self, server: MQTTServer) -> None:
        """Connect to MQTT server."""
        semaphore = Semaphore()
        semaphore.acquire()

        def _on_connect(mqttc, obj, flags, rc):
            semaphore.release()

        self.on_connect = _on_connect

        # We handle loopback internally.
        self.enable_bridge_mode()

        self.log.info("Connecting MQTT client: {}".format(self._client_id))
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
        semaphore.acquire()
        self.log.info("Connected to MQTT server.")

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.log.error("Disconnected: rc={} ({})".format(
            rc, mqtt.connack_string(rc)))

    def register(
            self, topic: str, msg: str, timeout: float = 5.,
            allow_fail: bool = False) -> bool:
        """Blocking registration.

        Parameters
        ----------
        topic: MQTT topic.
        msg: Message payload in final encoded form.
        timeout: Registration timeout.
        allow_fail: If False, raises RegistrationTimeout on failure.

        Returns
        -------
        True if registered successfully, False if timed out.
        """
        self.subscribe(topic)

        sem = Semaphore()
        sem.acquire()

        def _handler(client, userdata, msg, sem=sem, topic=topic):
            sem.release()

        self.message_callback_add(topic, _handler)
        self.publish(topic, msg)

        res = sem.acquire(timeout=timeout)
        if not allow_fail and not res:
            raise RegistrationTimeout(
                "Registration timed out on {}.".format(topic))
        self.message_callback_remove(topic)
        self.unsubscribe(topic)
        return res

    def _err_nonexistent(self, action, runtime, module, fd):
        self.log.error("Tried to {} nonexisting channel: {}/{}/{}".format(
            action, runtime, module, fd))

    def channel_open(
            self, runtime: int, module: int, fd: int, topic: str) -> None:
        """Open channel.

        Parameters
        ----------
        runtime: runtime index.
        module: module index on this runtime.
        fd: channel index on this module.
        topic: MQTT topic string.
        """
        if runtime not in self.channels:
            self.channels[runtime] = {}
        if module not in self.channels[runtime]:
            self.channels[runtime][module] = {}
        self.channels[runtime][module][fd] = topic

        channel = Channel(runtime, module, fd, topic)
        try:
            self.matcher[topic].add(channel)
        except KeyError:
            self.matcher[topic] = {channel}
            self.subscribe(topic)

    def channel_close(self, runtime: int, module: int, fd: int) -> None:
        """Close channel.

        Parameters
        ----------
        runtime: runtime index.
        module: module index on this runtime.
        fd: channel index on this module.
        """
        try:
            channel = self.channels[runtime][module][fd]

            subscribed = self.matcher[channel.topic]
            if channel in subscribed:
                subscribed.remove(channel)

            if len(subscribed) == 0:
                self.unsubscribe(channel)
                del self.matcher[channel.topic]
        except KeyError:
            self._err_nonexistent("close", runtime, module, fd)

    def channel_publish(
            self, runtime: int, module: int, fd: int, payload: bytes) -> None:
        """Publish message.

        Parameters
        ----------
        runtime: Runtime index.
        module: Module index on this runtime.
        fd: Channel index on this module.
        payload: Message payload.
        """
        try:
            channel = self.channels[runtime][module][fd]
            self.publish(channel.topic, payload)
        except KeyError:
            self._err_nonexistent("publish to", runtime, module, fd)

    def on_message(self, client, userdata, msg):
        """Handle message.

        Messages are dispatched to runtimes with corresponding open channels.
        """
        try:
            matches = self.matcher[msg.topic]
            self.log.debug("Handling message with {} matches @ {}".format(
                msg.topic, len(matches)))
            for match in matches:
                self.runtimes[match.runtime].send(
                    Message(match.module, match.fd, msg.payload))
        except KeyError:
            self.log.error(
                "Received message to topic without active channel: {}. Was"
                "the channel unsubscribed from?".format(msg.topic))
