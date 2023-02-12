"""Runtime interface base class."""

import logging
import uuid
import json

from abc import abstractmethod
from beartype.typing import Optional
from beartype import beartype

from .types import Message, Header
from . import exceptions
from .module import ModuleLookup

from .logging import format_message
from .runtime_mixins import RuntimeManagerMixins


@beartype
class RuntimeManager(RuntimeManagerMixins):
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

    TYPE = "abstract"
    APIS = []
    MAX_NMODULES = 0
    DEFAULT_NAME = "runtime"

    def __init__(
        self, rtid: Optional[str] = None, name: Optional[str] = None,
        cfg: dict = {}
    ) -> None:
        self.log = logging.getLogger("if.{}".format(name))
        self.log_rt = logging.getLogger("rt.{}".format(name))
        self.rtid = str(uuid.uuid4()) if rtid is None else rtid
        self.name = self.DEFAULT_NAME if name is None else name
        self.index = -1
        self.manager = None
        self.modules = ModuleLookup(max=self.MAX_NMODULES)

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
            index = self.modules.get(module_id)
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
