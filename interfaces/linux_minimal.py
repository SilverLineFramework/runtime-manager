"""Linux minimum viable runtime."""

import os
import signal
import subprocess

from beartype.typing import Optional
from beartype import beartype

from libsilverline import Message, SLSocket
from manager import RuntimeManager, linux


@beartype
class LinuxMinimal(RuntimeManager):
    """Minimal linux runtime communicating with AF_UNIX sockets.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    command: Command to execute runtime binary.
    cfg: Additional config attributes.
    cpus: CPUs to add to cgroup. If None, does not assign a cgroup.
    """

    TYPE = "linux/min/wasmer"
    APIS = ["wasm", "wasm:wasmer", "wasi", "stdio:in", "stdio:out"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "linux-minimal-python"
    DEFAULT_SHORTNAME = "min"
    DEFAULT_COMMAND = "PYTHONPATH=. ./env/bin/python runtimes/linux_minimal.py"

    def __init__(
        self, rtid: Optional[str] = None, name: Optional[str] = None,
        command: Optional[str] = None, cfg: dict = {},
        cpus: Optional[str] = None
    ) -> None:
        self.cpus = cpus
        self.command = self.DEFAULT_COMMAND if command is None else command
        super().__init__(rtid, name, cfg=cfg)

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        if self.cpus is not None:
            linux.make_cgroup(self.cpus, self.DEFAULT_SHORTNAME)

        self.socket = SLSocket(self.index, server=True, timeout=5.)
        self.process = subprocess.Popen(
            "{} {}".format(self.command, self.index), shell=True,
            preexec_fn=os.setsid)
        self.socket.accept()
        return self.config

    def stop(self) -> None:
        """Stop process."""
        self.socket.close()
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        linux.delete_cgroup(self.DEFAULT_SHORTNAME)

    def send(self, msg: Message) -> None:
        """Send message."""
        self.socket.write(msg)

    def receive(self) -> Optional[Message]:
        """Receive message."""
        return self.socket.read()


@beartype
class LinuxMinimalWAMR(LinuxMinimal):
    """Minimal linux WAMR runtime."""

    TYPE = "linux/min/wamr"
    APIS = ["wasm", "wasi", "stdio:out"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "linux-minimal-wamr"
    DEFAULT_SHORTNAME = "wamr"
    DEFAULT_COMMAND = "./runtimes/bin/linux-minimal-wamr"
