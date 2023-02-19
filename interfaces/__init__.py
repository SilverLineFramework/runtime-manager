"""Runtime-manager interfaces."""

from manager import RuntimeManager

from .benchmarking import Benchmarking, OpcodeCount
from .linux_minimal import LinuxMinimal, LinuxMinimalWAMR
from .linux import LinuxRuntime
from .test import RegistrationOnly

__all__ = [
    "Benchmarking",
    "OpcodeCount",
    "LinuxMinimal",
    "LinuxMinimalWAMR",
    "LinuxRuntime",
    "RegistrationOnly"
]

tree = {
    "benchmarking": {
        "_": Benchmarking,
        "opcodes": OpcodeCount
    },
    "linux": {
        "min": {
            "wasmer": LinuxMinimal,
            "wamr": LinuxMinimalWAMR
        },
        "kernel": None,
        "_": LinuxRuntime
    },
    "test": {
        "reg": RegistrationOnly
    }
}


def get_runtime(name: str) -> "RuntimeManager":
    """Get runtime by name."""
    rt_class = tree
    for spec in name.split('/'):
        rt_class = rt_class[spec]
    return rt_class
