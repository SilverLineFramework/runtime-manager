"""SilverLine Runtime Manager Messaging and Types."""

import json
from beartype.typing import NamedTuple
from beartype import beartype


@beartype
class Message(NamedTuple):
    """Runtime-manager messaging.

    Todos
    -----
    Add wasi dirs "dir" (list[str]) attribute to Create Module
    Add "status" (object) attribute to Module Exited

    Attributes
    ----------
    h1: first header value.
    h2: second header value.
    payload: message contents.
    """

    h1: int
    h2: int
    payload: bytes

    @classmethod
    def from_str(cls, h1: int, h2: int, payload: str):
        """Create message from string."""
        return cls(h1=h1, h2=h2, payload=bytes(payload, encoding='utf-8'))

    @classmethod
    def from_dict(cls, h1: int, h2: int, payload: dict):
        """Create message from dictionary using JSON encoding."""
        return cls(
            h1=h1, h2=h2, payload=bytes(json.dumps(payload), encoding='utf-8'))


class Header:
    """Header enum with header byte values.

    Change these values and upgrade the underlying connection if larger
    header values are required, i.e. to support >128 modules or >256 channels.

    Uprading module index assignment (``ModuleLookup.free_index``) not to use
    brute force search is also likely required.
    """

    keepalive   = 0x00
    log_runtime = 0x01
    exited      = 0x02
    ch_open     = 0x03
    ch_close    = 0x04
    log_module  = 0x05
    profile     = 0x06

    create      = 0x00
    delete      = 0x01
    stop        = 0x02

    control     = 0x80
    index_bits  = 0x7f


@beartype
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


class Flags:
    """Channel flags enum.

    Bit 0 indicates read permissions, and bit 1 indicates write permissions.
    Notably, if the write bit is set, the channel topic cannot contain
    wildcards.

    Higher bits can be saved for other features (such as MQTT QoS).
    """

    read      = 0b0001
    write     = 0b0010
    readwrite = 0b0011

    qos0      = 0b0000
    qos1      = 0b0100
    qos2      = 0b1000
