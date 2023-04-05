"""Runtime interface base class."""

import logging
import uuid
import json
import threading

from abc import abstractmethod
from beartype.typing import Optional
from beartype import beartype

from libsilverline import format_message, Message, Header

from . import exceptions
from .module import ModuleLookup


@beartype
class RuntimeManager:
    """Runtime interface layer.

    The constructor can be overwritten to provide more control over
    initialization and config. Generally, configuration should be set using
    the ``TYPE``, ``APIS``, ``MAX_NMODULES``, and ``DEFAULT_NAME`` attributes.

    Parameters
    ----------
    rtid: Runtime UUID.
    name: Runtime shortname.
    cfg: Additional configuration fields to add.
    """

    TYPE: str = "abstract"
    APIS: list[str] = []
    MAX_NMODULES: int = 0
    DEFAULT_NAME: str = "runtime"
    DEFAULT_SHORTNAME: str = "rt"

    def __init__(
        self, rtid: Optional[str] = None, name: Optional[str] = None,
        cfg: dict = {}
    ) -> None:
        self.name = self.DEFAULT_NAME if name is None else name
        shortname = self.name.split('.')[-1]
        self.log = logging.getLogger("if.{}".format(shortname))
        self.log_rt = logging.getLogger("rt.{}".format(shortname))
        self.rtid = str(uuid.uuid4()) if rtid is None else rtid
        self.index = -1
        self.manager = None
        self.modules = ModuleLookup(max=self.MAX_NMODULES)

        self.config = {
            "type": "runtime",
            "uuid": self.rtid,
            "name": self.name,
            "runtime_type": self.TYPE,
            "max_nmodules": self.MAX_NMODULES,
            "apis": self.APIS,
        }
        self.config.update(cfg)

        self.done = False

    @abstractmethod
    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        pass

    def stop(self) -> None:
        """Stop runtime."""
        pass

    @abstractmethod
    def send(self, msg: Message) -> None:
        """Send message to runtime."""
        pass

    @abstractmethod
    def receive(self) -> Optional[Message]:
        """Poll interface and receive message; return None on timeout."""
        pass

    def create_module(self, data: dict) -> None:
        """Create module; overwrite this method to add additional steps.

        Parameters
        ----------
        data: module create message payload; is sent on as a JSON. See
            documentation for field structure.
        """
        index = self.modules.insert(data)
        data["index"] = index
        self.send(Message.from_dict(
            Header.control | index, Header.create, data))
        self.log.info(format_message(
            "Created module: {}".format(data['uuid']), self.index, index))

    def delete_module(self, module_id: str) -> None:
        """Delete module; overwrite this method to add additional steps."""
        try:
            index = self.modules.get(module_id)["index"]
            self.send(Message(Header.control | index, Header.delete, bytes()))
            self.log.info(format_message("Deleted module.", self.index, index))
        except KeyError:
            raise exceptions.ModuleException(
                "Tried to delete nonexisting module: {}".format(module_id))

    def handle_profile(self, module: str, msg: bytes) -> None:
        """Handle profiling message.

        Does nothing by default, and must be implemented by inheriting
        classes.
        """
        pass

    def handle_keepalive(self, payload: bytes) -> None:
        """Send runtime keepalive; overwrite to add additional metadata."""
        self.mgr.publish(
            self.control_topic("keepalive"),
            self.mgr.control_message("update", {
                "type": "runtime", "uuid": self.rtid,
                "apis": self.APIS, "name": self.name,
                **json.loads(payload)
            }))

    def handle_log(self, payload: bytes, module: int = -1) -> None:
        """Handle logging message."""
        if payload[0] & 0x80 == 0:
            self.log_rt.debug(payload.decode('unicode-escape'))
        else:
            self.log_rt.log(
                payload[0] & 0x7f, payload[1:].decode('unicode-escape'))

    # --------------------------- Internal Methods -------------------------- #

    def __loop_start(self) -> None:
        """Start main loop."""
        def _loop():
            while not self.done:
                msg = self.receive()
                if msg is not None:
                    self.log.log(5, format_message(
                        "Received message.", self.index, msg.h1, msg.h2))
                    self.on_runtime_message(msg)
            self.log.debug(format_message("Exiting main loop.", self.index))

        self.thread = threading.Thread(target=_loop)
        self.thread.start()

    def _start(self, mgr, index: int) -> None:
        """Full runtime start procedure."""
        self.index = index
        self.mgr = mgr

        topic = self.control_topic("control")
        self.mgr.subscribe(topic)
        self.mgr.message_callback_add(topic, self.on_mqtt_message)

        metadata = self.start()
        metadata["parent"] = self.mgr.uuid
        self.mgr._register(
            self.control_topic("reg"),
            self.mgr.control_message("create", metadata))
        self.__loop_start()
        self.log.info("Registered: {}:{} (x{:02x})".format(
            self.name, self.rtid, self.index))

    def _stop(self) -> None:
        """Full runtime stop procedure."""
        self.stop()
        self.done = True
        self.thread.join()

    def control_topic(self, topic: str, *ids: str) -> str:
        """Format control topic name."""
        return self.mgr.control_topic(topic, self.rtid, *ids)

    def cleanup_module(self, idx: int, mid: str, msg: Message) -> None:
        """Clean up module after exiting."""
        self.mgr.publish(
            self.control_topic("control"),
            self.mgr.control_message("exited", {
                "type": "module", "uuid": mid, **json.loads(msg.payload)}))
        self.mgr.channels.cleanup(self.index, idx)
        self.modules.remove(idx)
        self.log.info(format_message("Module exited.", self.index, idx))

    def __handle_control_message(self, data: bytes) -> None:
        """Handle control message on {realm}/proc/control/{rtid}."""
        self.log.debug(
            "Received control message: {}".format(data.decode('utf-8')))
        try:
            data_dict = json.loads(data)
            action = (data_dict["action"], data_dict["data"]["type"])
            match action:
                case ("create", "module"):
                    self.create_module(data_dict["data"])
                case ("delete", "module"):
                    self.delete_module(data_dict["data"]["uuid"])
                case _:
                    raise exceptions.InvalidMessage(
                        "Invalid message action: {}".format(action))
        except json.JSONDecodeError:
            raise exceptions.InvalidMessage(
                "Invalid json: {}".format(data.decode('utf-8')))
        except KeyError as e:
            raise exceptions.InvalidMessage(
                "Message missing required key: {}".format(e))

    def on_mqtt_message(self, client, userdata, msg) -> None:
        """External message callback."""
        try:
            self.__handle_control_message(msg.payload)
        except Exception as e:
            exceptions.handle_error(e, self.log, self.index)

    def __handle_runtime_control_message(self, msg: Message) -> None:
        """Handle control message."""
        match (msg.h1 & Header.control, msg.h1 & Header.index_bits, msg.h2):
            case (0x00, h1, h2):
                self.mgr.channels.publish(self.index, h1, h2, msg.payload)
            case (Header.control, _, Header.keepalive):
                self.handle_keepalive(msg.payload)
            case (Header.control, _, Header.log_runtime):
                self.handle_log(msg.payload, module=-1)
            case (Header.control, idx, Header.exited):
                self.cleanup_module(idx, self.modules.uuid(idx), msg)
            case (Header.control, idx, Header.ch_open):
                self.mgr.channels.open(
                    runtime=self.index, module=idx, fd=msg.payload[0],
                    topic=msg.payload[2:], flags=msg.payload[1])
            case (Header.control, _, Header.ch_close):
                self.mgr.channels.close(self.index, msg.payload[0])
            case (Header.control, idx, Header.log_module):
                self.handle_log(msg.payload, module=idx)
            case (Header.control, idx, Header.profile):
                self.handle_profile(self.modules.uuid(idx), msg.payload)
            case _:
                raise exceptions.SLException("Unknown message type")

    def on_runtime_message(self, msg: Message) -> None:
        """Handle message from the runtime."""
        try:
            self.__handle_runtime_control_message(msg)
        except Exception as e:
            exceptions.handle_error(e, self.log, self.index, msg.h1, msg.h2)
