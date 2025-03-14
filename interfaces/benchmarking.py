"""Benchmarking runtime."""

from beartype import beartype

from .linux_minimal import LinuxMinimal


@beartype
class Benchmarking(LinuxMinimal):
    """Execution time / memory usage benchmarking runtime."""

    TYPE = "benchmarking"
    APIS = ["wasm", "wasi", "profile:benchmarking"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "benchmarking-basic"
    DEFAULT_SHORTNAME = "bench"
    DEFAULT_COMMAND = (
        "PYTHONPATH=. ./env/bin/python runtimes/linux_benchmarking.py")
    PROFILE_TOPIC = "profile/benchmarking"

    def handle_profile(self, module: str, msg: bytes) -> None:
        """Handle profiling message."""
        self.mgr.publish(
            self.control_topic(self.PROFILE_TOPIC, module), msg, qos=2)


@beartype
class BenchmarkingSeeded(Benchmarking):
    """Benchmarking runtime with a random seed provided to each benchmark."""

    TYPE = "benchmarking/seeded"
    APIS = ["wasm", "wasi", "profile:benchmarking-seeded"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "benchmarking-seeded"
    DEFAULT_SHORTNAME = "seed"
    DEFAULT_COMMAND = (
        "PYTHONPATH=. ./env/bin/python runtimes/linux_benchmarking_seeded.py")
    PROFILE_TOPIC = "profile/seeded"


@beartype
class BenchmarkingInterference(Benchmarking):
    """Execution time for 2-way interference."""

    TYPE = "benchmarking/interference"
    APIS = ["wasm", "wasi", "profile:interference"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "benchmarking-interference"
    DEFAULT_SHORTNAME = "if"
    DEFAULT_COMMAND = (
        "PYTHONPATH=. ./env/bin/python "
        "runtimes/linux_benchmarking_interference.py")
    PROFILE_TOPIC = "profile/interference"


@beartype
class OpcodeCount(Benchmarking):
    """Opcode counting runtime."""

    TYPE = "benchmarking/opcodes"
    APIS = ["wasm", "wasi", "profile:opcodes"]

    MAX_NMODULES = 1
    DEFAULT_NAME = "benchmarking-opcodes"
    DEFAULT_SHORTNAME = "intrp"
    DEFAULT_COMMAND = "./runtimes/bin/profiling-opcodes"
    PROFILE_TOPIC = "profile/opcodes"
