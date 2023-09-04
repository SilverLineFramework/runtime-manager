"""Profiling data packet types."""

import numpy as np
import json
import struct
from collections import namedtuple, OrderedDict


def benchmarking(payload):
    """Basic benchmarking."""
    data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 3)
    return {
        "utime": data[:, 0],
        "stime": data[:, 1],
        "maxrss": data[:, 2]
    }


def seeded(payload):
    """Benchmarking with a random seed."""
    data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 4)
    return {
        "utime": data[:, 0],
        "stime": data[:, 1],
        "maxrss": data[:, 2],
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


def dr_access(payload):
    """Data Race Access (Stage 1)."""
    parsed = {}
    def parse_pl(fmt, payload, offset):
        res = struct.unpack_from(fmt, payload, offset)
        offset += struct.calcsize(fmt)
        return res, offset 

    def parse_defset(payload, offset):
        (ct,), offset = parse_pl('<I', payload, offset)
        shared_v, offset = parse_pl(f"<{ct}I", payload, offset)
        return list(set(shared_v)), offset

    offset = 0
    (parsed['cpu_time'],), offset = parse_pl('<Q', payload, offset)
    # Read shared instructions
    parsed['shared_insts'], offset = parse_defset(payload, offset)
    # Read shared addrs
    parsed['shared_addrs'], offset = parse_defset(payload, offset)

    AccessRecord = namedtuple('AccessRecord', ['tid', 'has_write', 'inst_idxs'])
    parsed['partials'] = {}
    while offset != len(payload):
        # Read partials
        fields, offset = parse_pl('<IQ?I', payload, offset)
        addr, acc_tup = fields[0], fields[1:]
        acc = AccessRecord._make(acc_tup)
        entry_list, offset = parse_pl(f"<{acc.inst_idxs}I", payload, offset)
        acc = acc._replace(inst_idxs=entry_list)
        parsed['partials'][addr] = acc

    return parsed

