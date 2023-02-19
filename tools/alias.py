"""Write cluster management aliases."""

import os
import json
import pandas as pd


_desc = "Write cluster management aliases."


def _parse(p):
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")


def _main(args):
    with open(args.cfg) as f:
        cfg = json.load(f)

    with open(os.path.expanduser('~/.alias'), 'a') as f:
        devices = pd.read_csv(cfg["manifest"], sep='\t')["Device"]

        # ssh
        for d in devices:
            f.write("ssh {}@{}{}".format(cfg["username"], d, cfg["domain"]))
