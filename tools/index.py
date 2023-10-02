"""Generate list of benchmarks."""

import os
import random
import copy

_desc = "Index executable benchmark files, excluding common files."


def _index(base):
    if os.path.isdir(base):
        res = []
        for p in os.listdir(base):
            if "common" not in p:
                res += _index(os.path.join(base, p))
        return res
    else:
        return [base]


def _parse(p):
    p.add_argument("-d", "--dir", help="Target directory.", default="wasm")
    p.add_argument(
        "-p", "--prefix", default="benchmarks",
        help="Directory to execute command in.")
    p.add_argument(
        "-r", "--replace", nargs='+', default=[],
        help="Substitutions to perform.")
    p.add_argument(
        "-s", "--shuffle", default=False, action='store_true',
        help="Shuffle files.")
    p.add_argument(
        "-t", "--set", default=None, type=int,
        help="Generate sets of t items, separated by `:`.")
    p.add_argument(
        "-n", "--limit", default=None, type=int,
        help="Only list first n matches.")
    return p


def _main(args):
    os.chdir(args.prefix)

    def _subst(s):
        for subst in args.replace:
            src, dst = subst.split("=")
            s = s.replace(src, dst)
        return s

    out = [_subst(s) for s in _index(args.dir)]

    if args.set:
        outs = [copy.copy(out) for _ in range(args.set)]
        for x in outs:
            random.shuffle(x)
        out = [":".join(x) for x in zip(*outs)]
    else:
        if args.shuffle:
            random.shuffle(out)

    if isinstance(args.limit, int):
        out = out[:args.limit]

    print(" ".join(out))
