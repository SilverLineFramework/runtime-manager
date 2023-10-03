"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import struct
import signal

from libsilverline import Message, SLSocket, Header
from common import make_command, run_and_wait


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index: int) -> None:
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = -1

    def _run(self, cmd):
        """Run single benchmark iteration."""
        self.process = os.fork()
        err, real_time, rusage = run_and_wait(self.process, cmd)

        if err != 0:
            self.socket.write(Message.from_str(
                Header.control | 0x00, Header.log_module,
                "Nonzero exit code: {}".format(err)
            ))
            return None
        else:
            return struct.pack(
                "III", real_time,
                int(rusage.ru_utime * 10**6), int(rusage.ru_stime * 10**6))

    def _run_loop(self, file, args, repeat, repeat_mode):
        """Run benchmarking loop."""
        def kill():
            os.kill(self.process, signal.SIGKILL)

        watchdog = threading.Timer(args.get("limit", 60.0), kill)
        watchdog.start()

        stats = []
        for i in range(repeat):
            cmd = self._make_cmd(file, args, i, repeat_mode)
            res = self._run(cmd)
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
        engine = args.get("engine", "iwasm-i")
        if isinstance(engine, list):
            engine = engine[idx]
        argv = args.get("argv", [])
        if not repeat_mode:
            argv = argv[idx]

        return make_command(engine, file, argv)

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
        if not repeat_mode:
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
