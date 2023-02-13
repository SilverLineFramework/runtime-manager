"""Linux minimum viable runtime."""

import subprocess

from beartype.typing import Optional
from beartype import beartype

from manager import Message, SLSocket, RuntimeManager


@beartype
class LinuxMinimal(RuntimeManager):
    """Minimal linux runtime communicating with AF_UNIX sockets.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    command: Command to execute runtime binary.
    cfg: Additional config attributes.
    """

    TYPE = "linux/minimal/python"
    APIS = ["wasm", "wasi", "stdio:in", "stdio:out"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "linux-minimal-python"
    DEFAULT_COMMAND = "PYTHONPATH=. python runtimes/linux_minimal.py"

    def __init__(
        self, rtid: str = None, name: Optional[str] = None,
        command: Optional[str] = None, cfg: dict = {}
    ) -> None:
        self.command = self.DEFAULT_COMMAND if command is None else command
        super().__init__(rtid, name, cfg=cfg)

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        self.socket = SLSocket(self.index, server=True, timeout=1.)
        self.process = subprocess.Popen(
            "{} {}".format(self.command, self.index), shell=True)
        self.socket.accept()
        return self.config

    def stop(self) -> None:
        """Stop process."""
        self.socket.close()
        self.process.terminate()

    def send(self, msg: Message) -> None:
        """Send message."""
        self.socket.write(msg)

    def receive(self) -> Optional[Message]:
        """Receive message."""
        return self.socket.read()


@beartype
class LinuxMinimalWAMR(LinuxMinimal):
    """Minimal linux WAMR runtime."""

    TYPE = "linux/minimal/wamr"
    APIS = ["wasm", "wasi", "stdio:out"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "linux-minimal-wamr"
    DEFAULT_COMMAND = "./runtimes/linux-minimal-wamr/build/runtime"
