"""SilverLine Manager Exceptions."""

import traceback

from common import format_message


class UnhandledSLException(Exception):
    """Base class for unhandled exceptions."""

    pass


class SLException(Exception):
    """Base class for handled exceptions."""

    def __init__(self, msg, *args) -> None:
        super().__init__(msg)
        self.msg = msg
        self.args = args

    def fmt(self, *args) -> str:
        """Get error message."""
        return format_message(self.msg, *args, *self.args)


class ChannelException(SLException):
    """Base class for channel-based exceptions."""

    pass


class ModuleException(SLException):
    """Base class for module-related exceptions."""

    pass


class InvalidMessage(SLException):
    """Invalid message."""

    pass


def handle_error(exc, log, *context):
    """Error logger."""
    if isinstance(exc, SLException):
        log.error(exc.fmt(*context))
    else:
        log.error("Uncaught exception: {}".format(exc))
        log.error("\n".join(traceback.format_exception(exc)))
