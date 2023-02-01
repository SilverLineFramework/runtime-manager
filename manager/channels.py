"""Channels interface."""

import logging
import paho.mqtt.client as mqtt
from beartype import beartype

from .types import Message, Flags, Channel
from . import exceptions
from .logging import format_message


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

    def open(self, ch: Channel) -> None:
        """Open channel."""
        if ch.runtime not in self.channels:
            self.channels[ch.runtime] = {}
        if ch.module not in self.channels[ch.runtime]:
            self.channels[ch.runtime][ch.module] = {}

        if ch.fd in self.channels[ch.runtime][ch.module]:
            raise exceptions.ChannelException(
                "Tried to open already-existing channel")

        # Check for wildcards
        if (ch.flags | Flags.write) != 0:
            if '+' in ch.topic or '#' in ch.topic:
                raise exceptions.ChannelException(
                    "Channel topic name cannot contain a wildcard ('+', '#') "
                    "in write or read-write mode: {}".format(ch.topic))

        # Requires subscribing
        if (ch.flags | Flags.read) != 0:
            try:
                self.matcher[ch.topic].add(ch)
            except KeyError:
                self.mgr.subscribe(ch.topic)
                self.matcher[ch.topic] = {ch}

        self.channels[ch.runtime][ch.module][ch.fd] = ch

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
            raise exceptions.ChannelException(
                "Tried to cleanup nonexisting module.")

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
