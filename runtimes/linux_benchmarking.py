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

In module create message::

    {
        ...
        "repeat": 100,
        ...
    }


realm/proc/profile/{mode}/{module-uuid}
All unsighed integers.
mode = "benchmarking":
    24b:   [utime /32 ][stime /32 ][maxrss /u32]

mode = "opcodes":
    1024b: [ ------------ op_count /32 x 256 ------------ ]

mode = "instrumented":
    4Nb:   [ ------------ loop_count /32 x N ------------ ]

mode = "deployed":
    (periodic mode)
    32b:   [ ---- start /u64 ---- ][ wall /32 ][utime /32 ]
           [stime /32 ][maxrss /32][ch_in /32 ][ch_out /32]


Benchmark message::

    wall /32
    cpu /32
"""

import os
import sys
import json
import threading
import numpy as np

from manager import Message, SLSocket, Header


class LinuxBenchmarkingRuntimeWasmer:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index):
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None
        self.stop = False
        self.done = False

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        stats = np.zeros([data["resources"]["repeat"], 3], dtype=np.uint32)
        for i in range(data["resources"]["repeat"]):
            self.process = os.fork()
            if self.process == 0:
                os.execve("wasmer", [
                    "--env", *data["env"], data["filename"], *data["args"]])
            else:
                _, status, rusage = os.wait4(self.process, 0)
                if status != 0:
                    self.socket.write(Message.from_str(
                        Header.control | 0x00, Header.log_module,
                        "Nonzero exit code: {}".format(status)
                    ))
                stats[i][0] = rusage.ru_utime
                stats[i][1] = rusage.ru_stime
                stats[i][2] = rusage.ru_maxrss

            if self.stop:
                break

        self.socket.write(Message(
            Header.control | 0x00, Header.profile, stats.tobytes()))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited,
            {"status": "killed" if self.killed else "exited"}))

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
                    if self.process is not None:
                        os.kill(self.process)
                case _:
                    pass

    def loop(self):
        """Main loop."""
        while not self.done:
            msg = self.socket.read()
            if msg is not None:
                self.handle_message(msg)


if __name__ == '__main__':
    LinuxBenchmarkingRuntimeWasmer(int(sys.argv[1])).loop()
