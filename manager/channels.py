"""Channels interface."""

import logging
import paho.mqtt.client as mqtt
from beartype import beartype

from libsilverline import format_message, Message, Flags, Channel
from . import exceptions


@beartype
class ChannelManager:
    """Channel manager.

    Attributes
    ----------
    matcher: mqtt.MQTTMatcher
        Dictionary-like object that fetches sets of subscribed channels for a
        topic string.
    channels: dict
        Channel lookup table with runtime, module, and fd levels.
    """

    def __init__(self, mgr):

        self.mgr = mgr
        self.log = logging.getLogger("ch")
        self.matcher = mqtt.MQTTMatcher()
        self.channels = {}

    def open(
        self, runtime: int, module: int, fd: int, topic: bytes, flags: int
    ) -> None:
        """Open channel."""
        if runtime not in self.channels:
            self.channels[runtime] = {}
        if module not in self.channels[runtime]:
            self.channels[runtime][module] = {}

        if fd in self.channels[runtime][module]:
            raise exceptions.ChannelException(
                "Tried to open already-existing channel")

        # Handle standard translation
        topic_str = topic.rstrip(b'\0').decode('utf-8')
        if topic_str.startswith("$SL/"):
            _uuid = self.mgr.runtimes[runtime].modules.uuid(module)
            topic_str = "/".join(
                [self.mgr.server.realm, topic_str.lstrip("$SL/"), _uuid])

        # Check for wildcards
        if (flags | Flags.write) != 0:
            if '+' in topic_str or '#' in topic_str:
                raise exceptions.ChannelException(
                    "Channel topic name cannot contain a wildcard ('+', '#') "
                    "in write or read-write mode: {}".format(topic_str))

        ch = Channel(
            runtime=runtime, module=module, fd=fd, topic=topic_str,
            flags=flags)

        # Requires subscribing
        if (flags | Flags.read) != 0:
            try:
                self.matcher[topic_str].add(ch)
            except KeyError:
                self.mgr.subscribe(topic_str)
                self.matcher[topic_str] = {ch}

        self.log.debug("Opened channel: {} (flags=x{:02x})".format(
            topic.decode('utf-8'), flags))
        self.channels[runtime][module][fd] = ch

    def close(self, runtime: int, module: int, fd: int) -> None:
        """Close channel.

        Parameters
        ----------
        runtime: runtime index.
        module: module index on this runtime.
        fd: channel index on this module.
        """
        try:
            channel = self.channels[runtime][module][fd]
        except KeyError:
            raise exceptions.ChannelException(
                "Tried to close nonexisting channel.")

        del self.channels[runtime][module][fd]

        if channel.flags | Flags.read:
            subscribed = self.matcher[channel.topic]
            if channel in subscribed:
                subscribed.remove(channel)
            if len(subscribed) == 0:
                self.mgr.unsubscribe(channel.topic)
                del self.matcher[channel.topic]

    def cleanup(self, runtime: int, module: int) -> None:
        """Cleanup all channels associated with a module.

        Parameters
        ----------
        runtime: runtime index.
        module: module index on this runtime.
        """
        try:
            fds = list(self.channels[runtime][module].keys())
            for fd in fds:
                self.close(runtime, module, fd)
            del self.channels[runtime][module]
        except KeyError:
            # This will always happen if the module does not open any channels.
            pass

    def publish(
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
            ch = self.channels[runtime][module][fd]
        except KeyError:
            raise exceptions.ChannelException(
                "Tried to publish to nonexisting channel.")

        self.log.debug(format_message(
            "Publishing message: {}:{:02b}".format(ch.topic, ch.flags),
            runtime, module, fd))

        # Loopback
        self.handle_message(ch.topic, payload, rt=runtime, mod=module)
        # MQTT
        self.mgr.publish(ch.topic, payload)

    def handle_message(self, topic: str, payload: bytes, rt=-1, mod=-1):
        """Handle MQTT message.

        Parameters
        ----------
        topic, payload: message contents.
        rt, mod: runtime and module indices to exclude for loopback.
        """
        matched = False
        for topic_matches in self.matcher.iter_match(topic):
            for ch in topic_matches:
                matched = True
                if ch.runtime != rt and ch.module != mod:
                    self.log.debug("Matched to channel: {}".format(ch))
                    self.mgr.runtimes[ch.runtime].send(
                        Message(ch.module, ch.fd, payload))

        if not matched:
            raise exceptions.ChannelException(
                "Handling message without any matches.")
