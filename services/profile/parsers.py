"""Profiling data packet types."""

import numpy as np
import json


def benchmarking(payload):
    """Basic benchmarking."""
    data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 3)
    return {
        "wall": data[:, 0],
        "utime": data[:, 1],
        "stime": data[:, 2]
    }


def seeded(payload):
    """Benchmarking with a random seed."""
    data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 4)
    return {
        "wall": data[:, 0],
        "utime": data[:, 1],
        "stime": data[:, 2],
        "seed": data[:, 3]
    }


def opcodes(payload):
    """Opcode counting."""
    data = np.frombuffer(payload, dtype=np.uint64)
    return {"opcodes": data}


def instrumented(payload):
    """Instrumentation counts."""
    data = np.frombuffer(payload, dtype=np.uint32)
    return {"counts": data}


def deployed(payload):
    """Instrumentation from deployed modules."""
    data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 8)
    start = (
        data[:, 0].astype(np.uint64)
        | (data[:, 1].astype(np.uint64) << np.uint64(32)))
    return {
        "start": start,
        "wall": data[:, 2],
        "cpu_time": data[:, 3],
        "memory": data[:, 4],
        "ch_mqtt": data[:, 5],
        "ch_local": data[:, 6],
        "ch_out": data[:, 7]
    }


def interference(payload):
    """Explicit instrumentation benchmarking."""
    return json.loads(payload)


def raw32(payload):
    """Save raw 32-bit integers."""
    data = np.frombuffer(payload, dtype=np.uint32)
    return {"data": data}


def raw64(payload):
    """Save raw 64-bit integers."""
    data = np.frombuffer(payload, dtype=np.uint64)
    return {"data": data}
