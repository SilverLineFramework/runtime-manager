"""Copy file from node."""

import os
import pandas as pd

from libsilverline import SilverlineCluster, configure_log

from ._ssh import run_command, Device


_desc = "Copy file from cluster."


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument(
        "-s", "--src", help="Source filepath.")
    p.add_argument("-d", "--dst", help="Destination filepath.")
    p.add_argument(
        "-v", "--verbose", default=21, type=int, help="Logging level.")
    p.add_argument(
        "-i", "--ignore_err", default=False, action='store_true',
        help="Ignore errors encountered during execution.")
    return p


def _main(args, put=True):

    configure_log(log=None, level=args.verbose)
    cluster = SilverlineCluster.from_config(args.cfg)

    def execute(connection, device):
        connection.get(device.format(args.src), local=device.format(args.dst))

    targets = pd.read_csv(cluster.manifest, sep='\t')
    devices = set(Device(cluster, dict(row)) for _, row in targets.iterrows())

    print("Copying files from {} devices: {} --> {}".format(
        len(devices), args.src, args.dst))
    run_command(execute, devices, ignore_err=args.ignore_err, sync=args.sync)
