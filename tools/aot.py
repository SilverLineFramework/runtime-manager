"""AOT Compilation."""

import os
import logging
import pandas as pd
import subprocess
from multiprocessing.pool import ThreadPool
import logging

from rich.progress import Progress
from libsilverline import SilverlineCluster, configure_log, console


_desc = "AOT compile WebAssembly sources for cluster devices."


def _iwasm(row, src):
    WAMRC = "./runtimes/bin/wamrc"
    dst = src.replace("wasm/", "aot/iwasm/{Target}-{Arch}/".format(**row))
    return dst, "{wamrc} --target={Target} --cpu={Arch} -o {dst} {src}".format(
        wamrc=WAMRC, dst=dst, src=src, **row)


def _wasmer(row, src, mode="cranelift"):
    dst = src.replace(
        "wasm/", "aot/wasmer-{mode}/{Triple}/".format(mode=mode, **row))
    return dst, (
        "wasmer compile {src} -o {dst} --target {Triple} --enable-all --{mode}"
    ).format(dst=dst, mode=mode, src=src, **row)


def _wasmtime(row, src):
    dst = src.replace("wasm/", "aot/wasmtime/{Triple}-{Arch}/".format(**row))
    cmd = (
        "wasmtime compile {src} -o {dst} --wasm-features all --target {Triple}"
    ).format(dst=dst, src=src, **row)
    if row["Triple"] == "x86_64-unknown-linux-gnu":
        cmd += " --cranelift-enable {Arch}".format(**row)
    return dst, cmd


log_srcs = logging.getLogger("source")
log_cmpl = logging.getLogger("compile")


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument(
        "-p", "--path", default=".",
        help="Directory with wasm files in wasm/; outputs to aot/.")
    p.add_argument(
        "-o", "--out", help="AOT binary output directory.", default="aot")
    p.add_argument(
        "-v", "--verbose", default=20, type=int, help="Logging level.")
    p.add_argument(
        "-j", "--threads", default=8, help="Compilation threads.", type=int)
    return p


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


def get_commands(manifest, sources):
    """Get compilation targets."""
    df = pd.read_csv(manifest, sep='\t')
    cmds = []
    for _, row in df.iterrows():
        for s in sources:
            cmds += [
                _iwasm(row, s), _wasmtime(row, s), _wasmer(row, s, "llvm"),
                _wasmer(row, s, "cranelift")]

    return list(set(cmds))


def execute(args, jobs):
    """Run compilation."""
    log_cmpl.info("Compiling {} Jobs:".format(len(jobs)))

    with Progress(console=console) as progress:
        task = progress.add_task("Compiling...", total=len(jobs))

        def compile(job):
            dst, cmd = job
            if os.path.exists(dst):
                log_cmpl.info("Already exists: {}. Skipping.".format(dst))
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                subprocess.run(cmd.split(" "), stdout=subprocess.DEVNULL)
                progress.update(task, advance=1)

        with ThreadPool(processes=args.threads) as p:
            p.map(compile, jobs)


def _main(args):
    configure_log(log=None, level=args.verbose)
    cluster = SilverlineCluster.from_config(args.cfg)

    sources = get_sources(os.path.join(args.path, "wasm"))
    commands = get_commands(cluster.manifest, sources)
    execute(args, commands)
