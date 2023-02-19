"""Command line tools."""

from . import alias
from . import configure
from . import cpufreq
from . import list
from . import run
from . import runall
from . import start
from . import status
from . import stop

commands = {
    "alias": alias,
    "configure": configure,
    "cpufreq": cpufreq,
    "list": list,
    "run": run,
    "runall": runall,
    "start": start,
    "status": status,
    "stop": stop
}
