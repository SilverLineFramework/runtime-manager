"""Stop module."""

import logging
from libsilverline import SilverlineClient, configure_log


_desc = "Stop Silverline module(s)."


def _parse(p):
    p.add_argument("-c", "--cfg", help="Config file.", default="config.json")
    p.add_argument("-v", "--verbose", default=20, help="Logging level.")
    p.add_argument(
        "-n", "--modules", nargs="+", default=[],
        help="Modules to stop. Modules can be specified by name, UUID, or "
        "last hex digits of UUID.")
    return p


def _main(args):
    configure_log(log=None, level=args.verbose)
    log = logging.getLogger("cli")
    client = SilverlineClient.from_config(args.cfg, name="cli").start()
    for mod in args.modules:
        mid = client.infer_module(mod)
        if mid is None:
            log.error("Could not find module: {}".format(mod))
        else:
            client.delete_module(mid)
            log.info("Deleted: {}".format(mid))

    client.stop()
