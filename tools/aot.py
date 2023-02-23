"""AOT Compilation."""

import os
import logging
import pandas as pd
import subprocess
from multiprocessing.pool import ThreadPool

from rich.progress import Progress

from libsilverline import SilverlineCluster, configure_log, console


_desc = "AOT compile WebAssembly sources for cluster devices."


log_srcs = logging.getLogger("source")
log_tgts = logging.getLogger("target")
log_cmpl = logging.getLogger("compile")


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument(
        "-s", "--source", help="WASM binary source directory.", default="wasm")
    p.add_argument(
        "-o", "--out", help="AOT binary output directory.", default="aot")
    p.add_argument(
        "-v", "--verbose", default=20, type=int, help="Logging level.")
    p.add_argument(
        "-w", "--wamrc", default="./wamrc", help="WAMR compiler path.")
    p.add_argument(
        "-j", "--threads", default=8, help="Compilation threads.", type=int)
    return p


def get_targets(path):
    """Get compilation targets."""
    df = pd.read_csv(path, sep='\t')
    targets = df.groupby(["Target", "Arch"]).size().reset_index()
    targets = list(zip(targets["Target"], targets["Arch"]))
    log_tgts.info("{} Targets:".format(len(targets)))
    for t, a in targets:
        log_tgts.debug("    {}.{}".format(t, a))
    return targets


def get_sources(dir):
    """Get WASM executable files (except for common files)."""
    log_srcs.debug("Expanding directory: {}".format(dir))
    srcs = []
    for p in os.listdir(dir):
        fp = os.path.join(dir, p)
        if os.path.isdir(fp):
            if p != "common":
                srcs += get_sources(fp)
        elif p.endswith(".wasm"):
            srcs.append(fp)
    log_srcs.info("{} Files: {}".format(len(srcs), dir))
    return srcs


def _main(args):

    configure_log(log=None, level=args.verbose)
    cluster = SilverlineCluster.from_config(args.cfg)

    targets = get_targets(cluster.manifest)
    sources = get_sources(args.source)

    jobs = [(t, a, s) for t, a in targets for s in sources]
    log_cmpl.info("Compiling {} Jobs:".format(len(jobs)))

    with Progress(console=console) as progress:
        task = progress.add_task("Compiling...", total=len(jobs))

        def compile(job):
            t, a, s = job

            out = s.replace(
                args.source, os.path.join(args.out, "{}.{}".format(t, a))
            ).replace(".wasm", ".aot")

            os.makedirs(os.path.dirname(out), exist_ok=True)
            subprocess.run([
                args.wamrc, "--target={}".format(t), "--cpu={}".format(a),
                "-o", out, s], stdout=subprocess.DEVNULL)
            progress.update(task, advance=1)

        with ThreadPool(processes=args.threads) as p:
            p.map(compile, jobs)
