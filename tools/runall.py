"""Run module on entire cluster."""

from . import run
import pandas as pd
from argparse import ArgumentParser

from libsilverline import SilverlineCluster


_desc = "Launch Silverline module(s) across cluster nodes."
_parse = run._parse


def _main(args):
    devices = list(pd.read_csv(
        SilverlineCluster.from_config(args.config)['manifest'])["Devices"])
    run._main(args, default_runtime=devices)


if __name__ == '__main__':
    _main(_parse(ArgumentParser(description=_desc)).parse_args())
