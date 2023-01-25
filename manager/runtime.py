"""Runtime base class."""

import uuid
import time
import logging

from abc import abstractmethod
from beartype.typing import Optional, NamedTuple

from .module import Module


CREATE_MODULE = 0x80
DELETE_MODULE = 0x81
MODULE_EXITED = 0x80
KEEPALIVE = 0x81
RUNTIME_LOG = 0x82
OPEN_CHANNEL = 0x80
CLOSE_CHANNEL = 0x81
MODULE_LOG = 0x82
MODULE_PROFILE = 0x83


class Message(NamedTuple):
    """Runtime-manager message.

    | Sender  | Header     | Socket             | Message          | Data   |
    | ------- | ---------- | ------------------ | -----------------| ------ |
    | Manager | x80.x00    | sl/{rt}:x80        | Create Module    | json   |
    | Manager | x81.x00    | sl/{rt}:x81        | Delete Module    | json   |
    | Manager | {mod}.{fd} | sl/{rt}/{mod}:{fd} | Receive Message  | u8[]   |
    | Runtime | x80.x00    | sl/{rt}:x80        | Module Exited    | json   |
    | Runtime | x81.x00    | sl/{rt}:x81        | Keepalive        | json   |
    | Runtime | x82.x00    | sl/{rt}:x82        | Runtime Logging  | json   |
    | Runtime | {mod}.x80  | sl/{rt}/{mod}:x80  | Open Channel     | char[] |
    | Runtime | {mod}.x81  | sl/{rt}/{mod}:x81  | Close Channel    | char   |
    | Runtime | {mod}.x82  | sl/{rt}/{mod}:x82  | Module Logging   | char[] |
    | Runtime | {mod}.x83  | sl/{rt}/{mod}:x83  | Profiling Data   | char[] |
    | Runtime | {mod}.{fd} | sl/{rt}/{mod}:{fd} | Publish Message  | u8[]   |

    Attributes
    ----------
    h1: first header value.
    h2: second header value.
    payload: message contents.
    """

    h1: int
    h2: int
    payload: bytes


class RuntimeManager:
    """Runtime interface layer."""

    def __init__(self, rtid: str, name: str, max_nmodules: int = 128):
        self.log = logging.getLogger("runtime.{}".format(name))
        self.rtid = str(uuid.uuid4()) if rtid is None else rtid
        self.name = name
        self.index = -1
        self.modules = {}
        self.modules_uuid = {}
        self.max_nmodules = max_nmodules

    def set_index(self, index: int) -> None:
        """Set runtime index."""
        self.index = index

    @abstractmethod
    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        pass

    @abstractmethod
    def send(self, msg: Message) -> None:
        """Send message to runtime."""
        pass

    @abstractmethod
    def receive(self) -> Optional[Message]:
        """Poll interface and receive message; return None on timeout."""
        pass

    def create_module(self, mod: Module) -> None:
        """Create module."""
        for i in range(self.max_nmodules):
            if i not in self.modules:
                self.modules[i] = mod
                self.modules_uuid[mod.uuid] = i
                self.send(Message(CREATE_MODULE, 0, mod.to_json(i)))
        else:
            self.log.error(
                "Module limit exceeded: {}".format(self.max_nmodules))

    def delete_module(self, mod: Module) -> None:
        """Delete module."""
        try:
            index = self.modules_uuid[mod.uuid]
            del self.modules[index]
            del self.modules_uuid[mod.uuid]
            self.send(Message(DELETE_MODULE, 0, mod.to_json(index)))
        except KeyError:
            self.log.error(
                "Tried to delete nonexistent module: {}".format(mod.to_json()))


class TestRuntime(RuntimeManager):
    """Runtime for debugging the manager interface."""

    def __init__(self, rtid: str = None, name: str = "debug") -> None:
        super().__init__(rtid, name, max_nmodules=1)
        self.config = {
            "type": "runtime",
            "uuid": self.rtid,
            "name": self.name,
            "runtime_type": "debug/manager",
            "apis": ["debug:manager"],
        }

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        print("Runtime started.")
        return self.config

    def send(self, msg: Message) -> None:
        """Send message."""
        print("Forwarding message ({:02x}.{:02x}): {}".format(
            msg.h1, msg.h2, msg.payload))

    def receive(self) -> Optional[Message]:
        """The TestRuntime does not send messages."""
        time.sleep(1)
        return None


class LinuxRuntime(RuntimeManager):
    """Linux runtime communicating with AF_UNIX sockets."""

    def __init__(
        self, rtid: str = None, name: str = "runtime", path: str = "./runtime"
    ) -> None:
        self.path = path
        super().__init__(rtid, name, max_nmodules=128)

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

    def receive(self) -> Optional[Message]:
        """Poll interface and receive message; return None on timeout."""
        # poll socket_rt and socket_mod
        pass

    def create_module(self, cfg: dict) -> None:
        """Create module."""
        # get file
        # then...
        super().create_module(cfg)
