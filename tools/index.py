"""Generate list of benchmarks."""

import os


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
    return p


def _main(args):
    os.chdir(args.prefix)

    def _subst(s):
        for subst in args.replace:
            src, dst = subst.split("=")
            s = s.replace(src, dst)
        return s

    print(" ".join(_subst(s) for s in _index(args.dir)))
