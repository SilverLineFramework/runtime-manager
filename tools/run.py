"""Run module."""

import os
import logging

from libsilverline import SilverlineClient, configure_log


_desc = "Launch Silverline module(s)."


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument("-v", "--verbose", default=20, help="Logging level.")
    p.add_argument(
        "-r", "--runtime", nargs='+', default=None,
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
    p.add_argument("-d", "--dirs", nargs='+', default=None, help="WASI dirs.")
    p.add_argument(
        "--period", type=int, default=10 * 1000 * 1000,
        help="Period for sched_deadline, in nano seconds.")
    p.add_argument(
        "--utilization", type=float, default=None,
        help="Utilization for sched_deadline. If 0.0, uses CFS.")
    p.add_argument(
        "--repeat", type=int, default=None,
        help="Number of times to run module if benchmarking.")
    p.add_argument(
        "--limit", type=float, default=60.0, help="Benchmarking time limit.")
    p.add_argument(
        "--engine", default=None, help="WASM engine to use for benchmarking.")
    p.add_argument(
        "--fault_crash", default=None,
        help="Action to perform if the module crashes (ignore, restart).")
    return p


def _module_args(file, args):
    data = {"argv": args.argv, "env": args.env}
    if args.utilization is not None:
        c = int(args.utilization * args.period)
        data["resources"] = {"period": args.period, "runtime": c}
    for kw in ["repeat", "engine", "limit", "dirs", "fault_crash"]:
        val = getattr(args, kw)
        if val is not None:
            data[kw] = val
    return data


def _main(args, default_runtime=None):
    configure_log(log=None, level=args.verbose)
    log = logging.getLogger("cli")
    client = SilverlineClient.from_config(args.cfg, name="cli").start()

    if default_runtime is not None:
        args.runtime = default_runtime

    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            if len(args.file) <= 1:
                client.create_module(
                    rtid, args.file[0], name=args.name,
                    args=_module_args(args.file[0], args))
            else:
                client.create_module_batch(
                    rtid, args.file, name=[args.name for _ in args.file],
                    args=[_module_args(f, args) for f in args.file])

    client.stop()
