"""Linux runtime."""

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
            "apis": ["wasi:unstable", "wasi:snapshot_preview1"],
            "page_size": 65536,
            "aot_target": {},
            "metadata": None,
            "platform": None,
        }

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        # create sockets
        self.socket_rt = None
        self.socket_mod = {}
        # - Each runtime opens `/tmp/sl/{rt}`
        # - Each module has the runtime open `/tmp/sl/{rt}/{mod}`.
        # start runtime using subprocess on self.path
        return self.config

    def send(self, msg: Message) -> None:
        """Send message."""
        # Module message
        if msg.h1 & 0x80 == 0:
            # send (size), then (msg.h2, msg.payload) to
            self.socket_mod[msg.h1]
        else:
            # send (size), then (msg.h1, msg.payload) to
            self.socket_rt

    def receive(self, timeout: float = 5.) -> Optional[Message]:
        """Poll interface and receive message; return None on timeout."""
        # poll socket_rt and socket_mod
        pass

    def create_module(self, cfg: dict) -> None:
        """Create module."""
        # get file
        # then...
        super().create_module(cfg)
