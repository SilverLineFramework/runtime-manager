"""Linux runtime."""

import struct
import socket
import json
import subprocess

from beartype.typing import Optional

from manager.types import Message
from .base import RuntimeManager


class LinuxMinimalRuntime(RuntimeManager):
    """Minimal linux runtime communicating with AF_UNIX sockets.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    path: Path to runtime binary.
    """

    def __init__(
        self, rtid: str = None, name: str = "runtime-linux-minimal",
        path: str = "./runtime"
    ) -> None:
        self.path = path
        super().__init__(rtid, name, max_nmodules=1)

        self.config = {
            "type": "runtime",
            "uuid": self.rtid,
            "name": self.name,
            "runtime_type": "linux/minimal",
            "apis": [],
            "page_size": 65536,
            "aot_target": {},
            "metadata": None,
            "platform": None,
        }

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind("/tmp/sl/{:02x}.s".format(self.index))
        self.socket.settimeout(5.)
        self.socket.listen(1)

        subprocess.Popen([self.path])

        self.socket.accept()
        return self.config

    def send(self, msg: Message) -> None:
        """Send message."""
        header = struct.pack("IBB", len(msg.payload), msg.h1, msg.h2)

        self.socket.send(header)
        self.socket.send(msg.payload)

    def receive(self) -> Optional[Message]:
        """Receive message."""
        try:
            payloadlen, h1, h2 = struct.unpack("IBB", self.socket.recv(6))
            payload = self.socket.recv(payloadlen)
            return Message(h1, h2, payload)
        except TimeoutError:
            return None


class LinuxRuntime(LinuxMinimalRuntime):
    """Default Linux Runtime."""

    def __init__(
        self, rtid: str = None, name: str = "runtime-linux-default",
        path: str = "./runtime"
    ) -> None:
        self.path = path
        super().__init__(rtid, name, max_nmodules=128)

        self.config = {
            "type": "runtime",
            "uuid": self.rtid,
            "name": self.name,
            "runtime_type": "linux/default",
            "apis": ["wasi:unstable", "wasi:snapshot_preview1"],
            "page_size": 65536,
            "aot_target": {},
            "metadata": None,
            "platform": None,
        }
        self.socket_mod = {}

    def create_module(self, data: dict) -> None:
        """Create module."""
        index = self.insert_module(data)
        self.socket_mod[index] = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_mod[index].bind(
            "/tmp/sl/{:02x}.{:02x}.s".format(self.index, index))
        self.socket_mod[index].listen(1)
        self.send(Message(0x80 | index, 0x00, json.dumps(data)))
        self.socket_mod.accept()

    def delete_module(self, data: dict) -> None:
        """Delete module."""
        try:
            index = self.modules.get(data["uuid"])
            self.send(Message(0x80 | index, 0x01, None))
            self.socket_mod[index].close()
            del self.socket_mod[index]
        except KeyError:
            self.log.error(
                "Tried to delete nonexistent module: {}".format(data["uuid"]))

    def send(self, msg: Message) -> None:
        """Send message."""
        header = struct.pack("IBB", len(msg.payload), msg.h1, msg.h2)

        if msg.h1 & 0x80 == 0:
            sock = self.socket_mod[msg.h1]
        else:
            sock = self.socket

        sock.send(header)
        sock.send(msg.payload)
