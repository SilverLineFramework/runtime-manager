"""Command line tools."""

from collections import namedtuple

from . import make_alias
from . import command
from . import configure
from . import cpufreq
from . import get
from . import list
from . import put
from . import run
from . import runall
from . import status
from . import stop
from .shortcuts import start, shutdown, reboot, update, kill, version, Alias


commands = {
    "alias": make_alias,
    "cmd": command,
    "configure": configure,
    "cpufreq": cpufreq,
    "get": get,
    "kill": kill,
    "list": list,
    "put": put,
    "reboot": reboot,
    "run": run,
    "runall": runall,
    "shutdown": shutdown,
    "start": start,
    "status": status,
    "stop": stop,
    "update": update,
    "version": version
}
