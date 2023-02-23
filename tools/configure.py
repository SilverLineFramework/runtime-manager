"""Create configuration."""

import os
import json

from libsilverline import MQTTServer, SilverlineCluster


def _get_platform_data() -> dict:
    try:
        from cpuinfo import get_cpu_info
    except ImportError:
        return {"cpu": {}}

    info = get_cpu_info()

    return {
        "cpu": {
            "cores": info["count"],
            "cpufreq": info["hz_actual"][0]
        },
        "mem": {
            "l1i_size": info["l1_instruction_cache_size"],
            "l1d_size": info["l1_data_cache_size"],
            "l2_size": info["l2_cache_size"],
            "l2_line": info["l2_cache_line_size"],
            "l2_assoc": info["l2_cache_associativity"],
            "l3_size": info["l3_cache_size"],
            "total": os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
        }
    }


_desc = "Create node/cluster configuration file."


def _parse(p):
    p.add_argument(
        "-o", "--out", default="config.json",
        help="Output configuration path; will overwrite if already exists.")

    MQTTServer.make_args(p)
    SilverlineCluster.make_args(p)

    g = p.add_argument_group("CPU")
    g.add_argument(
        "-t", "--target", default=None,
        help="LLVM compilation target architecture name.")
    g.add_argument(
        "-c", "--cpu", default=None,
        help="LLVM compilation CPU microarchitecture name.")

    return p


def _main(args):
    platform = _get_platform_data()
    platform["cpu"]["target"] = args.target
    platform["cpu"]["cpu"] = args.cpu

    cfg = {
        **MQTTServer.make_config(args),
        **SilverlineCluster.make_config(args),
        "platform": platform
    }

    if os.path.dirname(args.out):
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(cfg, f, indent=4)
