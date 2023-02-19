"""Get cluster status."""

import json
from argparse import ArgumentParser
import subprocess
import pandas as pd
from multiprocessing.pool import ThreadPool

from rich.console import Console
from rich.table import Table
from rich.text import Text

from libsilverline import SilverlineClient, SilverlineCluster, configure_log


_desc = "List nodes and node status."


def _get_status(row, suffix):
    row = row[1]
    if row['Type'] in {'linux', 'orchestrator'}:
        return subprocess.run(
            ["ping", "-c", "1", "-W", "1", row['Device'] + suffix],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0
    else:
        return None


def _table(status, runtimes, uuids, targets):
    STATUS_TEXT = {
        True: Text("up", style="bold bright_green"),
        False: Text("down", style="bold bright_red"),
        None: Text("--", style="bold bright_white")
    }
    RUNTIME_TEXT = {
        True: Text("up", style="bold bright_green"),
        False: Text("down", style="bold bright_red"),
        None: Text("n/a", style="bold bright_blue")
    }

    table = Table()
    columns = ["Device", "Node", "Runtime", "UUID", "Model", "CPU", "Target", "Arch"]
    for column in columns:
        table.add_column(Text(column, style="bold"), justify="left")

    for s, rt, uuid, (_, row) in zip(status, runtimes, uuids, targets.iterrows()):
        table.add_row(
            row["Device"],
            STATUS_TEXT[s],
            RUNTIME_TEXT[rt],
            uuid[-4:],
            row['Model'],
            row['CPU'],
            row['Target'],
            row['Arch']
        )

    Console().print(table)


def _parse(p):
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument(
        "-v", "--verbose", default=40, type=int, help="Logging level.")
    return p


def _main(args):
    configure_log(log=None, level=args.verbose)

    with open(args.cfg) as f:
        cfg = json.load(f)

    client = SilverlineClient.from_config(cfg).start()

    cluster = SilverlineCluster.from_config(cfg)
    targets = pd.read_csv(cluster.manifest, sep='\t')

    with ThreadPool(processes=len(targets)) as pool:
        status = pool.map(
            lambda x: _get_status(x, cluster.domain), list(targets.iterrows()))

    try:
        runtimes = client.get_runtimes()
        rt_dict = {rt["name"]: rt["uuid"] for rt in runtimes}
        runtimes = [row["Device"] in rt_dict for _, row in targets.iterrows()]
        uuids = [rt_dict[row["Device"]] for _, row in targets.iterrows()]
    except Exception as e:
        runtimes = [None for _ in targets.iterrows()]
        uuids = ["-" for _ in targets.iterrows()]

    _table(status, runtimes, uuids, targets)


if __name__ == '__main__':
    _main(_parse(ArgumentParser(description=_desc)).parse_args())
