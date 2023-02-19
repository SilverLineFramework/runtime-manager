"""SSH Primitives."""

import logging
from beartype import beartype
from rich.progress import Progress
from fabric.connection import Connection
from multiprocessing.pool import ThreadPool

from libsilverline import SilverlineCluster


@beartype
class WriteFile(object):
    """Dummy file to make tqdm.write behave like logging."""

    def __init__(self, name: str) -> None:
        self.name = name

    def write(self, x: str) -> None:
        """Behave like file."""
        if len(x.rstrip()) > 0:
            print("[{}] ".format(self.name) + x.rstrip())

    def flush(self) -> None:
        """Flush does nothing."""
        pass


@beartype
class Device:
    """SSH device wrapper."""

    def __init__(self, cluster: SilverlineCluster, row: dict) -> None:
        self.context = {
            "name": row.get("Device"),
            "fullname": row.get("Device") + cluster.domain,
            "model": row.get("Model", "-"),
            "cpu": row.get("CPU", "-"),
            "target": row.get("Target", "-"),
            "arch": row.get("Arch", "-")
        }
        self.name = self.context["name"]
        self.fullname = self.context["fullname"]
        self.username = cluster.username

    def format(self, command: str) -> str:
        """Format command with context."""
        return command.format(**self.context)

    def execute(self, func, ignore_err=False) -> None:
        """Execute function."""
        try:
            with Connection(self.fullname, self.username, 22) as connection:
                func(connection, self)
        except Exception as e:
            if not ignore_err:
                print("[{}] Failed: {}".format(self.name, e))

    def stream(self):
        """File output stream."""
        return WriteFile(self.name)


@beartype
def run_command(
    func, devices: set[Device], ignore_err: bool = False, sync: bool = False
) -> None:
    """Run fabric command."""
    with Progress() as progress:
        n = len(devices)
        task = progress.add_task(
            "Executing on {} devices...".format(n), total=n)

        def _execute(device):
            device.execute(func, ignore_err=ignore_err)
            progress.update(task, advance=1)
            devices.remove(device)

        if sync:
            for d in list(devices):
                _execute(d)
        else:
            with ThreadPool(processes=len(devices)) as p:
                p.map(_execute, devices)
