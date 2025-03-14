"""MQTT message handler."""

import json
import logging
import traceback
from paho.mqtt import client

from beartype.typing import Optional, Union, cast
from beartype import beartype

from orchestrator.models import Runtime
from orchestrator.messages import Message, SLException, UUIDNotFound


@beartype
class BaseHandler:
    """Base class for message handlers, including some common utilities."""

    NAME: str = "abstract"
    TOPIC: Optional[str] = None

    def __init__(self):
        self.log = logging.getLogger(self.NAME)

    def handle_message(self, msg: client.MQTTMessage) -> list[Message]:
        """Message handler wrapper with error handling."""
        decoded = None
        try:
            decoded = self._decode(msg)
            res = self.handle(decoded)
            if res is None:
                return []
            elif isinstance(res, list):
                return res
            else:
                return [res]

        # SLExceptions are raised by handlers in response to
        # invalid request data (which has been detected).
        except SLException as e:
            return [e.message]
        # Uncaught exceptions here must be caused by some programmer error
        # or unchecked edge case, so are always hidden.
        except Exception as e:
            self.log.error(traceback.format_exc())
            cause = decoded.payload if decoded else msg.payload
            self.log.error("Caused by: {}".format(str(cause)))
            return []

    def handle(self, msg: Message) -> Optional[Union[Message, list[Message]]]:
        """Handle message.

        Parameters
        ----------
        msg: MQTT input message.

        Returns
        -------
        If messages.Message or a list of messages, sends as a response.
        Otherwise (if None), does nothing.

        Raises
        ------
        messages.SLException
            When a handler raises SLException in the decode or handle
            methods, the error payload is sent to the log channel
            (realm/proc/log) and shown in the orchestrator log.
        """
        raise NotImplementedError()

    @staticmethod
    def _decode(msg: client.MQTTMessage) -> Message:
        """Decode MQTT message as JSON."""
        try:
            payload = str(msg.payload.decode("utf-8", "ignore"))
            if (payload[0] == "'"):
                payload = payload[1:len(payload) - 1]
            return Message(msg.topic, json.loads(payload))
        except json.JSONDecodeError:
            raise SLException({"desc": "Invalid JSON", "data": msg.payload})

    @staticmethod
    def _get_object(uuid: str, model=Runtime):
        """Fetch runtime/module by name or UUID or generate error."""
        try:
            return model.objects.get(name=uuid)
        except model.DoesNotExist:
            try:
                return model.objects.get(uuid=uuid)
            except model.DoesNotExist:
                raise UUIDNotFound(uuid, obj_type=str(model.TYPE))

    @staticmethod
    def _object_from_dict(model, attrs: dict):
        """Convert attrs to model."""
        filtered = {k: v for k, v in attrs.items() if k in model.INPUT_ATTRS}
        return model(**filtered)

    def _set_status(
        self, tgt: Union[str, Message], status: str, action: str = "",
        model=Runtime
    ):
        """Set new status of object by UUID or message, and return model."""
        if isinstance(tgt, str):
            uuid = tgt
        else:
            uuid = cast(str, tgt.get("data", "uuid"))

        obj = self._get_object(uuid, model=model)
        obj.status = status
        obj.save()
        self.log.info("{}: {} ({})".format(action, obj.name, uuid))
        return obj
