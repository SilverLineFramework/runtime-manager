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

    def __init__(self, index: int) -> None:
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None

    def _run(self, cmd):
        """Run single benchmark iteration."""
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
                return None
            else:
                return struct.pack(
                    "III",
                    int(rusage.ru_utime * 10**6),
                    int(rusage.ru_stime * 10**6),
                    rusage.ru_maxrss)

    def _run_loop(self, cmds, limit):
        """Run benchmarking loop."""

        def kill():
            os.kill(self.process, signal.SIGKILL)

        watchdog = threading.Timer(limit, kill)
        watchdog.start()

        stats = []
        for cmd in cmds:
            res = self._run(cmd)
            if res is None:
                stats.append(struct.pack("III", 0, 0, 0))
                break
            else:
                stats.append(res)

        self.socket.write(Message.from_str(
            Header.control | 0x00, Header.log_module,
            "Exited with {} samples.".format(len(stats))))

        watchdog.cancel()
        return b''.join(stats)

    def _make_cmd(self, file, args):
        """Assemble shell command."""
        engine = args.get("engine", "wasmer run --singlepass --")

        if engine == "native":
            cmd = [file] + args.get("argv", [])
        else:
            cmd = engine.split(" ")
            # Ends in '--': runtime, module args separated by '--'
            cmd, sep = (cmd[:-1], True) if cmd[-1] == "--" else (cmd, False)

            cmd += ["--dir=."]
            cmd += ["--env=\"{}\"".format(var) for var in args.get("env", [])]
            cmd += [file]
            cmd += ["--"] if sep else []
            cmd += args.get("argv", [])
        return cmd

    def run(self, msg):
        """Run program."""
        self.stop = False
        data = json.loads(msg.payload)

        args = data.get("args", {})
        argv = args.get("argv", [])
        file = data.get("file")
        if len(argv) > 0 and isinstance(argv[0], str):
            cmd = self._make_cmd(file, argv)
            cmds = [cmd] * args.get("repeat", 1)
        else:
            cmds = [self._make_cmd(file, a) for a in argv]

        stats = self._run_loop(cmds, args.get("limit", 60.0))

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
