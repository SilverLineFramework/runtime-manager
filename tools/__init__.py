"""Command line tools."""

from . import alias
from . import aot
from . import benchmark
from . import command
from . import configure
from . import cpufreq
from . import get
from . import index
from . import list
from . import put
from . import run
from . import runall
from . import start
from . import status
from . import stop
from .shortcuts import shortcuts

commands: dict = {
    "aot": aot,
    "benchmark": benchmark,
    "alias": alias,
    "cmd": command,
    "configure": configure,
    "cpufreq": cpufreq,
    "get": get,
    "index": index,
    "list": list,
    "put": put,
    "run": run,
    "runall": runall,
    "start": start,
    "status": status,
    "stop": stop,
    **shortcuts
}
