"""Copy file to node."""

import os
import pandas as pd

from libsilverline import SilverlineCluster, configure_log

from ._ssh import run_command, Device


_desc = "Copy file to cluster."


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument(
        "-s", "--src", help="Source filepath.")
    p.add_argument("-d", "--dst", help="Destination filepath.")
    p.add_argument(
        "-v", "--verbose", default=21, type=int, help="Logging level.")
    return p


def _main(args, put=True):

    configure_log(log=None, level=args.verbose)
    cluster = SilverlineCluster.from_config(args.cfg)

    def execute(connection, device):
        connection.put(device.format(args.src), remote=device.format(args.dst))

    targets = pd.read_csv(cluster.manifest, sep='\t')
    devices = set(Device(cluster, dict(row)) for _, row in targets.iterrows())

    print("Copying files to {} devices: {} --> {}".format(
        len(devices), args.src, args.dst))
    run_command(execute, devices, ignore_err=args.ignore_err, sync=args.sync)
