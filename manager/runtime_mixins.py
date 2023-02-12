"""Additional RuntimeManager methods."""

import json
import threading

from . import exceptions
from .types import Channel, Message, Header
from .logging import format_message


class RuntimeManagerMixins:
    """Runtime manager mixins.

    These methods should not be overridden by inheriting classes (under normal
    circumstances).
    """

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
        self.loop_start()
        self.log.info("Registered: {}:{} (x{:02x})".format(
            self.name, self.rtid, self.index))

    def control_topic(self, topic: str, *ids: list[str]) -> str:
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

    def on_mqtt_message(self, client, userdata, msg) -> None:
        """External message callback."""
        try:
            self.__handle_control_message(msg.payload)
        except Exception as e:
            exceptions.handle_error(e, self.log, self.index)

    def __handle_runtime_control_message(self, msg: Message) -> None:
        """Handle control message."""
        # Index is lower bits of first header byte.
        idx = msg.h1 & Header.index_bits

        match msg.h2:
            case Header.keepalive:
                self.handle_keepalive(msg.payload)
            case Header.log_runtime:
                self.handle_log(msg.payload, module=-1)
            case Header.exited:
                self.cleanup_module(idx, self.modules.uuid(idx), msg)
            case Header.ch_open:
                self.mgr.channels.open(
                    runtime=self.index, module=idx, fd=msg.payload[0],
                    topic=msg.payload[2:], flags=msg.payload[1])
            case Header.ch_close:
                self.mgr.channels.close(self.index, msg.payload[0])
            case Header.log_module:
                self.handle_log(msg.payload, module=self.modules.uuid(idx))
            case Header.profile:
                self.handle_profile(self.modules.uuid(idx), msg.payload)
            case _:
                raise exceptions.SLException("Unknown message type")

    def on_runtime_message(self, msg: Message) -> None:
        """Handle message from the runtime."""
        try:
            if Header.control & msg.h1:
                self.__handle_runtime_control_message(msg)
            else:
                self.mgr.channels.publish(
                    self.index, msg.h1, msg.h2, msg.payload)
        except Exception as e:
            exceptions.handle_error(e, self.log, self.index, msg.h1, msg.h2)

    def loop(self) -> None:
        """Run main loop once for this runtime."""
        msg = self.receive()
        if msg is not None:
            self.log.debug(format_message(
                "Received message.", self.index, msg.h1, msg.h2))
            self.on_runtime_message(msg)

    def loop_start(self) -> None:
        """Start main loop."""
        def _loop():
            while not self.done:
                self.loop()
            self.log.debug(format_message("Exiting main loop.", self.index))

        self.thread = threading.Thread(target=_loop)
        self.thread.start()

    def loop_stop(self) -> None:
        """Stop main loop."""
        self.done = True
        self.thread.join()
