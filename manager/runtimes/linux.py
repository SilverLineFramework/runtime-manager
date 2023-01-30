"""Linux runtime."""

import json

from manager.types import Message
from manager import socket

from .linux_minimal import LinuxMinimalRuntime


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
        self.socket_mod[index] = socket.connect(
            self.index, module=index, server=True, timeout=5.)
        self.send(Message.from_dict(0x80 | index, 0x00, data))
        self.socket_mod.accept()

    def delete_module(self, data: dict) -> None:
        """Delete module."""
        try:
            index = self.modules.get(data["uuid"])
            self.send(Message(0x80 | index, 0x01, bytes()))
            self.socket_mod[index].close()
            del self.socket_mod[index]
        except KeyError:
            self.log.error(
                "Tried to delete nonexistent module: {}".format(data["uuid"]))

    def send(self, msg: Message) -> None:
        """Send message."""
        if msg.h1 & 0x80 == 0:
            socket.write(self.socket_mod[msg.h1], msg)
        else:
            socket.write(self.socket, msg)
