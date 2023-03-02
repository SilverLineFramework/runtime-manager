"""Process opcode data."""

import numpy as np
import json
from matplotlib import pyplot as plt

from utils import apply_recursive, Index, Matrix

from argparse import ArgumentParser


def _parse(p):
    p.add_argument(
        "-p", "--path", help="Path to dataset.", default="data/opcodes")
    p.add_argument(
        "-o", "--out", help="Output (base) path.", default="opcodes")
    p.add_argument(
        "--plot", help="Draw plot.", action='store_true', default=False)
    return p


def _main(args):

    def load(path):
        with open(path) as f:
            data = json.load(f)
        return (
            np.array(data["opcodes"], dtype=np.uint32),
            data["module"]["file"].replace("wasm/", "").replace(".wasm", ""))

    data, files = list(zip(*apply_recursive(args.path, load)))
    data = np.array(data)
    nonzero = np.where(np.sum(data, axis=0) > 10)[0]

    opcodes = Index(
        nonzero, display=["{:02x}".format(int(i)) for i in nonzero])
    mat = Matrix(
        data=data[:, nonzero], rows=Index(files), cols=opcodes
    )[np.argsort(files)]

    mat.save(args.out + ".npz", rows="files", cols="opcodes")

    if args.plot:
        fig, ax = plt.subplots(figsize=(40, 40))
        (mat @ (lambda x: np.log(x + 1))).plot(ax)
        fig.savefig(args.out + ".png", bbox_inches="tight", pad_inches=0.2)


if __name__ == '__main__':
    _main(_parse(ArgumentParser()).parse_args())
