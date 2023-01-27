"""Supported runtimes.

Each runtime should extend RuntimeManager, and must implement the .start(),
.send(), and .receive() methods.
"""

from .base import RuntimeManager
from .linux_minimal import LinuxMinimalRuntime
from .linux import LinuxRuntime
from .test import RegistrationOnlyRuntime

__all__ = ["RuntimeManager", "LinuxMinimalRuntime", "RegistrationOnlyRuntime"]
