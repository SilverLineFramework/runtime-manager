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


_desc = "Run (runtimes x files x engines) benchmarking."


DEFAULT_ENGINES = [
    "wasmer-j-ll", "wasmer-j-cl", "wasmer-j-singlepass", "iwasm-i",
    "wasmedge-i", "wasmtime-j", "wasm3-i"
]


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument("-v", "--verbose", default=20, help="Logging level.")
    p.add_argument(
        "-r", "--runtime", nargs='+', default=None,
        help="Target runtime names, uuids, or last characters of uuid.")
    p.add_argument(
        "-f", "--file", nargs="+", default=["wasm/apps/helloworld.wasm"],
        help="Target file paths, relative to WASM/WASI base directory.")
    p.add_argument(
        "--repeat", type=int, default=100,
        help="Number of times to run module if benchmarking.")
    p.add_argument(
        "--limit", type=float, default=60.0, help="Benchmarking time limit.")
    p.add_argument(
        "--ilimit", type=float, default=None,
        help="Time limit for each run (even when repeated).")
    p.add_argument(
        "--engine", nargs="+", default=DEFAULT_ENGINES,
        help="WASM engine(s) to use for benchmarking.")
    p.add_argument(
        "--shuffle", default=False, action='store_true',
        help="Shuffle modules on each runtime before running.")
    p.add_argument(
        "--argv", default=[], nargs='+', help="Argv to pass to the module.")
    p.add_argument(
        "--argfile", default=None, help="Json file containing list of "
        "arguments (list of list) to pass to each module (overrides --argv).")
    p.add_argument(
        "--norepeat", default=False, action='store_true',
        help="Run each argv as different entries in the same benchmark.")
    p.add_argument(
        "--eshuffle", default=False, action='store_true',
        help="Assign random engine to each benchmark, similar to norepeat.")
    p.add_argument(
        "--max_seed", default=9999, type=int,
        help="Maximum seed for seeded benchmarking.")
    p.add_argument(
        "--dirmode", default=False, action='store_true',
        help="Generate arguments by indexing into directory (last arg)"
        "for seeded benchmarking instead of passing directly.")
    p.add_argument(
        "--scriptmode", default=False, action='store_true',
        help="Generate arguments using python script (last arg) that takes a "
        "seed for seeded benchmarking instead of passing directly.")
    p.add_argument(
        "--interference", default=0, type=int,
        help="Enable interference mode for this many ways.")
    return p


def cross(func, **kwargs):
    """Create cross product list by applying func to iterable args/kwargs."""
    out = [{}]
    for key, it in kwargs.items():
        out = [{key: item, **k} for k in out for item in it]
    return [func(**k) for k in out]


def supported_runtimes(args, manifest, device):
    """Get list of supported (wasm) runtimes on this device."""
    row = manifest.get(device)
    if row is None:
        return args.engine
    return [k for k in args.engine if row.get(k) == 'x']


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

    def _file(file=None, engine=None, **_):
        return file

    def _modulename(file=None, engine=None, **_):
        splits = [file.split("/")[-1].split('.')[0]]
        if args.argfile:
            splits.append(args.argfile.split("/")[-1].split(".")[0])
        if isinstance(engine, list):
            return ".".join(splits)
        else:
            return ".".join(splits + [engine])

    def _moduleargs(engine=None, arg=None, **_):
        return {
            "engine": engine, "argv": arg, "repeat": args.repeat,
            "limit": args.limit, "ilimit": args.ilimit, "dirs": ["."],
            "dirmode": args.dirmode, "scriptmode": args.scriptmode,
            "max_seed": args.max_seed
        }

    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            if args.norepeat:
                random.shuffle(argv)
                iters = {"file": args.file, "engine": args.engine}
                partials = {"arg": argv}
            elif args.eshuffle:
                random.shuffle(argv)
                supported = supported_runtimes(args, manifest, rt)
                randengine = [random.choice(supported) for _ in argv]
                iters = {"file": args.file}
                partials = {"arg": argv, "engine": randengine}
            elif args.interference > 0:
                ifset = [args.file.copy() for _ in range(args.interference)]
                for x in ifset:
                    random.shuffle(x)
                files = [":".join(x) for x in list(zip(*ifset))]
                iters = {"file": files, "engine": args.engine, "arg": argv}
            else:
                iters = {"file": args.file, "engine": args.engine, "arg": argv}
                partials = {}

            files = cross(partial(_file, **partials), **iters)
            names = cross(partial(_modulename, **partials), **iters)
            module_args = cross(partial(_moduleargs, **partials), **iters)

            if args.shuffle:
                tmp = list(zip(files, names, module_args))
                random.shuffle(tmp)
                files, names, module_args = zip(*tmp)

            client.create_module_batch(rtid, files, names, module_args)

    client.stop()
