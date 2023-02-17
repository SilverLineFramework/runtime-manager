"""Start Silverline node and runtimes."""

from argparse import ArgumentParser

from manager import Manager
from libsilverline import configure_log, MQTTServer
import interfaces


def _parse():
    p = ArgumentParser(
        description="Launch Silverline module(s).")
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument("-v", "--verbose", default=20, help="Logging level.")
    p.add_argument(
        "-l", "--log", default=None,
        help="Log directory; if not passed, logs are not saved.")

    return p


if __name__ == '__main__':

    args = _parse().parse_args()
    configure_log(args.log, args.verbose)

    rt1 = interfaces.LinuxMinimal(name="min")
    # rt2 = interfaces.LinuxMinimalWAMR(name="wamr")
    # rt3 = interfaces.Benchmarking(name="bench")
    # rt4 = interfaces.OpcodeCount(name="intrp")

    mgr = Manager(
        [rt1], server=MQTTServer.from_config("config.json")
    ).start().run_until_stop()
