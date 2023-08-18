"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import struct
import signal

from libsilverline import Message, SLSocket, Header


# Supported engine commands
ENGINES = {
    "native": "native",
    "iwasm": "./runtimes/bin/iwasm -v=0",
    "iwasm-aot": "./runtimes/bin/iwasm -v=0",
    "wasmer-cranelift": "./runtimes/bin/wasmer run --cranelift --enable-all --",
    "wasmer-llvm": "./runtimes/bin/wasmer run --llvm --enable-all --",
    "wasmer-singlepass": "./runtimes/bin/wasmer run --singlepass --enable-all --",
    "wasmedge": "./runtimes/bin/wasmedge",
    "wasmedge-aot": "./runtimes/bin/wasmedge",
    "wasmtime": "./runtimes/bin/wasmtime run --wasm-features all --",
    "wasm3": "./runtimes/bin/wasm3",
}

# File formats other than normal wasm files in wasm/*.wasm
CUSTOM_FORMATS = {
    "iwasm-aot": "aot-iwasm/",
    "wasmedge-aot": "aot-wasmedge/",
    "native": "native/"
}

class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index: int) -> None:
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None

    def _run(self, cmd):
        """Run single benchmark iteration."""
        self.process = os.fork()
        if self.process == 0:
            try:
                devnull = os.open("/dev/null", os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.execvp(cmd[0], cmd)
            except Exception as e:
                os._exit(1)
        else:
            try:
                with open("/sys/fs/cgroup/cpuset/bench/tasks") as f:
                    f.write(str(self.process))
            except FileNotFoundError:
                pass

            _, status, rusage = os.wait4(self.process, 0)
            if os.waitstatus_to_exitcode(status) != 0:
                self.socket.write(Message.from_str(
                    Header.control | 0x00, Header.log_module,
                    "Nonzero exit code: {}".format(status)
                ))
                return None
            else:
                return struct.pack(
                    "III",
                    int(rusage.ru_utime * 10**6),
                    int(rusage.ru_stime * 10**6),
                    rusage.ru_maxrss)

    def _run_loop(self, file, args, repeat, repeat_mode):
        """Run benchmarking loop."""

        def kill():
            os.kill(self.process, signal.SIGKILL)

        watchdog = threading.Timer(args.get("limit", 60.0), kill)
        watchdog.start()

        stats = []
        for i in range(repeat):
            if args.get("ilimit"):
                watchdog2 = threading.Timer(args.get("ilimit"), kill)
                watchdog2.start()

            cmd = self._make_cmd(file, args, i, repeat_mode)
            res = self._run(cmd)

            if args.get("ilimit"):
                watchdog2.cancel()                

            if res is None:
                stats.append(struct.pack("III", 0, 0, 0))
                if repeat_mode:
                    break
            else:
                stats.append(res)

        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module,
            "Exited with {} samples.".format(len(stats))))

        watchdog.cancel()
        return b''.join(stats)

    def _make_cmd(self, file, args, idx, repeat_mode):
        """Assemble shell command."""
        engine = args.get("engine", "wasmer-singlepass")
        if isinstance(engine, list):
            engine = engine[idx]
        argv = args.get("argv", [])
        if not repeat_mode:
            argv = argv[idx]

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
            cmd += ["--env=\"{}\"".format(var) for var in args.get("env", [])]
            cmd += [file]
            cmd += ["--"] if sep else []
            cmd += argv
        return cmd

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        args = data.get("args", {})

        # repeat_mode: one set of argv that we repeat
        argv = args.get("argv", [])
        repeat_mode = len(argv) == 0 or not isinstance(argv[0], list)

        repeat = args.get("repeat", 1)
        if isinstance(args.get("engine"), list):
            repeat = len(args.get("engine"))
        if repeat_mode:
            repeat = min(repeat, len(argv))

        stats = self._run_loop(data.get("file"), args, repeat, repeat_mode)

        self.socket.write(Message(
            Header.control | 0x00, Header.profile, stats))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited, {"status": "exited"}))

    def handle_message(self, msg: Message) -> None:
        """Handle message from manager."""
        match (msg.h1 & Header.control, msg.h1 & Header.index_bits, msg.h2):
            case (0x00, _, _):
                pass
            case (Header.control, _, Header.create):
                threading.Thread(target=self.run, args=[msg]).start()
            case _:
                pass

    def loop(self):
        """Main loop."""
        while True:
            msg = self.socket.read()
            if msg is not None:
                self.handle_message(msg)


if __name__ == '__main__':
    LinuxBenchmarkingRuntime(int(sys.argv[1])).loop()
