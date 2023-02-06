"""Benchmarking runtime."""

from beartype import beartype

from .linux_minimal import LinuxMinimalRuntime


@beartype
class LinuxBenchmarkingRuntime(LinuxMinimalRuntime):
    """Execution time / memory benchmarking runtime."""

    TYPE = "linux/benchmarking"
    APIS = []
    MAX_NMODULES = 1

    def __init__(
        self, rtid: str = None, name: str = "runtime-benchmarking",
        command: list[str] = ["python", "linux_benchmarking.py"],
        cfg: dict = {}
    ) -> None:
        super().__init__(rtid, name, command=command, cfg=cfg)

    def handle_profile(self, module: int, msg: bytes) -> None:
        """Handle profiling message."""
        self.mgr.publish(
            self.control_topic("profile/benchmarking", module), msg)
