"""Runtime interface base class."""

import logging
import uuid
import json
import threading
import traceback

from abc import abstractmethod
from beartype.typing import Optional
from beartype import beartype

from manager.types import Message, Header, Channel
from manager import exceptions
from .util import ModuleLookup


@beartype
class RuntimeManager:
    """Runtime interface layer.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    cfg: Additional configuration fields to add.
    """

    TYPE = "abstract"
    APIS = []
    MAX_NMODULES = 0

    def __init__(
        self, rtid: Optional[str] = None, name: str = "runtime", cfg: dict = {}
    ) -> None:
        self.log = logging.getLogger("rt.{}".format(name))
        self.rtid = str(uuid.uuid4()) if rtid is None else rtid
        self.name = name
        self.index = -1
        self.modules = ModuleLookup()

        self.config = {
            "type": "runtime",
            "uuid": self.rtid,
            "name": self.name,
            "runtime_type": self.TYPE,
            "apis": self.APIS,
        }
        self.config.update(cfg)

        self.done = False

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

    def bind_manager(self, mgr, index: int) -> None:
        """Set runtime index."""
        self.index = index
        self.mgr = mgr

    def control_topic(self, topic: str, *ids: list[str]) -> str:
        """Format control topic name."""
        return self.mgr.control_topic(topic, self.rtid, *ids)

    def insert_module(self, data: dict) -> int:
        """Insert module into manager."""
        idx = self.modules.free_index(max=self.MAX_NMODULES)
        if idx < 0:
            raise exceptions.ModuleException(
                "Module limit (max={}) exceeded.".format(self.MAX_NMODULES),
                self.index, data["uuid"])
        data["index"] = idx
        self.modules.add(data)
        return idx

    def create_module(self, data: dict) -> None:
        """Create module; overwrite this method to add additional steps."""
        index = self.insert_module(data)
        self.send(Message.from_dict(0x80 | index, 0x00, data))
        self.log.info("Created module: {} -> x{:02x}".format(
            data["uuid"], index))

    def delete_module(self, module_id: str) -> None:
        """Delete module."""
        try:
            index = self.modules.get(module_id)
            self.send(Message(0x80 | index, 0x01, bytes()))
            self.log.info("Deleted module: x{:02x}".format(index))
        except KeyError:
            raise exceptions.ModuleException(
                "Tried to delete nonexisting module.", self.index, module_id)

    def cleanup_module(self, idx: int, mid: str, msg: Message) -> None:
        """Clean up module after exiting."""
        self.mgr.publish(
            self.control_topic("control"),
            self.mgr.control_message("exited", {
                "type": "module", "uuid": mid,
                "reason": json.loads(msg.payload)
            }))
        self.mgr.channels.cleanup(self.index, idx)
        self.modules.remove(idx)
        self.log.info("Exited: x{:02x}".format(idx))

    def on_mqtt_message(self, client, userdata, msg) -> None:
        """External message callback."""
        try:
            self._handle_control_message(msg.payload)
        except exceptions.SLException as e:
            self.log.error(e.fmt())
        except Exception as e:
            self.log.error("Uncaught exception: {}".format(e))
            self.log.error("\n".join(traceback.format_exception()))

    def _handle_control_message(self, data: bytes) -> None:
        """Handle control message on {realm}/proc/control/{rtid}."""
        self.log.debug("Received control message: {}".format(data))
        try:
            data = json.loads(data)
            action = (data["action"], data["data"]["type"])
            match action:
                case ("create", "module"):
                    self.create_module(data["data"])
                # case ("create", "runtime"):
                #     pass
                case ("delete", "module"):
                    self.delete_module(data["data"]["uuid"])
                # case ("delete", "runtime"):
                #     pass
                case _:
                    raise exceptions.InvalidMessage(
                        "Invalid message action: {}".format(action))
        except json.JSONDecodeError:
            raise exceptions.InvalidMessage("Invalid json: {}".format(data))
        except KeyError as e:
            raise exceptions.InvalidMessage(
                "Message missing required key: {}".format(e))

    def _handle_runtime_control_message(self, msg: Message) -> None:
        """Handle control message."""
        # Index is lower bits of first header byte.
        idx = msg.h1 & 0x7f
        mid = self.modules.uuid(idx)

        match msg.h2:
            case Header.keepalive:
                self.mgr.publish(
                    self.control_topic("keepalive"),
                    self.mgr.control_message("update", {
                        "type": "runtime", "uuid": self.rtid,
                        "name": self.name, **json.loads(msg.payload)
                    }))
            case Header.log_runtime:
                self.mgr.publish(self.control_topic("log"), msg.payload)
            case Header.exited:
                self.cleanup_module(idx, mid, msg)
            case Header.ch_open:
                self.mgr.channels.open(Channel(
                    self.index, idx, msg.payload[0],
                    msg.payload[2:].decode('utf-8'), msg.payload[1]))
            case Header.ch_close:
                self.mgr.channels.close(self.index, msg.payload[0])
            case Header.log_module:
                self.mgr.publish(self.control_topic("log", mid), msg.payload)
            case Header.profile:
                self.mgr.publish(
                    self.control_topic("profile", mid), msg.payload)
            case _:
                raise exceptions.SLException(
                    "Unknown message type", self.index, msg.h1, msg.h2)

    def on_runtime_message(self, msg: Message) -> None:
        """Handle message from the runtime."""
        try:
            if 0x80 & msg.h1:
                self._handle_runtime_control_message(msg)
            else:
                self.mgr.channels.publish(
                    self.index, msg.h1, msg.h2, msg.payload)
        except exceptions.SLException as e:
            self.log.error(e.fmt())
        except Exception as e:
            self.log.error("Uncaught exception: {}".format(e))
            self.log.error("\n".join(traceback.format_exception(e)))

    def loop(self) -> None:
        """Run main loop for this runtime."""
        while not self.done:
            msg = self.receive()
            if msg is not None:
                self.log.debug("Received: x{:02x}.{:02x}.{:02x}".format(
                    self.index, msg.h1, msg.h2))
                self.on_runtime_message(msg)
        self.log.debug("Exiting main loop for runtime {}:{}".format(
            self.rtid, self.name))

    def loop_start(self):
        """Start main loop."""
        self.thread = threading.Thread(target=self.loop)
        self.thread.start()

    def loop_stop(self):
        """Stop main loop."""
        self.done = True
        self.thread.join()
