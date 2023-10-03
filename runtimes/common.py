"""Common python-based runtime utilities."""

import os
import time
from beartype.typing import Any


# Supported engine commands
ENGINES = {
    "native": "native",
    "iwasm-i": "./runtimes/bin/iwasm -v=0",
    "iwasm-a": "./runtimes/bin/iwasm -v=0",
    "wasmer-j-cl": "./runtimes/bin/wasmer run --cranelift --enable-all --",
    "wasmer-a-cl": "./runtimes/bin/wasmer run --enable-all --",
    "wasmer-j-ll": "./runtimes/bin/wasmer run --llvm --enable-all --",
    "wasmer-a-ll": "./runtimes/bin/wasmer run --enable-all --",
    "wasmer-j-sp": "./runtimes/bin/wasmer run --singlepass --enable-all --",
    "wasmedge-i": "./runtimes/bin/wasmedge",
    "wasmedge-j": "./runtimes/bin/wasmedge",
    "wasmedge-a": "./runtimes/bin/wasmedge",
    "wasmtime-j": "./runtimes/bin/wasmtime run --wasm-features all --",
    "wasmtime-a": "./runtimes/bin/wasmtime run --wasm-features all --allow-precompiled --",
    "wasm3-i": "./runtimes/bin/wasm3",
}

# File formats other than normal wasm files in wasm/*.wasm
CUSTOM_FORMATS = {
    "iwasm-a": "aot/iwasm/",
    "wasmer-a-cl": "aot/wasmer-cranelift/",
    "wasmer-a-ll": "aot/wasmer-llvm/",
    "wasmtime-a": "aot/wasmtime/",
    "wasmedge-a": "aot/wasmedge/",
    "native": "native/"
}


def make_command(
    engine: str, file: str, argv: list[str], env: list[str] = []
) -> list[str]:
    """Create executable command."""
    if engine in CUSTOM_FORMATS:
        file = file.replace("wasm/", CUSTOM_FORMATS[engine])
    engine_cmd = ENGINES.get(engine, engine)

    if engine == "native":
        cmd = [file] + argv
    else:
        cmd = engine_cmd.split(" ")
        # Ends in '--': runtime, module args separated by '--'
        cmd, sep = (cmd[:-1], True) if cmd[-1] == "--" else (cmd, False)

        cmd += ["--dir=."]
        cmd += ["--env=\"{}\"".format(var) for var in env]
        cmd += [file]
        cmd += ["--"] if sep else []
        cmd += argv
    return cmd


def run_and_wait(pid: int, cmd: list[str]) -> tuple[int, int, Any]:
    """Run command (after forking) and return rusage."""
    start = time.perf_counter_ns()
    if pid == 0:
        try:
            devnull = os.open("/dev/null", os.O_WRONLY)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.execvp(cmd[0], cmd)
        except Exception as e:
            os._exit(1)
    else:
        _, status, rusage = os.wait4(pid, 0)
        real_time = (time.perf_counter_ns() - start) // 1000
        return os.waitstatus_to_exitcode(status), real_time, rusage
