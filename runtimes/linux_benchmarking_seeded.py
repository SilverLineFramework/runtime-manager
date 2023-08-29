"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import struct
import signal
import random

from libsilverline import Message, SLSocket, Header


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


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index: int) -> None:
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None
        self.done = False

    def _run(self, cmd, seed):
        """Run single benchmark iteration."""
        print(" ".join(cmd))
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
                    "Nonzero exit code: {}".format(status)))
                return None
            else:
                return struct.pack(
                    "IIII",
                    int(rusage.ru_utime * 10**6), int(rusage.ru_stime * 10**6),
                    rusage.ru_maxrss, seed)

    def _run_loop(self, file, args, repeat):
        """Run benchmarking loop."""
        def kill():
            os.kill(self.process, signal.SIGKILL)
            self.done = True

        self.done = False
        watchdog = threading.Timer(args.get("limit", 60.0), kill)
        watchdog.start()

        stats = []
        for i in range(repeat):
            if args.get("ilimit"):
                watchdog2 = threading.Timer(args.get("ilimit"), kill)
                watchdog2.start()

            cmd = self._make_cmd(file, args, i)
            seed = random.randint(0, args.get("max_seed", 9999))
            if args.get("dirmode", False):
                path = args.get("argv", [])[-1]
                ls = os.listdir(path)
                cmd[-1] = os.path.join(path, ls[seed % len(ls)])
            else:
                cmd.append(str(seed))
            res = self._run(cmd, seed)

            if args.get("ilimit"):
                watchdog2.cancel()

            if res is None:
                stats.append(struct.pack("IIII", 0, 0, 0, 0))
            else:
                stats.append(res)
            if self.done:
                break

        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module,
            "Exited with {} samples.".format(len(stats))))

        watchdog.cancel()
        return b''.join(stats)

    def _make_cmd(self, file, args, idx):
        """Assemble shell command."""
        engine = args.get("engine", "wasmer-singlepass")
        if isinstance(engine, list):
            engine = engine[idx]
        argv = args.get("argv", [])

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
        repeat = args.get("repeat", 1)

        stats = self._run_loop(data.get("file"), args, repeat)

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
