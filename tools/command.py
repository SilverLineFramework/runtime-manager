"""SSH Utilities."""

import json
import pandas as pd
from libsilverline import SilverlineCluster, configure_log

from ._ssh import run_command, Device


_desc = "Execute command on cluster using SSH."


def _parse(p):
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument(
        "-x", "--command", help="Command to run.", default="echo {name}")
    p.add_argument(
        "-v", "--verbose", default=40, type=int, help="Logging level.")
    return p


def _main(args):

    configure_log(log=None, level=args.verbose)

    with open(args.cfg) as f:
        cfg = json.load(f)
    cluster = SilverlineCluster.from_config(cfg)

    def execute(connection, device):
        connection.run(device.format(args.command), out_stream=device.stream())

    targets = pd.read_csv(cluster.manifest, sep='\t')
    devices = set(Device(cluster, dict(row)) for _, row in targets.iterrows())

    run_command(execute, devices, ignore_err=False, sync=True)
