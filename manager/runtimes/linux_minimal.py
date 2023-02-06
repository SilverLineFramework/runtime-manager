"""Linux minimum viable runtime."""

import subprocess

from beartype.typing import Optional
from beartype import beartype

from manager.types import Message
from manager import SLSocket

from .base import RuntimeManager


@beartype
class LinuxMinimalRuntime(RuntimeManager):
    """Minimal linux runtime communicating with AF_UNIX sockets.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    command: Command to execute runtime binary.
    """

    TYPE = "linux/minimal"
    APIS = ["wasm", "wasi", "stdin", "stdout"]
    MAX_NMODULES = 1

    def __init__(
        self, rtid: str = None, name: str = "runtime-linux-minimal",
        command: str = "PYTHONPATH=. python runtimes/linux_minimal.py",
        cfg: dict = {}
    ) -> None:
        self.command = command
        super().__init__(rtid, name, cfg=cfg)

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        self.socket = SLSocket(self.index, server=True, timeout=5.)
        subprocess.Popen("{} {}".format(self.command, self.index), shell=True)
        self.socket.accept()
        return self.config

    def send(self, msg: Message) -> None:
        """Send message."""
        self.socket.write(msg)

    def receive(self) -> Optional[Message]:
        """Receive message."""
        return self.socket.read()
