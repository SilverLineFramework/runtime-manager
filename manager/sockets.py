"""Socket helper code."""

import socket
import struct

from beartype.typing import Optional

from .types import Message


def socket_connect(
    runtime: int, module: int = -1, server: bool = True, timeout: int = 5.
) -> socket.socket:
    """Connect to socket."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    if module == -1:
        address = "/tmp/sl/{:02x}.s".format(runtime)
    else:
        address = "/tmp/sl/{:02x}.{:02x}.s".format(runtime, module)

    if server:
        sock.bind(address)
        sock.listen(1)
    else:
        sock.connect(address)

    return sock


def socket_read(sock: socket.socket) -> Optional[Message]:
    """Read socket."""
    try:
        payloadlen, h1, h2 = struct.unpack("IBB", sock.recv(6))
        payload = sock.recv(payloadlen)
        return Message(h1, h2, payload)
    except TimeoutError:
        return None


def socket_write(sock: socket.socket, msg: Message) -> Optional[Message]:
    """Send message to socket."""
    header = struct.pack("IBB", len(msg.payload), msg.h1, msg.h2)
    sock.send(header)
    sock.send(msg.payload)
