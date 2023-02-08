"""Runtime-manager interfaces."""

from .benchmarking import LinuxBenchmarkingRuntime
from .linux_minimal import LinuxMinimalRuntime, LinuxMinimalWAMR
from .linux import LinuxRuntime
from .test import RegistrationOnlyRuntime

__all__ = [
    "LinuxBenchmarkingRuntime",
    "LinuxMinimalRuntime",
    "LinuxRuntime",
    "RegistrationOnlyRuntime"
]


tree = {
    "linux": {
        "benchmarking": {
            "basic": LinuxBenchmarkingRuntime,
            "interpreted": None,
            "instrumented": None
        },
        "minimal": {
            "wasmer": LinuxMinimalRuntime,
            "wamr": LinuxMinimalWAMR
        },
        "default": LinuxRuntime,
        "kernel": None
    },
    "test": {
        "reg": RegistrationOnlyRuntime
    }
}
