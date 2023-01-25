"""Runtime interface base class."""

import logging
import uuid
import json

from abc import abstractmethod
from functools import partial
from beartype.typing import Optional

from manager.types import Message, Header
from .util import ModuleLookup


class RuntimeManager:
    """Runtime interface layer.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    max_nmodules: Maximum number of modules supported by this runtime.    
    """

    def __init__(self, rtid: str, name: str, max_nmodules: int = 128):
        self.log = logging.getLogger("runtime.{}".format(name))
        self.rtid = str(uuid.uuid4()) if rtid is None else rtid
        self.name = name
        self.index = -1
        self.modules = ModuleLookup()
        self.max_nmodules = max_nmodules

    def bind_manager(self, mgr, index: int) -> None:
        """Set runtime index."""
        self.index = index
        self.mgr = mgr
        self.publish = mgr.publish
        self.channel_open = partial(mgr.channel_open, runtime=self.index)
        self.channel_close = partial(mgr.channel_close, runtime=self.index)

    def control_topic(self, topic: str, *ids: list[str]) -> str:
        """Format control topic name."""
        return self.mgr.control_topic(topic, [self.rtid] + ids)

    @abstractmethod
    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        pass

    @abstractmethod
    def send(self, msg: Message) -> None:
        """Send message to runtime."""
        pass

    @abstractmethod
    def receive(self, timeout: float = 5.) -> Optional[Message]:
        """Poll interface and receive message; return None on timeout."""
        pass

    def insert_module(self, data: dict) -> None:
        """Insert module into manager."""
        idx = self.modules.free_index(max=self.max_nmodules)
        if idx >= 0:
            data["index"] = idx
            self.modules.add(data)
            return idx
        else:
            self.log.error(
                "Module limit exceeded: {}".format(self.max_nmodules))

    def create_module(self, data: dict) -> None:
        """Create module; overwrite this method to add additional steps."""
        index = self.insert_module(data)
        # --> additional steps here if required.
        self.send(Message(0x80 | index, 0x00, json.dumps(data)))

    def delete_module(self, data: dict) -> None:
        """Delete module."""
        # --> additional steps here if required.
        try:
            index = self.modules.get(data["uuid"])
            self.send(Message(0x80 | index, 0x01, None))
        except KeyError:
            self.log.error(
                "Tried to delete nonexistent module: {}".format(data["uuid"]))

    def handle_orchestrator_message(self, data: bytes) -> None:
        """Handle control message on {realm}/proc/control/{rtid}."""
        self.log.debug("Received control message: {}".format(data))

        try:
            data = json.loads(data)
            if data["action"] == "create":
                self.create_module(data["data"])
            elif data["action"] == "delete":
                self.delete_module(data["data"]["uuid"])
            else:
                self.log.error(
                    "Invalid message action: {}".format(data["action"]))
        except json.JSONDecodeError:
            self.log.error(
                "Mangled JSON could not be decoded: {}".format(data))
        except KeyError as e:
            self.log.error("Message missing required key: {}".format(e))

    def handle_runtime_message(self, msg: Message) -> None:
        """Handle control message from the runtime."""
        # Control message
        if 0x80 & msg.h1:
            # Index is lower bits of first header byte.
            idx = msg.h1 & 0x7f
            mid = self.modules.uuid(idx)

            match msg.h2:
                case Header.keepalive:
                    self.publish(
                        self.control_topic("keepalive"),
                        self.mgr.control_message("update", {
                            "type": "runtime", "uuid": self.rtid,
                            "name": self.name, **json.load(msg.payload)
                        }))
                case Header.log_runtime:
                    self.publish(self.control_topic("log"), msg.payload)
                case Header.exited:
                    self.publish(
                        self.control_topic("control"),
                        self.mgr.control_message("delete", {
                            "type": "module", "uuid": mid,
                            "reason": json.load(msg.payload)
                        }))
                    self.modules.remove(idx)
                case Header.ch_open:
                    self.channel_open(idx, msg.payload[0], msg.payload[1:])
                case Header.ch_close:
                    self.channel_close(idx, msg.payload[0])
                case Header.log_module:
                    self.publish(self.control_topic("log", mid), msg.payload)
                case Header.profile:
                    self.publish(
                        self.control_topic("profile", mid), msg.payload)
                case _:
                    self.log.error(
                        "Unknown message type: {:02x}.{:02x}".format(
                            msg.h1, msg.h2))

        # Normal Message
        else:
            self.mgr.channel_publish(self.index, msg.h1, msg.h2, msg.payload)
