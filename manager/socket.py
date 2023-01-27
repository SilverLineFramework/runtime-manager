"""Socket helper code."""

import os
import socket
import struct
import select

from beartype.typing import Optional

from .types import Message


class SLSocket:
    """Silverline local socket."""

    def __init__(
        self, runtime: int, module: int = -1, server: bool = True,
        timeout: int = 5.
    ) -> None:
        """Create and connect to socket."""
        self.timeout = timeout
        self.server = server
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)

        if module == -1:
            address = "/tmp/sl/{:02x}.s".format(runtime)
        else:
            address = "/tmp/sl/{:02x}.{:02x}.s".format(runtime, module)

        if server:
            if os.path.exists(address):
                os.remove(address)
            os.makedirs(os.path.dirname(address), exist_ok=True)
            self.socket.bind(address)
            self.socket.listen(1)
        else:
            self.socket.connect(address)
            self.connection = self.socket
            # self.poll = select.poll()
            # self.poll.register(self.socket, select.POLLIN)

    def accept(self) -> None:
        """Accept connection."""
        self.connection, _ = self.socket.accept()
        print("accepted connection.")
        # self.poll = select.poll()
        # self.poll.register(self.socket, select.POLLIN)

    def read(self) -> Optional[Message]:
        """Read with timeout."""
        # self.poll.poll(self.timeout)
        try:
            recv = self.connection.recv(6)
            if recv:
                payloadlen, h1, h2 = struct.unpack("IBB", recv)
                payload = self.connection.recv(payloadlen)
                print("recv", h1, h2, self.server)
                return Message(h1, h2, payload)
            else:
                return None
        except TimeoutError:
            return None

    def write(self, msg: Message) -> None:
        """Send message to socket."""
        print("send", msg.h1, msg.h2, self.server)
        header = struct.pack("IBB", len(msg.payload), msg.h1, msg.h2)
        try:
            self.connection.sendall(header)
            self.connection.sendall(msg.payload)
        except TimeoutError:
            pass
