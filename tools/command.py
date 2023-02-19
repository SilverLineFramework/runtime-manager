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
        "-v", "--verbose", default=21, type=int, help="Logging level.")
    p.add_argument(
        "-i", "--ignore_err", default=False, action='store_true',
        help="Ignore errors encountered during execution.")
    p.add_argument(
        "-s", "--sync", default=False, action='store_true',
        help="Execute command synchronously instead of asynchronously.")
    p.add_argument(
        "-r", "--sudo", default=False, action='store_true',
        help="Execute command as root.")
    p.add_argument(
        "-p", "--password", default="",
        help="Password if executing as sudo.")
    return p


def _main(args):

    configure_log(log=None, level=args.verbose)

    with open(args.cfg) as f:
        cfg = json.load(f)
    cluster = SilverlineCluster.from_config(cfg)

    def execute(connection, device):
        cmd = device.format(args.command)
        stream = device.stream()
        if args.sudo:
            connection.sudo(cmd, out_stream=stream, password=args.password)
        else:
            connection.run(cmd, out_stream=stream)

    targets = pd.read_csv(cluster.manifest, sep='\t')
    devices = set(Device(cluster, dict(row)) for _, row in targets.iterrows())

    print("Executing on {} devices: {}".format(len(devices), args.command))
    run_command(execute, devices, ignore_err=args.ignore_err, sync=args.sync)
