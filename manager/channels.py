"""Channels interface."""

import logging
import paho.mqtt.client as mqtt
from beartype.typing import NamedTuple

from .types import Message


class Flags:
    """Channel flags enum."""

    read = 0b0001
    write = 0b0010
    readwrite = 0b0011


class Channel(NamedTuple):
    """Open Channel.

    Attributes
    ----------
    runtime: Runtime index.
    module: Module index for this runtime.
    fd: Channel index for this module.
    topic: Topic name.
    flags: Read, write, or read-write.
    """

    runtime: int
    module: int
    fd: int
    topic: str
    flags: int

    def to_str(self) -> str:
        """Get string representation."""
        return "[{:02x}.{:02x}.{:02x}] {}:{:02b}".format(
            self.runtime, self.module, self.fd, self.topic, self.flags)


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
        self.log = logging.getLogger("channels")
        self.matcher = mqtt.MQTTMatcher()
        self.channels = {}

    def _err_nonexistent(self, action, runtime, module, fd):
        self.log.error("Tried to {} nonexisting channel: {}/{}/{}".format(
            action, runtime, module, fd))

    def open(self, ch: Channel) -> None:
        """Open channel."""
        if ch.runtime not in self.channels:
            self.channels[ch.runtime] = {}
        if ch.module not in self.channels[ch.runtime]:
            self.channels[ch.runtime][ch.module] = {}

        if ch.fd in self.channels[ch.runtime][ch.module]:
            self.close(ch.runtime, ch.module, ch.fd)

        if (ch.flags | Flags.write) != 0:
            try:
                self.matcher[ch.topic].add(ch)
            except KeyError:
                try:
                    self.mgr.subscribe(ch.topic)
                    self.matcher[ch.topic] = {ch}
                # Subscribing fails with ValueError if the channel topic is
                # illegal (i.e. contains wildcard '+' or '#')
                except ValueError:
                    pass

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
            try:
                subscribed = self.matcher[channel.topic]
                if channel in subscribed:
                    subscribed.remove(channel)
                if len(subscribed) == 0:
                    self.mgr.unsubscribe(channel.topic)
                    del self.matcher[channel.topic]
            except KeyError:
                pass
        except KeyError:
            self._err_nonexistent("close", runtime, module, fd)

    def cleanup(self, runtime: int, module: int) -> None:
        """Cleanup all channels associated with a module.

        Parameters
        ----------
        runtime: runtime index.
        module: module index on this runtime.
        """
        try:
            for fd in self.channels[runtime][module]:
                self.close(runtime, module, fd)
            del self.channels[runtime][module]
        except KeyError:
            self.log.error("Invalid module: {}.{}".format(runtime, module))

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
            channel = self.channels[runtime][module][fd]
            self.log.debug("Publishing @ {}".format(channel.to_str()))
            # Loopback
            self.handle_message(channel.topic, payload, rt=runtime, mod=module)
            # MQTT
            self.mgr.publish(channel.topic, payload)
        except KeyError:
            self._err_nonexistent("publish to", runtime, module, fd)

    def handle_message(self, topic: str, payload: bytes, rt=-1, mod=-1):
        """Handle MQTT message.

        Parameters
        ----------
        topic, payload: message contents.
        rt, mod: runtime and module indices to exclude for loopback.
        """
        for topic_matches in self.matcher.iter_match(topic):
            for ch in topic_matches:
                if ch.runtime != rt and ch.module != mod:
                    self.log.debug("Matched to channel: {}".format(ch))
                    self.mgr.runtimes[ch.runtime].send(
                        Message(ch.module, ch.fd, payload))
