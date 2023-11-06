"""Start Silverline node and runtimes."""

import uuid
import json
import platform
from argparse import ArgumentParser, RawTextHelpFormatter

from libsilverline import configure_log, MQTTServer

from manager import Manager
import interfaces


_desc = "Start Silverline runtime manager and runtime(s)."

def _parse(p):
    p.add_argument("-n", "--name", help="Node name.", default="node")
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument(
        "-v", "--verbose", type=int, default=20, help="Logging level.")
    p.add_argument(
        "-g", "--cpus", nargs='+', default=None, help="CPUs to assign to "
        "cgroup; if not passed, uses the default cgroup.")
    p.add_argument(
        "-l", "--log", default=None,
        help="Log directory; if not passed, logs are not saved.")
    p.add_argument(
        "-r", "--runtimes", nargs='+', 
        help="Runtimes to start. Supported options: \n" + interfaces.nested_dict_str(interfaces.tree),
        default=["linux/min/wasmer"])
    p.add_argument(
        "-a", "--rtargs", nargs='*',
        help="List of arguments to pass to runtime",
        default=[])

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
        if len(args.runtimes) == 1:
            name = args.name
        else:
            name = "{}.{}".format(args.name, rt_class.DEFAULT_SHORTNAME)
        return rt_class(
            name=name, rtid=str(uuid.uuid4()), cfg=runtime_cfg, cpus=cpu, rtargs=args.rtargs)

    if args.cpus is None:
        args.cpus = [None] * len(args.runtimes)
    runtimes = [
        _make_runtime(rt, cpu) for rt, cpu in zip(args.runtimes, args.cpus)]

    mqtt = MQTTServer.from_config(cfg)
    Manager(runtimes, server=mqtt, name=args.name).start().run_until_stop()


if __name__ == '__main__':
    _main(_parse(ArgumentParser(description=_desc, formatter_class=RawTextHelpFormatter)).parse_args())
