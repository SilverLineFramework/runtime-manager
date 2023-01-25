"""Testing (fake) runtime."""

import time

from beartype.typing import Optional

from manager.types import Message
from .base import RuntimeManager


class TestRuntime(RuntimeManager):
    """Runtime for debugging the manager interface."""

    def __init__(self, rtid: str = None, name: str = "debug") -> None:
        super().__init__(rtid, name, max_nmodules=1)
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

    def receive(self, timeout: float = 5.) -> Optional[Message]:
        """The TestRuntime does not send messages."""
        time.sleep(timeout)
        return None
