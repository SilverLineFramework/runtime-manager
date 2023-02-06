"""Minimum viable runtime."""

import os
import sys
import json
import threading
from subprocess import Popen, PIPE

from manager import Message, SLSocket, Header, Flags


class LinuxMinimalRuntime:
    """Mimimal linux runtime using wasmer.

    Only supports one-shot stdin/stdout for a single module.
    """

    def __init__(self, index, cmd=["wasmer"]):
        self.cmd = cmd
        self.socket = SLSocket(index, server=False, timeout=5.)
        self.process = None
        self.killed = False
        self.done = False

    def run(self, msg):
        """Run program."""
        self.killed = False
        data = json.loads(msg.payload)

        cmd = self.cmd
        if "env" in data and data["env"]:
            cmd += ["--env"] + data["env"]
        cmd += [data["filename"]] + data["args"][1:]
        print(cmd)
        self.process = Popen(cmd, stdin=PIPE, stdout=PIPE, shell=True)

        self.socket.write(Message(
            Header.control | 0x00, Header.ch_open,
            bytes([0x00, Flags.readwrite])
            + bytes("std/{}".format(data["uuid"]), encoding='utf-8')))

        stdout, _ = (self.process.communicate())
        self.socket.write(Message(0x00, 0x00, stdout))
        self.socket.write(Message.from_dict(
            Header.control | 0x00, Header.exited,
            {"status": "killed" if self.killed else "exited"}))
        self.process = None

    def handle_message(self, msg: Message) -> None:
        """Handle message from manager."""
        if msg.h1 & Header.control == 0:
            self.process.stdin.write(msg.payload)
        elif msg.h2 == Header.create:
                threading.Thread(target=self.run, args=[msg]).start()

    def loop(self):
        """Main loop."""
        while not self.done:
            msg = self.socket.read()
            if msg is not None:
                self.handle_message(msg)


if __name__ == '__main__':
    LinuxMinimalRuntime(int(sys.argv[1])).loop()
