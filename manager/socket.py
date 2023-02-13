"""Socket helper code."""

import os
import socket
import select
import struct

from beartype.typing import Optional
from beartype import beartype

from .types import Message


@beartype
class SLSocket:
    """Silverline local socket.

    Sockets use the following protocol::

        [ -- len:2 -- ][h1:1][h2:1][ ------ payload:len ------ ]

    See the documentation of `manager.types.Message` for header values.
    Empty payloads are also supported.

    Parameters
    ----------
    runtime: runtime index
    module: module index on this runtime.
    server: whether this socket is a server or client socket.
    timeout: connect, receive timeout in seconds.
    base_path: socket base path.
    chunk_size: size of chunks to read from the socket.
    """

    HEADER_FMT = "HBB"
    HEADER_SIZE = 4

    def __init__(
        self, runtime: int, module: int = -1, server: bool = True,
        timeout: float = 5., base_path="/tmp/sl", chunk_size: int = 4096
    ) -> None:
        self.timeout = timeout
        self.server = server
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.chunk_size = chunk_size

        if module == -1:
            address = "{}/{:02x}.s".format(base_path, runtime)
        else:
            address = "{}/{:02x}.{:02x}.s".format(base_path, runtime, module)

        if server:
            if os.path.exists(address):
                os.remove(address)
            os.makedirs(os.path.dirname(address), exist_ok=True)
            self.socket.bind(address)
            self.socket.listen(1)
        else:
            self.socket.connect(address)
            self.connection = self.socket
            self.connection.setblocking(0)

    def accept(self) -> None:
        """Accept connection."""
        self.connection, _ = self.socket.accept()
        self.connection.setblocking(0)

    def read(self) -> Optional[Message]:
        """Read with timeout."""
        ready = select.select([self.connection], [], [], self.timeout)
        if ready[0]:
            recv = self.connection.recv(self.HEADER_SIZE)
            if len(recv) == self.HEADER_SIZE:
                payloadlen, h1, h2 = struct.unpack(self.HEADER_FMT, recv)
                payload = []
                while payloadlen > 0:
                    recv = min(payloadlen, self.chunk_size)
                    payload.append(self.connection.recv(recv))
                    payloadlen -= recv
                return Message(h1, h2, b"".join(payload))
        return None

    def write(self, msg: Message) -> None:
        """Send message to socket."""
        header = struct.pack(self.HEADER_FMT, len(msg.payload), msg.h1, msg.h2)
        try:
            self.connection.sendall(header)
            if len(msg.payload) > 0:
                self.connection.sendall(msg.payload)
        except TimeoutError:
            pass

    def close(self) -> None:
        """Close socket (and interrupt currently reading operations)."""
        self.socket.shutdown(socket.SHUT_RDWR)
