"""Run benchmarking."""

import os
import logging
import pandas as pd

from libsilverline import SilverlineClient, SilverlineCluster, configure_log


_desc = "Run (runtimes x files x engines) benchmarking."


ENGINES = {
    "native": "native",
    "wasmer-cranelift": "wasmer run --cranelift",
    "wasmer-llvm": "wasmer run --llvm",
    "wasmer-singlepass": "wasmer run --singlepass",
    "wasmtime": "wasmtime run --wasm-features all",
    "iwasm": "./runtimes/bin/iwasm",
    "iwasm-aot": "./runtimes/bin/iwasm",
    "wasmedge": "wasmedge"
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
        help="Target file paths, relative to WASM/WASI base directory")
    p.add_argument(
        "--repeat", type=int, default=100,
        help="Number of times to run module if benchmarking.")
    p.add_argument(
        "--limit", type=float, default=60.0, help="Benchmarking time limit.")
    p.add_argument(
        "--engine", nargs="+", default=None,
        help="WASM engine to use for benchmarking.")
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
        args.engine = list(ENGINES.keys())

    for rt in args.runtime:
        rtid = client.infer_runtime(rt)
        if rtid is None:
            log.error("Could not find runtime: {}".format(rt))
        else:
            files = [file for file in args.file for _ in args.engine]
            names = [
                file.split("/")[-1].split('.')[0] + "." + engine
                for file in args.file for engine in args.engine]
            args = [
                {
                    "engine": ENGINES[engine],
                    "repeat": args.repeat, "limit": args.limit
                } for _ in args.file for engine in args.engine]
            client.create_module_batch(rtid, files, names, args)

    client.stop()
