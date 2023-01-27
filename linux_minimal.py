"""Minimum viable runtime."""

import os
import sys
import json
import subprocess
import threading

from manager import Message, SLSocket, Header


class LinuxMinimalRuntime:
    """Mimimal linux runtime."""

    def __init__(self, index):

        self.index = index
        self.socket = SLSocket(self.index, server=False, timeout=5.)
        self.process = None
        self.killed = False
        self.done = False

    def run(self, msg):
        """Run program."""
        self.killed = False
        self.process = subprocess.Popen(
            "python -u linux_minimal/linux_minimal.py",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        os.write(self.process.stdin.fileno(), msg.payload)

        data = json.loads(msg.payload)

        ch_open = bytes("\0std/{}".format(data["uuid"]), encoding='utf-8')
        self.socket.write(Message(0x80 | self.index, Header.ch_open, ch_open))

        # Each line is a new message. When the program terminates, we should
        # get EOF, which should terminate readline() with a falsy value.
        # print("entering...")
        # while True:
        #     line = self.process.stdout.readline()
        #     print(line)
        #    if line:
        #          print("line:", line)
        #         self.socket.write(Message(self.index, 0x00, line))
        #     else:
        #         break

        stdout, _ = (self.process.communicate())
        self.socket.write(Message(self.index, 0x00, stdout))

        rc = json.dumps({"status": "killed" if self.killed else "exited"})
        self.socket.write(Message(
            0x80 | self.index, Header.exited, bytes(rc, encoding='utf-8')))
        self.process = None

    def stop(self):
        """Stop program."""
        if self.process:
            self.killed = True
            self.process.kill()

    def loop(self):
        """Main loop."""
        while not self.done:
            msg = self.socket.read()
            if msg is not None:
                # Channel message
                if msg.h1 & 0x80 == 0:
                    self.process.stdin.write(msg.payload)
                else:
                    match msg.h2:
                        case Header.create:
                            self.thread = threading.Thread(target=self.run, args=[msg])
                            self.thread.start()
                        case Header.delete:
                            self.stop()
                        case Header.stop:
                            self.done = True
                            self.stop()
                        case _:
                            pass

    def loop_start(self):
        """Start loop."""
        threading.Thread(target=self.loop).start()


if __name__ == '__main__':
    LinuxMinimalRuntime(int(sys.argv[1])).loop()
