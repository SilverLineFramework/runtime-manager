"""List running runtimes and modules."""

import os
import time
from functools import partial

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.live import Live

from libsilverline import SilverlineClient, configure_log


def _inner(client):
    try:
        runtimes = client.get_runtimes()
    except Exception as e:
        table = Table()
        table.add_column("Exception:")
        table.add_row(str(e))
        return table

    table = Table()
    table.add_column("", justify="left")
    table.add_column("uuid:name", justify="left")
    table.add_column("type", justify="left")
    table.add_column("modules", justify="left")
    table.add_column("queue", justify="left")
    table.add_column("", justify="right")

    runtimes.sort(key=lambda rt: rt["name"])
    for idx, rt in enumerate(runtimes):
        _idx = Text("{:02}".format(idx), style="bold black")

        _rt = Text(rt["uuid"][-4:], style="bold blue")
        _rt.append(':')
        _rt.append(rt["name"], style="bold white")

        _mod = Text()
        for i, mod in enumerate(rt["children"]):
            _mod.append(mod["uuid"][-4:], style="bold green")
            _mod.append(":")
            _mod.append(mod["name"])
            if i != len(rt["children"]) - 1:
                _mod.append("  ")

        _queue = Text()
        for i, mod in enumerate(rt["queued"][:1]):
            _queue.append(mod["uuid"][-4:], style="bold green")
            _queue.append(":")
            _queue.append(mod["name"])
            if i != len(rt["queued"]) - 1:
                _queue.append(" ")

        if len(rt["queued"]) > 1:
            _queue.append("...")
            _rem = "(+{})".format(len(rt["queued"]) - 1)
        else:
            _rem = ""

        table.add_row(_idx, _rt, rt["runtime_type"], _mod, _queue, _rem)

    return table


_desc = "List runtimes and modules running on each runtime."


def _parse(p):
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument(
        "-v", "--verbose", default=40, type=int, help="Logging level.")
    p.add_argument(
        "-w", "--watch", default=0.0, type=float,
        help="Watch refresh interval, if >0.")
    return p


def _main(args):
    configure_log(log=None, level=args.verbose)

    client = SilverlineClient.from_config(args.cfg).start()
    if args.watch > 0.0:
        func = partial(_inner, client)
        with Live(func()) as live:
            while True:
                live.update(func())
                time.sleep(args.watch)
    else:
        Console().print(_inner(client))
