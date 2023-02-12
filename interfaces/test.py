"""Debugging runtimes."""

import time

from beartype.typing import Optional
from beartype import beartype

from manager import Message, RuntimeManager


@beartype
class RegistrationOnly(RuntimeManager):
    """Dummy runtime for basic debugging."""

    TYPE = "debug/none"
    AIPS = []
    MAX_NMODULES = 0

    def __init__(self, rtid: str = None, name: str = "debug-none") -> None:
        super().__init__(rtid, name)

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        self.log.info("Runtime started.")
        return self.config

    def send(self, msg: Message) -> None:
        """Not implemented."""
        pass

    def receive(self) -> Optional[Message]:
        """Not implemented."""
        time.sleep(1.)
        pass
