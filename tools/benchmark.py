"""Run benchmarking.

Use with `index.py` to run benchmark suites. For example::

    hc benchmark -f `hc index -p benchmarks -d wasm/polybench/small`
    hc benchmark -f `hc index -p benchmarks -d wasm/mibench -r wasm=aot`
"""

import os
import json
import logging
import pandas as pd
import random

from libsilverline import SilverlineClient, SilverlineCluster, configure_log


_desc = "Run (runtimes x files x engines) benchmarking."


ENGINES = {
    "native": "native",
    "iwasm-aot": "./runtimes/bin/iwasm",
    "wasmer-cranelift": "./runtimes/bin/wasmer run --cranelift",
    "wasmer-llvm": "./runtimes/bin/wasmer run --llvm",
    "wasmer-singlepass": "./runtimes/bin/wasmer run --singlepass",
    "iwasm": "./runtimes/bin/iwasm",
    "wasmedge": "./runtimes/bin/wasmedge",
    "wasmedge-aot": "./runtimes/bin/wasmedge",
    "wasmtime": "./runtimes/bin/wasmtime run --wasm-features all",
    "iwasm-wali": "./runtimes-bin/iwasm-wali --stack-size=262144"
}


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
        "--engine", nargs="+", default=None,
        help="WASM engine to use for benchmarking.")
    p.add_argument(
        "--shuffle", default=False, action='store_true',
        help="Shuffle modules on each runtime before running.")
    p.add_argument(
        "--argfile", default=None, help="Json file containing list of "
        "arguments (list of list) to pass to each module.")
    return p


def _main(args):
    configure_log(log=None, level=args.verbose)
    log = logging.getLogger("cli")
    client = SilverlineClient.from_config(args.cfg, name="cli").start()

    if args.runtime is None:
        args.runtime = list(pd.read_csv(
            SilverlineCluster.from_config(args.cfg).manifest, sep='\t'
        )["Device"])
    if args.engine is None:
        args.engine = [
            "wasmer-llvm", "wasmer-cranelift", "wasmer-singlepass", "iwasm",
            "wasmedge", "wasmtime"]

    if args.argfile:
        with open(args.argfile) as f:
            argv = json.load(f)
    else:
        argv = [[]]

    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            files = [
                file
                for file in args.file for _ in args.engine for _ in argv]
            names = [
                file.split("/")[-1].split('.')[0] + "." + engine
                for file in args.file for engine in args.engine for _ in argv]
            module_args = [
                {
                    "engine": ENGINES[engine], "argv": arg,
                    "repeat": args.repeat, "limit": args.limit
                }
                for _ in args.file for engine in args.engine for arg in argv]

            if args.shuffle:
                tmp = list(zip(files, names, module_args))
                random.shuffle(tmp)
                files, names, module_args = zip(*tmp)

            client.create_module_batch(rtid, files, names, module_args)

    client.stop()
