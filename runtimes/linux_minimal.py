"""Minimum viable runtime."""

import sys
import json
import threading
from subprocess import Popen, PIPE
from beartype.typing import Optional, IO

from libsilverline import Message, SLSocket, Header, Flags


class LinuxMinimalRuntime:
    """Mimimal linux runtime using wasmer.

    Only supports one-shot stdin/stdout for a single module.
    """

    def __init__(self, index: int, cmd: str = "wasmer run") -> None:
        self.cmd = cmd
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.pipe: Optional[IO[bytes]] = None

    def run(self, msg: Message) -> None:
        """Run program."""
        data = json.loads(msg.payload)
        cmd = [self.cmd]
        args = data.get("args", {})
        if "env" in args and args["env"]:
            cmd += ["--env"] + args["env"]
        cmd += [data.get("file")] + args.get("argv", [])

        process = Popen(" ".join(cmd), stdin=PIPE, stdout=PIPE, shell=True)
        self.pipe = process.stdin
        self.socket.write(Message(
            Header.control | 0x00, Header.ch_open,
            bytes([0x00, Flags.readwrite])
            + bytes("$SL/proc/stdio", encoding='utf-8')))

        stdout, _ = process.communicate()
        self.socket.write(Message(0x00, 0x00, stdout))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited, {"status": "exited"}))

    def handle_message(self, msg: Message) -> None:
        """Handle message from manager."""
        if msg.h1 & Header.control == 0:
            if self.pipe is not None:
                self.pipe.write(msg.payload)
        elif msg.h2 == Header.create:
            threading.Thread(target=self.run, args=[msg]).start()

    def loop(self) -> None:
        """Main loop."""
        while True:
            msg = self.socket.read()
            if msg is not None:
                self.handle_message(msg)


if __name__ == '__main__':
    LinuxMinimalRuntime(int(sys.argv[1])).loop()
