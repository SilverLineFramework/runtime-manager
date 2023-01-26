"""Linux runtime."""

import json
import subprocess

from beartype.typing import Optional

from manager.types import Message
from .base import RuntimeManager
from manager.sockets import socket_connect, socket_read, socket_write


class LinuxMinimalRuntime(RuntimeManager):
    """Minimal linux runtime communicating with AF_UNIX sockets.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    command: Command to execute runtime binary.
    """

    TYPE = "linux/minimal"
    APIS = []
    MAX_NMODULES = 1

    def __init__(
        self, rtid: str = None, name: str = "runtime-linux-minimal",
        command: list[str] = ["./runtime"], cfg: dict = {}
    ) -> None:
        self.command = command
        super().__init__(rtid, name, cfg=cfg)

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        self.socket = socket_connect(self.index, server=True, timeout=5.)
        subprocess.Popen(self.command)
        self.socket.accept()
        return self.config

    def send(self, msg: Message) -> None:
        """Send message."""
        socket_write(self.socket, msg)

    def receive(self) -> Optional[Message]:
        """Receive message."""
        return socket_read(self.socket)


class LinuxRuntime(LinuxMinimalRuntime):
    """Default Linux Runtime."""

    TYPE = "linux/default"
    APIS = ["channels", "wasi:unstable", "wasi:snapshot_preview1"]
    MAX_NMODULES = 128

    def __init__(
        self, rtid: str = None, name: str = "runtime-linux-default",
        path: str = "./runtime"
    ) -> None:
        super().__init__(rtid, name, path, {
            "page_size": 65536, "aot_target": {},
            "metadata": None, "platform": None
        })
        self.socket_mod = {}

    def create_module(self, data: dict) -> None:
        """Create module."""
        index = self.insert_module(data)
        self.socket_mod[index] = socket_connect(
            self.index, module=index, server=True, timeout=5.)
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
        if msg.h1 & 0x80 == 0:
            socket_write(self.socket_mod[msg.h1], msg)
        else:
            socket_write(self.socket, msg)
