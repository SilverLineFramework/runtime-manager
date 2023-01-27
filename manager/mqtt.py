"""SilverLine communications interface."""

import ssl
import uuid
import json
import traceback
from threading import Semaphore

import paho.mqtt.client as mqtt

from beartype.typing import Callable

from .types import MQTTServer, Channel, Message


class MQTTClient(mqtt.Client):
    """MQTT (and channels) interface."""

    def on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.log.info("Disconnected: rc={} ({})".format(
            rc, mqtt.connack_string(rc)))

    def subscribe_callback(
        self, topic: str, callback: Callable[[bytes], None], decode_json=False,
    ) -> None:
        """Subscribe and create callback."""
        def _handler(client, userdata, msg):
            try:
                return callback(
                    json.loads(msg.payload) if decode_json else msg.payload)
            except json.JSONDecodeError:
                self.log.error("Invalid json: {}".format(msg.payload))
            except Exception as e:
                self.log.error("Uncaught exception: {}".format(e))
                self.log.error(traceback.format_exc())

        self.subscribe(topic)
        self.message_callback_add(topic, _handler)

    def connect(self, server: MQTTServer) -> None:
        """Connect to MQTT server."""
        semaphore = Semaphore()
        semaphore.acquire()

        def _on_connect(mqttc, obj, flags, rc):
            semaphore.release()

        self.on_connect = _on_connect

        # We handle loopback internally.
        self.enable_bridge_mode()

        self.log.info(
            "Connecting MQTT client: {}:{}".format(self.name, self.uuid))
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

            subscribed = self.matcher[channel]
            if channel in subscribed:
                subscribed.remove(channel)

            if len(subscribed) == 0:
                self.unsubscribe(channel)
                del self.matcher[channel.topic]
        except KeyError:
            self._err_nonexistent("close", runtime, module, fd)

    def channel_cleanup(self, runtime: int, module: int) -> None:
        """Cleanup all channels associated with a module.

        Parameters
        ----------
        runtime: runtime index.
        module: module index on this runtime.
        """
        try:
            for fd in self.channels[runtime][module]:
                self.channel_close(runtime, module, fd)
            del self.channels[runtime][module]
        except KeyError:
            self.log.error("Invalid module: {}.{}".format(runtime, module))

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
            # Loopback
            for ch in self.matcher[channel]:
                if ch.runtime != runtime and ch.module != module:
                    self.runtimes[ch.runtime].send(
                        Message(ch.module, ch.fd, payload))
            # MQTT
            self.publish(channel, payload)
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

    def register(self, topic: str, msg: str, timeout: float = 5.) -> None:
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
