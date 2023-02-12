"""Linux benchmarking runtime.

Benchmark spec::

    benchmark/
        benchmark.wasm
        benchmark.json
        data/ (optional)
            data.file.1
            data.file.2
            ...

In benchmark.json::

    {
        "args": ["argv", "to", "pass"],
        "env": ["envvar=value"],
        "inputs": [
            {"args": ["--data", "data.file.1"], "env": ["index=1"]},
            {"args": ["--data", "data.file.2"], "env": ["index=2"]},
            ...
        ]
    }
"""

import os
import sys
import json
import threading
import numpy as np

from manager import Message, SLSocket, Header


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index):
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None
        self.stop = False
        self.done = False

    def __run(self, data):
        # repeat = data.get("resources", {}).get("repeat", 1)
        repeat = 1
        stats = np.zeros([repeat, 3], dtype=np.uint32)
        for i in range(repeat):
            self.process = os.fork()
            if self.process == 0:
                os.execvp("wasmer", [
                    "--env", *data["env"], data["filename"], *data["args"]])
            else:
                _, status, rusage = os.wait4(self.process, 0)
                if status != 0:
                    self.socket.write(Message.from_str(
                        Header.control | 0x00, Header.log_module,
                        "Nonzero exit code: {}".format(status)
                    ))
                stats[i][0] = int(rusage.ru_utime * 10**6)
                stats[i][1] = int(rusage.ru_stime * 10**6)
                stats[i][2] = rusage.ru_maxrss

            if self.stop:
                return stats[:i + 1]

        return stats

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        stats = self.__run(data)

        self.socket.write(Message(
            Header.control | 0x00, Header.profile, stats.tobytes()))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited,
            {"status": "killed" if self.stop else "exited"}))

    def handle_message(self, msg: Message) -> None:
        """Handle message from manager."""
        if msg.h1 & Header.control == 0:
            pass
        else:
            match msg.h2:
                case Header.create:
                    threading.Thread(target=self.run, args=[msg]).start()
                case Header.delete:
                    self.stop = True
                case _:
                    pass

    def loop(self):
        """Main loop."""
        while not self.done:
            msg = self.socket.read()
            if msg is not None:
                self.handle_message(msg)


if __name__ == '__main__':
    LinuxBenchmarkingRuntime(int(sys.argv[1])).loop()
