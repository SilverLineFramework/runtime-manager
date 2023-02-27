"""Start runtimes on cluster."""

from . import command


_desc = "Start runtimes on cluster."


def _parse(p):
    command._parse(p)
    p.add_argument(
        "-t", "--runtimes", default="linux/min/wasmer",
        help="Runtime(s) to start on managers.")
    return p


def _main(args):
    # args.command = (
    #    "screen -S runtime -dm bash -c \"cd runtime-manager; "
    #    "./env/bin/python start.py --name {{name}} --cfg config.json "
    #    "--runtimes {} --verbose {} --cpus {{cgroup}}\"".format(
    #        args.runtimes, args.verbose))
    # args.sudo = True
    # args.verbose = 21
    args.command = (
        "screen -S runtime -dm bash -c "
        "\". /home/hc/.wasmedge/env; cd runtime-manager; "
        "./env/bin/python start.py --name {{name}} --cfg config.json "
        "--runtimes {} --verbose {}\"".format(
            args.runtimes, args.verbose))
    args.verbose = 21
    command._main(args)
