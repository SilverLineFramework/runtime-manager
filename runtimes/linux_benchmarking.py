"""Linux benchmarking runtime."""

import os
import sys
import json
import threading
import struct
import signal

from libsilverline import Message, SLSocket, Header


class LinuxBenchmarkingRuntime:
    """Mimimal linux benchmarking runtime."""

    def __init__(self, index):
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None

    def __run(self, cmd, repeat, limit):

        def kill():
            os.kill(self.process, signal.SIGKILL)

        watchdog = threading.Timer(limit, kill)
        watchdog.start()

        stats = []
        for _ in range(repeat):
            self.process = os.fork()
            if self.process == 0:
                try:
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
                    stats.append(struct.pack("III", 0, 0, 0))
                    break
                else:
                    stats.append(struct.pack(
                        "III",
                        int(rusage.ru_utime * 10**6),
                        int(rusage.ru_stime * 10**6),
                        rusage.ru_maxrss))

        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module,
            "Exited with {} samples.".format(len(stats))))

        watchdog.cancel()
        return b''.join(stats)

    def _make_cmd(self, file, args):
        engine = args.get("engine", "wasmer run --singlepass")
        if engine == "native":
            cmd = [file] + args.get("argv", [])
        else:
            cmd = engine.split(" ")
            cmd += ["--env=\"{}\"".format(var) for var in args.get("env", [])]
            cmd += [file] + args.get("argv", [])
        return cmd

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        args = data.get("args", {})
        cmd = self._make_cmd(data.get("file"), args)
        stats = self.__run(cmd, args.get("repeat", 1), args.get("limit", 60.0))

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
