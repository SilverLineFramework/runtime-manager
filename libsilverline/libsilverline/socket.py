"""Socket helper code."""

import os
import socket
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
    retries: maximum number of times to try sending data if send fails.
    """

    HEADER_FMT = "HBB"
    HEADER_SIZE = 4

    def __init__(
        self, runtime: int, module: int = -1, server: bool = True,
        timeout: float = 5., base_path="/tmp/sl", chunk_size: int = 4096,
        retries: int = 10
    ) -> None:
        self.timeout = timeout
        self.server = server
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.chunk_size = chunk_size
        self.retries = retries

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
            self.connection.settimeout(self.timeout)

    def accept(self) -> None:
        """Accept connection."""
        self.connection, _ = self.socket.accept()
        self.connection.settimeout(self.timeout)

    def read(self) -> Optional[Message]:
        """Read with timeout."""
        try:
            recv = self.connection.recv(self.HEADER_SIZE)
            if len(recv) == self.HEADER_SIZE:
                payloadlen, h1, h2 = struct.unpack(self.HEADER_FMT, recv)
                payload = []
                while payloadlen > 0:
                    size = min(payloadlen, self.chunk_size)
                    payload.append(self.connection.recv(size))
                    payloadlen -= size
                return Message(h1, h2, b"".join(payload))
            return None
        except TimeoutError:
            return None

    def _send(self, packet):
        for _ in range(self.retries):
            try:
                return self.connection.sendall(packet)
            except TimeoutError:
                pass
        raise TimeoutError

    def write(self, msg: Message) -> None:
        """Send message to socket."""
        header = struct.pack(self.HEADER_FMT, len(msg.payload), msg.h1, msg.h2)
        try:
            self._send(header)
            if len(msg.payload) > 0:
                self._send(msg.payload)
        except TimeoutError:
            pass

    def close(self) -> None:
        """Close socket (and interrupt currently reading operations)."""
        self.socket.shutdown(socket.SHUT_RDWR)
