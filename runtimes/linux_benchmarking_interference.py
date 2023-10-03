"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import struct
import signal
from functools import partial
from multiprocessing.pool import ThreadPool

from libsilverline import Message, SLSocket, Header
from common import make_command, run_and_wait


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index):
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = []
        self.done = False

    def __run_repeat(self, args):
        i, cmd = args

        stats = []
        while not self.done:
            self.process[i] = os.fork()
            err, rusage = run_and_wait(self.process[i], cmd)
            if err != 0:
                stats.append(0)
            else:
                stats.append(
                    int(rusage.ru_utime * 10**6)
                    + int(rusage.ru_stime * 10**6))
        return stats

    def __run(self, files, cmds, limit):

        def kill():
            self.done = True
            for p in self.process:
                try:
                    os.kill(p, signal.SIGKILL)
                except:
                    pass

        self.done = False
        watchdog = threading.Timer(limit, kill)
        watchdog.start()

        with ThreadPool(len(cmds)) as p:
            results = p.map(self.__run_repeat, enumerate(cmds))

        watchdog.cancel()
        return {
            "{}:{}".format(i, f): v
            for i, (f, v) in enumerate(zip(files, results))
        }

    def _make_cmd(self, file, argv, args):
        """Assemble shell command."""
        engine = args.get("engine", "iwasm-i")
        return make_command(engine, file, argv)

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        args = data.get("args", {})

        files = data.get("file").split(":")
        argv = args.get("argv", [])
        cmds = [self._make_cmd(f, argv, args) for f in files]
        self.process = [-1 for _ in files]

        stats = self.__run(files, cmds, args.get("limit", 60.0))

        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.profile, stats))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited, {"status": "exited"}))

    def handle_message(self, msg: Message) -> None:
        """Handle message from manager."""
        match (msg.h1 & Header.control, msg.h1 & Header.index_bits, msg.h2):
            case (0x00, _, _):
                pass
            case (Header.control, _, Header.create):
                self.run(msg)
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
