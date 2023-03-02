"""Process matrix dataset."""

import numpy as np
from matplotlib import pyplot as plt
from argparse import ArgumentParser

from trace import Dataset


def _parse(p):
    p.add_argument(
        "-p", "--path", help="Path to dataset.", default="data/matrix")
    p.add_argument(
        "-o", "--out", help="Output (base) path.", default="matrix")
    p.add_argument(
        "--plot", help="Draw plot.", action='store_true', default=False)
    p.add_argument(
        "--filter", action='store_true', default=False,
        help="Filter invalid devices")
    p.add_argument(
        "--exclude", nargs='+', help="Excluded devices.",
        default=[
            "iwasm-aot.hc-21", "iwasm-aot.hc-25", "iwasm-aot.hc-27",
            "wasmer-singlepass.hc-15", "wasmer-singlepass.hc-19"
        ])
    return p


def _main(args):
    matrix = Dataset.from_sessions([args.path]).to_matrix()

    if args.filter:
        filter = (np.sum(matrix.data > 0, axis=1) > 0)
        for k in args.exclude:
            filter[matrix.rows[k]] = False

        matrix = matrix[filter, :]

    matrix.save(args.out + ".npz", rows="platform", cols="files")

    if args.plot:
        fig, ax = plt.subplots(1, 1, figsize=(40, 40))
        with np.errstate(divide='ignore'):
            (matrix @ np.log).plot(ax)
        fig.savefig(args.out + ".png", bbox_inches='tight', pad_inches=0.2)


if __name__ == '__main__':
    _main(_parse(ArgumentParser()).parse_args())
