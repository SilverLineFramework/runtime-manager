"""SilverLine Modules."""


class InvalidMessage(ValueError):
    """Base class for invalid messages."""

    pass


class InvalidMessageType(InvalidMessage):
    """Message does not fit into known message types."""

    pass


class MissingRequiredKey(InvalidMessage):
    """Message is missing required key."""

    pass


class InvalidModuleSpec(InvalidMessage):
    """Missing or invalid module specifications."""

    pass
