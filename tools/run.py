"""Run and module."""

import logging
from argparse import ArgumentParser
from common import SilverlineClient, configure_log


def _parse():
    p = ArgumentParser(
        description="Launch Silverline module(s).")
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument("-v", "--verbose", default=20, help="Logging level.")
    p.add_argument(
        "-r", "--runtime", nargs='+', default=["test"],
        help="Target runtime names, uuids, or last characters of uuid.")
    p.add_argument(
        "-n", "--name", default="module",
        help="Module short (human-readable) name.")
    p.add_argument(
        "-f", "--file", nargs="+", default=["wasm/apps/helloworld.wasm"],
        help="Target file paths, relative to WASM/WASI base directory")
    p.add_argument(
        "-a", "--argv", nargs='+', default=[],
        help="Argument passthrough to the module.")
    p.add_argument(
        "-e", "--env", nargs='+', default=[],
        help="Environment variables to set.")
    p.add_argument(
        "-t", "--period", type=int, default=10 * 1000 * 1000,
        help="Period for sched_deadline, in nano seconds.")
    p.add_argument(
        "-u", "--utilization", type=float, default=0.0,
        help="Utilization for sched_deadline. If 0.0, uses CFS.")
    p.add_argument(
        "-k", "--repeat", type=int, default=0,
        help="Number of times to run module if benchmarking.")

    return p


if __name__ == '__main__':
    args = _parse().parse_args()

    configure_log(log=None, level=args.verbose)
    log = logging.getLogger("cli")
    client = SilverlineClient.from_config(args.cfg, connect=True, name="cli")
    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            for f in args.file:
                mid = client.create_module(
                    runtime=rtid, name=args.name, file=f, argv=args.argv,
                    env=args.env, period=args.period,
                    utilization=args.utilization, repeat=args.repeat)
                log.info("Created: {}:{} --> {}:{}".format(
                    f, mid[-4:], rt, rtid[-4:]))

    client.loop_stop()
