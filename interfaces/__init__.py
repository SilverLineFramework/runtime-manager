"""Runtime-manager interfaces."""

from manager import RuntimeManager

from .benchmarking import Benchmarking, BenchmarkingInterference, OpcodeCount
from .linux_minimal import LinuxMinimal, LinuxMinimalWAMR
from .linux import LinuxRuntime
from .test import RegistrationOnly

__all__ = [
    "Benchmarking",
    "BenchmarkingInterference"
    "OpcodeCount",
    "LinuxMinimal",
    "LinuxMinimalWAMR",
    "LinuxRuntime",
    "RegistrationOnly"
]

__benchmarking = {
    "_": Benchmarking,
    "if": BenchmarkingInterference,
    "interference": BenchmarkingInterference,
    "op": OpcodeCount,
    "opcodes": OpcodeCount
}


tree = {
    "_": None,
    "bench": __benchmarking,
    "benchmarking": __benchmarking,
    "linux": {
        "_": LinuxRuntime,
        "min": {
            "_": None,
            "wasmer": LinuxMinimal,
            "wamr": LinuxMinimalWAMR
        },
        "kernel": None
    },
    "test": {
        "_": None,
        "reg": RegistrationOnly
    }
}


def get_runtime(name: str) -> "RuntimeManager":
    """Get runtime by name."""
    rt_class = tree
    for spec in name.split('/'):
        rt_class = rt_class[spec]

    if isinstance(rt_class, dict):
        return rt_class["_"]
    else:
        return rt_class
