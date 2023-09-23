"""Run benchmarking.

Use with `index.py` to run benchmark suites. For example::

    hc benchmark -f `hc index -p benchmarks -d wasm/polybench/small`
    hc benchmark -f `hc index -p benchmarks -d wasm/mibench -r wasm=aot`
"""

import os
from functools import partial
import json
import logging
import pandas as pd
import random

from libsilverline import SilverlineClient, SilverlineCluster, configure_log


_desc = "Run data-race benchmarking (runtimes x files x instrumentation-density) ."



def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument("-v", "--verbose", default=20, type=int, help="Logging level.")
    p.add_argument(
        "-r", "--runtime", nargs='+', default=None,
        help="Target runtime names, uuids, or last characters of uuid.")
    p.add_argument(
        "-f", "--file", nargs="+", default=["wasm/apps/helloworld.wasm"],
        help="Target file paths, relative to WASM/WASI base directory.")
    p.add_argument(
        "-i", "--instdensity", default=["0"], nargs='+',
        help="Instrumentation density to apply.")
    p.add_argument(
        "--repeat", type=int, default=100,
        help="Number of times to run module if benchmarking.")
    p.add_argument(
        "--limit", type=float, default=60.0, help="Benchmarking time limit.")
    p.add_argument(
        "--ilimit", type=float, default=None,
        help="Time limit for each run (even when repeated).")
    p.add_argument(
        "--argv", default=[], nargs='+', help="Argv to pass to the module.")
    p.add_argument(
        "--argfile", default=None, help="Json file containing list of "
        "arguments (list of list) to pass to each module (overrides --argv).")
    p.add_argument(
        "--norepeat", default=False, action='store_true',
        help="Run each argv as different entries in the same benchmark.")
    return p


def cross(func, **kwargs):
    """Create cross product list by applying func to iterable args/kwargs."""
    out = [{}]
    for key, it in kwargs.items():
        out = [{key: item, **k} for k in out for item in it]
    return [func(**k) for k in out]



def _main(args):
    configure_log(log=None, level=args.verbose)
    log = logging.getLogger("cli")
    client = SilverlineClient.from_config(args.cfg, name="cli").start()

    _manifest = pd.read_csv(
        SilverlineCluster.from_config(args.cfg).manifest, sep='\t')
    manifest = {row["Device"]: row for _, row in _manifest.iterrows()}

    if args.runtime is None:
        args.runtime = list(_manifest["Device"])
    if args.argfile:
        with open(args.argfile) as f:
            argv = json.load(f)
    else:
        argv = [args.argv]

    def _file(file=None, instdensity=None, **_):
        return file

    def _modulename(file=None, instdensity=None, **_):
        splits = [file.split("/")[-1].split('.')[0]]
        if args.argfile:
            splits.append(args.argfile.split("/")[-1].split(".")[0])
        if isinstance(instdensity, list):
            return ".".join(splits)
        else:
            return ".".join(splits + [instdensity])

    def _moduleargs(instdensity=None, arg=None, **_):
        return {
            "argv": arg, "repeat": args.repeat,
            "limit": args.limit, "ilimit": args.ilimit, "dirs": ["."],
            "instrument": {
                "scheme": "memaccess-stochastic",
                "instargs": [instdensity, "1"],
            }
        }

    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            if args.norepeat:
                random.shuffle(argv)
                iters = {"file": args.file, "instdensity": args.instdensity}
                partials = {"arg": argv}
            else:
                iters = {"file": args.file, "instdensity": args.instdensity, "arg": argv}
                partials = {}

            files = cross(partial(_file, **partials), **iters)
            names = cross(partial(_modulename, **partials), **iters)
            module_args = cross(partial(_moduleargs, **partials), **iters)

            client.create_module_batch(rtid, files, names, module_args)

    client.stop()
