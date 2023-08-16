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


ENGINES = {
    "native": "native",
    "iwasm": "./runtimes/bin/iwasm -v=0 --",
    "iwasm-aot": "./runtimes/bin/iwasm -v=0 --",
    "wasmer-cranelift": "./runtimes/bin/wasmer run --cranelift --",
    "wasmer-llvm": "./runtimes/bin/wasmer run --llvm --",
    "wasmer-singlepass": "./runtimes/bin/wasmer run --singlepass --",
    "wasmedge": "./runtimes/bin/wasmedge",
    "wasmedge-aot": "./runtimes/bin/wasmedge",
    "wasmtime": "./runtimes/bin/wasmtime run --wasm-features all --",
    "wasm3": "./runtimes/bin/wasm3",
}

# Defaults can all operate on normal wasm files without AOT preprocessing.
DEFAULT_ENGINES = [
    "wasmer-llvm", "wasmer-cranelift", "wasmer-singlepass", "iwasm",
    "wasmedge", "wasmtime"
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
        "--engine", nargs="+", default=DEFAULT_ENGINES,
        help="WASM engine to use for benchmarking.")
    p.add_argument(
        "--shuffle", default=False, action='store_true',
        help="Shuffle modules on each runtime before running.")
    p.add_argument(
        "--argfile", default=None, help="Json file containing list of "
        "arguments (list of list) to pass to each module.")
    p.add_argument(
        "--norepeat", default=False, action='store_true',
        help="Run each argv as different entries in the same benchmark.")
    return p


def cross(func, *args, **kwargs):
    """Create cross product list by applying func to iterable args/kwargs."""
    out = [((), {})]
    for it in args:
        out = [((*a, item), k) for a, k in out for item in it]
    for key, it in kwargs.items():
        out = [(a, {key: item, **k}) for a, k in out for item in it]
    return [func(*a, **k) for a, k in out]


def _main(args):
    configure_log(log=None, level=args.verbose)
    log = logging.getLogger("cli")
    client = SilverlineClient.from_config(args.cfg, name="cli").start()

    if args.runtime is None:
        args.runtime = list(pd.read_csv(
            SilverlineCluster.from_config(args.cfg).manifest, sep='\t'
        )["Device"])
    if args.argfile:
        with open(args.argfile) as f:
            argv = json.load(f)
    else:
        argv = [[]]

    # Argument constructors
    def _file(file=None, **_):
        return file

    def _modulename(file=None, engine=None, **_):
        return file.split("/")[-1].split('.')[0] + "." + engine

    def _moduleargs(engine=None, arg=None, **_):
        return {
            "engine": ENGINES[engine], "argv": arg,
            "repeat": args.repeat, "limit": args.limit, "dirs": ["."]}

    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            if args.argrepeat:
                iters = {"file": args.file, "engine": args.engine, "arg": argv}
                module_args = cross(_moduleargs, **iters)
            else:
                iters = {"file": args.file, "engine": args.engine}
                module_args = cross(partial(_moduleargs, arg=argv), iters)

            files = cross(_file, **iters)
            names = cross(_modulename, **iters)

            if args.shuffle:
                tmp = list(zip(files, names, module_args))
                random.shuffle(tmp)
                files, names, module_args = zip(*tmp)

            client.create_module_batch(rtid, files, names, module_args)

    client.stop()
