"""Node manager."""

import ssl
import logging
import uuid
import json
import traceback
from threading import Semaphore

import paho.mqtt.client as mqtt

from beartype.typing import Callable

from .runtimes import RuntimeManager
from .types import Message, MQTTServer, Channel, RegistrationTimeout


class Manager(mqtt.Client):
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
        for i, rt in enumerate(self.runtimes):
            rt.bind_manager(self, i)
            self.subscribe_callback(
                rt.control_topic("control"),
                rt.handle_orchestrator_message, decode_json=True)
            self.register(
                rt.control_topic("reg"),
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

    def loop_runtime(self, rt_idx, rt: RuntimeManager) -> None:
        """Loop for a single runtime."""
        while True:
            msg = rt.receive(timeout=self.timeout)
            if msg is not None:
                rt.handle_runtime_message(rt, msg)

    def loop(self) -> None:
        """Main loop."""
        pass
        # Todo

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
            # Loopback
            for ch in self.matcher[channel.topic]:
                if ch is not channel:
                    self.runtimes[ch.runtime].send(
                        Message(ch.module, ch.fd, payload))
            # MQTT
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

    def subscribe_callback(
        self, topic: str, callback: Callable[[bytes], None],
    ) -> None:
        """Subscribe and create callback."""
        def _handler(client, userdata, msg):
            try:
                return callback(msg.payload)
            except Exception as e:
                self.log.error("Uncaught exception: {}".format(e))
                self.log.error(traceback.format_exc())

        self.subscribe(topic)
        self.message_callback_add(topic, _handler)
