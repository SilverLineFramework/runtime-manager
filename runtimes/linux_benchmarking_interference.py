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
            if self.process[i] == 0:
                try:
                    os.execvp(cmd[0], cmd)
                except Exception as e:
                    os._exit(1)
            else:
                _, status, rusage = os.wait4(self.process[i], 0)
                if os.waitstatus_to_exitcode(status) != 0:
                    stats.append(0)
                    break
                else:
                    stats.append(
                        int(rusage.ru_utime * 10**6)
                        + int(rusage.ru_stime * 10**6))
        if len(stats) > 2:
            return sum(stats[1:-1]) / (len(stats) - 2)
        else:
            return 0

    def __run(self, files, cmds, limit):

        def kill():
            self.done = True
            for p in self.process:
                os.kill(p, signal.SIGKILL)

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

    def __make_cmd(self, file, args):
        engine = args.get("engine", "wasmer run --singlepass")
        if engine == "native":
            cmd = [file]
        else:
            cmd = engine.split(" ") + ["--dir=.", file]
        return cmd

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        args = data.get("args", {})

        files = data.get("file").split(":")
        cmds = [self.__make_cmd(f, args) for f in files]
        self.process = [None for _ in files]

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
