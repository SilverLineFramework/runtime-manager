"""Benchmarking runtime."""

from beartype import beartype

from .linux_minimal import LinuxMinimal


@beartype
class Benchmarking(LinuxMinimal):
    """Execution time / memory usage benchmarking runtime."""

    TYPE = "benchmarking/basic"
    APIS = ["wasm", "wasi", "profile:benchmarking"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "benchmarking-basic"
    DEFAULT_COMMAND = "PYTHONPATH=. python runtimes/linux_benchmarking.py"
    PROFILE_TOPIC = "profile/benchmarking"

    def handle_profile(self, module: str, msg: bytes) -> None:
        """Handle profiling message."""
        self.mgr.publish(self.control_topic(self.PROFILE_TOPIC, module), msg)


@beartype
class OpcodeCount(Benchmarking):
    """Opcode counting runtime."""

    TYPE = "benchmarking/opcodes"
    APIS = ["wasm", "wasi", "profile:opcodes"]

    MAX_NMODULES = 1
    DEFAULT_NAME = "benchmarking-opcodes"
    DEFAULT_COMMAND = "./runtimes/profiling-opcodes/build/runtime"
    PROFILE_TOPIC = "profile/opcodes"
