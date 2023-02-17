"""List running runtimes and modules."""

from argparse import ArgumentParser
from libsilverline import SilverlineClient, configure_log

from rich.console import Console
from rich.table import Table
from rich.text import Text


def _parse():
    p = ArgumentParser(
        description="List runtimes and modules running on each runtime; UUIDs "
        "are shortened to the last 4 hex characters (2 bytes).")
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument("-v", "--verbose", default=40, help="Logging level.")
    return p


def _table(runtimes):
    table = Table()
    table.add_column("uuid:name", justify="left")
    table.add_column("type", justify="left")
    table.add_column("modules", justify="left")
    for rt in runtimes:
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

        table.add_row(_rt, rt["runtime_type"], _mod)

    Console().print(table)


if __name__ == '__main__':

    args = _parse().parse_args()
    configure_log(log=None, level=args.verbose)

    client = SilverlineClient.from_config(args.cfg).start()
    _table(client.get_runtimes())
