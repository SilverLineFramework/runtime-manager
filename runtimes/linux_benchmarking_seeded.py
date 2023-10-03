"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import struct
import signal
import random
import subprocess

from libsilverline import Message, SLSocket, Header
from common import make_command, run_and_wait


def _handle_seed(args, cmd):
    """Apply seed arguments to command."""
    seed = random.randint(0, args.get("max_seed", 9999))
    if args.get("dirmode", False):
        path = args.get("argv")[-1]
        ls = sorted(os.listdir(path))
        cmd[-1] = os.path.join(path, ls[seed % len(ls)])
    elif args.get("scriptmode", False):
        _cmd = ["./env/bin/python", args.get("argv")[-1], str(seed)]
        cmd[-1] = subprocess.run(
            _cmd, capture_output=True).stdout.decode('utf-8')
    else:
        cmd.append(str(seed))
    return cmd, seed


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index: int) -> None:
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = -1
        self.done = False

    def _run(self, cmd, seed):
        """Run single benchmark iteration."""
        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module, " ".join(cmd)))
        self.process = os.fork()
        err, real_time, rusage = run_and_wait(self.process, cmd)
        if err != 0:
            self.socket.write(Message.from_str(
                Header.control | 0x00, Header.log_module,
                "Nonzero exit code: {}".format(err)))
            return struct.pack("IIII", 0, 0, 0, 0)
        else:
            return struct.pack(
                "IIII", real_time, int(rusage.ru_utime * 10**6),
                int(rusage.ru_stime * 10**6), seed)

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
            try:
                cmd = self._make_cmd(file, args, i)
                stats.append(self._run(*_handle_seed(args, cmd)))
            except Exception as e:
                self.done = True
                self.socket.write(Message.from_str(
                    Header.control, Header.log_runtime, str(e)))

            if self.done:
                break

        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module,
            "Exited with {} samples.".format(len(stats))))

        watchdog.cancel()
        return b''.join(stats)

    def _make_cmd(self, file, args, idx):
        """Assemble shell command."""
        engine = args.get("engine", "iwasm-i")
        if isinstance(engine, list):
            engine = engine[idx]
        argv = args.get("argv", [])

        return make_command(engine, file, argv)

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
