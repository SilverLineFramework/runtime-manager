"""Command line tools."""

from . import alias
from . import aot
from . import command
from . import configure
from . import cpufreq
from . import get
from . import list
from . import put
from . import run
from . import runall
from . import start
from . import status
from . import stop
from .shortcuts import shortcuts


commands = {
    "aot": aot,
    "alias": alias,
    "cmd": command,
    "configure": configure,
    "cpufreq": cpufreq,
    "get": get,
    "list": list,
    "put": put,
    "run": run,
    "start": start,
    "status": status,
    "stop": stop,
    **shortcuts
}
