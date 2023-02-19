"""Start Silverline node and runtimes."""

import uuid
import json
import platform
from argparse import ArgumentParser

from libsilverline import configure_log, MQTTServer

from manager import Manager
import interfaces


_desc = "Start Silverline runtime manager and runtime(s)."


def _parse(p):
    p.add_argument("-n", "--name", help="Node name.", default="node")
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument("-v", "--verbose", default=20, help="Logging level.")
    p.add_argument(
        "-g", "--cpus", nargs='+', default=None, help="CPUs to assign to "
        "cgroup; if not passed, uses the default cgroup.")
    p.add_argument(
        "-l", "--log", default=None,
        help="Log directory; if not passed, logs are not saved.")
    p.add_argument(
        "-r", "--runtimes", nargs='+', help="Runtimes to start.",
        default=["linux/min/wasmer"])

    return p


def _main(args):
    configure_log(args.log, args.verbose)

    with open('config.json') as f:
        cfg = json.load(f)

    runtime_cfg = {
        "platform": cfg.get("platform", {}),
        "metadata": {"host": platform.node()}
    }

    def _make_runtime(rt, cpu):
        rt_class = interfaces.get_runtime(rt)
        return rt_class(
            name="{}.{}".format(args.name, rt_class.DEFAULT_SHORTNAME),
            rtid=str(uuid.uuid4()), cfg=runtime_cfg, cpus=cpu)

    if args.cpus is None:
        cpus = [None] * len(args.runtimes)
    runtimes = [_make_runtime(rt, cpu) for rt, cpu in zip(args.runtimes, cpus)]

    mqtt = MQTTServer.from_config(cfg)
    Manager(runtimes, server=mqtt, name=args.name).start().run_until_stop()


if __name__ == '__main__':
    _main(_parse(ArgumentParser(description=_desc)).parse_args())
