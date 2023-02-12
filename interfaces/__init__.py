"""Runtime-manager interfaces."""

from .benchmarking import Benchmarking, OpcodeCount
from .linux_minimal import LinuxMinimal, LinuxMinimalWAMR
from .linux import LinuxRuntime
from .test import RegistrationOnly
__all__ = [
    "Benchmarking",
    "OpcodeCount",
    "LinuxMinimal",
    "LinuxRuntime",
    "RegistrationOnly"
]


tree = {
    "linux": {
        "benchmarking": {
            "basic": Benchmarking,
            "opcodes": OpcodeCount,
            "instrumented": None
        },
        "minimal": {
            "wasmer": LinuxMinimal,
            "wamr": LinuxMinimalWAMR
        },
        "default": LinuxRuntime,
        "kernel": None
    },
    "test": {
        "reg": RegistrationOnly
    }
}
