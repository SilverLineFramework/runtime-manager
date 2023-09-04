"""Benchmarking runtime."""

from beartype import beartype

from .linux_minimal import LinuxMinimal


@beartype
class DataRace(LinuxMinimal):
    """Generic runtime for data-race detection analysis."""

    TYPE = "data-race"
    APIS = ["wasm", "wasi", "profile:data-race"]
    MAX_NMODULES = 1
    DEFAULT_NAME = "data-race-basic"
    DEFAULT_SHORTNAME = "dr"
    #DEFAULT_COMMAND = (
    #    "PYTHONPATH=. ./env/bin/python runtimes/linux_benchmarking.py")
    DEFAULT_COMMAND = (
        "./runtimes/bin/linux-datarace-wali")
    PROFILE_TOPIC = "profile/data-race"

    def handle_profile(self, module: str, msg: bytes) -> None:
        """Handle profiling message."""
        self.mgr.publish(
            self.control_topic(self.PROFILE_TOPIC, module), msg, qos=2)


@beartype
class DataRaceAccessSingle(DataRace):
    """Data Race Access (Stage 1) runtime in single mode."""

    TYPE = "data-race-access-single"
    APIS = ["wasm", "wasi", "profile:data-race-access-single"]
    DEFAULT_NAME = "data-race-access-single"
    DEFAULT_SHORTNAME = "dr-acc"
    DEFAULT_COMMAND = (
        "./runtimes/bin/linux-datarace-wali-access")
    PROFILE_TOPIC = "profile/dr_access"


@beartype
class DataRaceAccessBatch(DataRace):
    """Data Race Access (Stage 1) runtime in batch mode."""

    TYPE = "data-race-access"
    APIS = ["wasm", "wasi", "profile:data-race-access"]
    DEFAULT_NAME = "data-race-access-batch"
    DEFAULT_SHORTNAME = "dr-acc-batch"
    PROFILE_TOPIC = "profile/dr_access_batch"


@beartype
class DataRaceTSVDSingle(DataRace):
    """Data Race TSV Detector (Stage 2) runtime in single mode."""

    TYPE = "data-race-tsvd-single"
    APIS = ["wasm", "wasi", "profile:data-race-tsvd-single"]
    DEFAULT_NAME = "data-race-tsvd-single"
    DEFAULT_SHORTNAME = "dr-tsvd"
    DEFAULT_COMMAND = (
        "./runtimes/bin/linux-datarace-wali-tsvd")
    PROFILE_TOPIC = "profile/dr_tsvd"



@beartype
class DataRaceTSVDBatch(DataRace):
    """Data Race TSV Detector (Stage 2) runtime in batch mode."""

