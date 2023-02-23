"""Platform scraping."""

import os
from beartype import beartype
from beartype.typing import Any


@beartype
class SysFS:
    """Linux sysfs convenience wrapper."""

    def __init__(self, base: str) -> None:
        self.base = base

    def read(self, *path: str, type: Any) -> Any:
        """Read value from sysfs."""
        with open(os.path.join(self.base, *path)) as f:
            return type(f.read())

    def write(self, val: Any, *path: str, optional: bool = False) -> None:
        """Write value to sysfs."""
        path = os.path.join(self.base, path)
        if not optional or os.path.exists(path):
            with open(path, 'w') as f:
                f.write(str(val))

    def path(self, *args: str) -> str:
        """Expand path."""
        return os.path.join(self.base, *args)


def __int_arr(s: str) -> list[int]:
    if len(s.rstrip('\n')) > 0:
        arr = s.rstrip('\n').split('\n')
        return [int(x) for x in arr]
    else:
        return []


def delete_cgroup(name: str) -> None:
    """Delete cgroup cpuset."""
    sysfs = SysFS("/sys/fs/cgroup/cpuset")
    if os.path.exists(sysfs.path(name)):
        tasks = sysfs.read(name, "tasks", type=__int_arr)
        for t in tasks:
            sysfs.write("tasks", t)
        os.rmdir(sysfs.path(name))


def make_cgroup(cpus: str, name: str) -> None:
    """Create cgroup cpuset."""
    sysfs = SysFS("/sys/fs/cgroup/cpuset")
    os.makedirs(sysfs.path(name), exist_ok=True)
    sysfs.write(cpus, name, "cpuset.cpus")
    sysfs.write(0, name, "cpuset.mems")
    sysfs.write(0, name, "cpuset.cpu_exclusive")

    # Cpusets need R+W+X permissions; tasks need R+W permissions
    os.chmod(sysfs.path(), 777)
    os.chmod(sysfs.path("tasks"), 666)
    os.chmod(sysfs.path(name), 777)
    os.chmod(sysfs.path(name, "tasks"), 666)
