"""Set CPU frequency policy."""

import os
from argparse import ArgumentParser

from manager import linux


def _init_cpufreq(clock=0.0, boost=False):
    sysfs = linux.SysFS("/sys/devices/system/cpu")

    # AMD systems: disable boost
    sysfs.write(1 if boost else 0, "cpufreq/boost", optional=True)
    # Intel systems: enable no_turbo in intel_pstate
    sysfs.write(0 if boost else 1, "intel_pstate/no_turbo", optional=True)

    # All systems: set fixed frequency at slight underclock
    max_freq = None
    cpufreq_max = None
    policies = [
        p for p in os.listdir(sysfs.path("cpufreq")) if p.startswith("policy")]
    for p in policies:
        # Set performance mode (always use max freq)
        sysfs.write("performance", "cpufreq", p, "scaling_governor")

        # Underclock
        cpufreq_min = sysfs.read("cpufreq", p, "cpuinfo_min_freq")
        cpufreq_max = sysfs.read("cpufreq", p, "cpuinfo_max_freq")
        max_freq = int(max(cpufreq_max * (1 - clock), cpufreq_min))
        sysfs.write(max_freq, "cpufreq", p, "scaling_max_freq")
        sysfs.write(max_freq, "cpufreq", p, "scaling_min_freq")

    return cpufreq_max, max_freq


_desc = "Set CPU frequency policy."


def _parse(p):
    p.add_argument(
        "-c", "--clock", default=0.0, type=float,
        help="Clock frequency underclock: underclocks max_freq to max_freq * "
        "clock, with a floor of min_freq.")
    p.add_argument(
        "-b", "--boost", default=False, action='store_true',
        help="Enable use of boost clock (clock frequencies that cannot be "
        "sustained indefinitely.")
    return p


def _main(args):
    try:
        max_freq, set_freq = _init_cpufreq(clock=args.clock, boost=args.boost)
        print("max_freq: {} -> {}".format(max_freq, set_freq))
    except PermissionError:
        print("Warning: could not set cpufreq policy: root is required.")


if __name__ == '__main__':
    args = _parse(ArgumentParser()).parse_args()
    _main(args)
