"""Benchmarking runtime."""

from beartype import beartype

from .linux_minimal import LinuxMinimalRuntime


@beartype
class LinuxBenchmarkingRuntime(LinuxMinimalRuntime):
    """Execution time / memory benchmarking runtime."""

    TYPE = "linux/profiling/basic"
    APIS = ["wasm", "wasi", "profile:basic"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "linux-benchmarking-basic"
    DEFAULT_COMMAND = "PYTHONPATH=. python runtimes/linux_benchmarking.py"

    def handle_profile(self, module: int, msg: bytes) -> None:
        """Handle profiling message."""
        self.mgr.publish(
            self.control_topic("profile/benchmarking", module), msg)
