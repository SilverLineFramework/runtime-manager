"""Runtime-manager interfaces."""

from manager import RuntimeManager

from .benchmarking import (
    Benchmarking, BenchmarkingSeeded, BenchmarkingInterference, OpcodeCount)
from .data_race import (
    DataRaceAccessSingle, DataRaceAccessBatch, DataRaceTSVSingle, DataRaceTSVBatch)
from .linux_minimal import LinuxMinimal, LinuxMinimalWAMR
from .linux import LinuxRuntime
from .test import RegistrationOnly

from beartype.typing import cast


__all__ = [
    "Benchmarking",
    "BenchmarkingSeeded",
    "BenchmarkingInterference",
    "OpcodeCount",
    "LinuxMinimal",
    "LinuxMinimalWAMR",
    "LinuxRuntime",
    "RegistrationOnly"
]

__benchmarking = {
    "_": Benchmarking,
    "seeded": BenchmarkingSeeded,
    "if": BenchmarkingInterference,
    "interference": BenchmarkingInterference,
    "op": OpcodeCount,
    "opcodes": OpcodeCount
}

__data_race = {
    "_": None,
    "access": {
        "single": DataRaceAccessSingle,
        "batch": DataRaceAccessBatch
    },
    "tsv": {
        "single": DataRaceTSVSingle,
        "batch": DataRaceTSVBatch
    }
}

tree: dict = {
    "_": None,
    "bench": __benchmarking,
    "benchmarking": __benchmarking,
    "linux": {
        "_": None,
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
    },
    "data-race": __data_race
}

def nested_dict_str(dictionary, parent_key=""):
    cur_level_keys = []
    for key, value in dictionary.items():
        new_key = f"{parent_key}/{key}" if parent_key else key

        if isinstance(value, dict):
            cur_level_keys.append(nested_dict_str(value, new_key))
        elif value:
            cur_level_keys.append("  \u2022 " + new_key)

    return '\n'.join(cur_level_keys)

def get_runtime(name: str) -> RuntimeManager:
    """Get runtime by name."""
    rt_class = tree
    try:
        for spec in name.split('/'):
            rt_class = rt_class[spec]
    except KeyError:
        raise KeyError("No runtime matching \"{}\".".format(name))

    if isinstance(rt_class, dict):
        rt_class = rt_class["_"]

    if rt_class is None:
        raise NotImplementedError("Runtime {} is not yet implemented.".format(name))
    else:
        return cast(RuntimeManager, rt_class)
