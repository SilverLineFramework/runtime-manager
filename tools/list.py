"""List running runtimes and modules."""

from argparse import ArgumentParser
from common import SilverlineClient

from rich.console import Console
from rich.table import Table
from rich.text import Text


def _parse():
    p = ArgumentParser(
        description="List runtimes and modules running on each runtime; UUIDs "
        "are shortened to the last 4 hex characters (2 bytes).")
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    return p


def _table(runtimes):
    table = Table()
    table.add_column("uuid:name", justify="left")
    table.add_column("modules", justify="left")
    for rt in runtimes:
        _rt = Text(rt["uuid"][-4:], style="bold blue")
        _rt.append(':')
        _rt.append(rt["name"], style="bold white")

        _mod = Text()
        for mod in rt["children"]:
            _mod.append(mod["uuid"][-4:], style="bold green")
            _mod.append(":")
            _mod.append(mod["name"])
            _mod.append("  ")

        table.add_row(_rt, _mod)

    Console().print(table)



if __name__ == '__main__':

    args = _parse().parse_args()

    client = SilverlineClient.from_config(args.cfg)
    runtimes = client.get_runtimes()

    _table(runtimes)
