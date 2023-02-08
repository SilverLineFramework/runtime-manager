"""Linux runtime."""

from beartype import beartype

from manager import Message, Header, SLSocket
from .linux_minimal import LinuxMinimalRuntime


@beartype
class LinuxRuntime(LinuxMinimalRuntime):
    """Default Linux Runtime."""

    TYPE = "linux/default"
    APIS = ["channels", "wasi:unstable", "wasi:snapshot_preview1"]
    MAX_NMODULES = 128

    def __init__(
        self, rtid: str = None, name: str = "linux-default",
        path: str = "./todo"
    ) -> None:
        super().__init__(rtid, name, path, {
            "page_size": 65536, "aot_target": {},
            "metadata": None, "platform": None
        })
        self.socket_mod = {}

    def create_module(self, data: dict) -> None:
        """Create module."""
        index = self.insert_module(data)
        self.socket_mod[index] = SLSocket(
            self.index, module=index, server=True, timeout=5.)
        self.send(Message.from_dict(
            Header.control | index, Header.create, data))
        self.socket_mod[index].accept()

    def delete_module(self, data: dict) -> None:
        """Delete module."""
        try:
            index = self.modules.get(data["uuid"])
            self.send(Message(Header.control | index, Header.delete, bytes()))
            self.socket_mod[index].close()
            del self.socket_mod[index]
        except KeyError:
            self.log.error(
                "Tried to delete nonexistent module: {}".format(data["uuid"]))

    def send(self, msg: Message) -> None:
        """Send message."""
        if msg.h1 & Header.control == 0:
            self.socket_mod[msg.h1].write(msg)
        else:
            self.socket.write(msg)
