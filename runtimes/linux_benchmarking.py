"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import numpy as np

from libsilverline import Message, SLSocket, Header


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index):
        self.socket = SLSocket(index, server=False, timeout=1.)
        self.process = None
        self.stop = False
        self.done = False

    def __run(self, cmd, repeat):
        stats = []
        for _ in range(repeat):
            self.process = os.fork()
            if self.process == 0:
                os.execvp("wasmer", cmd)
            else:
                _, status, rusage = os.wait4(self.process, 0)
                if status != 0:
                    self.socket.write(Message.from_str(
                        Header.control | 0x00, Header.log_module,
                        "Nonzero exit code: {}".format(status)
                    ))
                stats.append((
                    int(rusage.ru_utime * 10**6),
                    int(rusage.ru_stime * 10**6),
                    rusage.ru_maxrss))
            if self.stop:
                break

        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module,
            "Exited with {} samples.".format(len(stats))))
        return np.array(stats, dtype=np.uint32)

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        args = data.get("args", {})
        cmd = ["run", "--singlepass"]
        if "env" in args and args["env"]:
            cmd += ["--env"] + args["env"]
        cmd += [data.get("file")] + args.get("argv", [])[1:]

        stats = self.__run(cmd, args.get("repeat", 1))

        self.socket.write(Message(
            Header.control | 0x00, Header.profile, stats.tobytes()))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited,
            {"status": "killed" if self.stop else "exited"}))

    def handle_message(self, msg: Message) -> None:
        """Handle message from manager."""
        match (msg.h1 & Header.control, msg.h1 & Header.index_bits, msg.h2):
            case (0x00, _, _):
                pass
            case (Header.control, _, Header.create):
                threading.Thread(target=self.run, args=[msg]).start()
            case (Header.control, _, Header.delete):
                self.stop = True
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
