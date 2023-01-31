"""Testing (fake) runtime."""

import time

from beartype.typing import Optional
from beartype import beartype

from manager.types import Message
from .base import RuntimeManager


@beartype
class RegistrationOnlyRuntime(RuntimeManager):
    """Runtime for debugging the manager."""

    def __init__(self, rtid: str = None, name: str = "debug") -> None:
        super().__init__(rtid, name)
        self.config = {
            "type": "runtime",
            "uuid": self.rtid,
            "name": self.name,
            "runtime_type": "debug/manager",
            "apis": ["debug:manager"],
        }

    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        print("Runtime started.")
        return self.config

    def send(self, msg: Message) -> None:
        """Send message."""
        print("Forwarding message ({:02x}.{:02x}): {}".format(
            msg.h1, msg.h2, msg.payload))

    def receive(self) -> Optional[Message]:
        """The TestRuntime does not send messages."""
        time.sleep(1.)
        return None
