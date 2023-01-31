"""SilverLine Manager Exceptions."""


class UnhandledSLException(Exception):
    """Base class for unhandled exceptions."""

    pass


class SLException(Exception):
    """Base class for handled exceptions."""

    def __init__(self, msg, *args) -> None:
        super().__init__(msg)
        self.msg = msg
        self.args = args

    def _fmt(self, x):
        if isinstance(x, int):
            return "{:02x}".format(x)
        elif isinstance(x, str):
            return x[:2] + ".." + x[-4:]
        return x

    def fmt(self) -> str:
        """Get error message."""
        if len(self.args) == 0:
            return self.msg
        else:
            return "[{}] {}".format(
                ".".join([self._fmt(a) for a in self.args]), self.msg)


class ChannelException(SLException):
    """Base class for channel-based exceptions."""

    pass


class ModuleException(SLException):
    """Base class for module-related exceptions."""

    pass


class InvalidMessage(SLException):
    """Invalid message."""

    pass
