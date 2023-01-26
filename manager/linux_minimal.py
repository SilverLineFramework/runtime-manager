"""Minimum viable runtime."""

import os

from wasmer import engine, wasi, Store, Module, Instance

from .types import Message
from .sockets import socket_connect, socket_read, socket_write


class LinuxMinimalRuntime:
    """Mimimal linux runtime."""

    def __init__(self, index):

        self.index = index
        self.socket = socket_connect(self.index, server=False, timeout=5.)

    def run(self, msg):
        """Run module with WASI.

        Steps taken from:
        https://github.com/wasmerio/wasmer-python/blob/master/examples/wasi.py
        """
        store = Store()

        with open(msg["filename"], 'rb') as f:
            wasm_bytes = f.read()

        module = Module(store, wasm_bytes)
        wasi_version = wasi.get_version(module, strict=True)

        wasi_env = wasi.StateBuilder(os.path.basename(msg["filename"]))
        for arg in msg["args"]:
            wasi_env = wasi_env.argument(arg)
        for env in msg["env"]:
            wasi_env = wasi_env.environment(*env.split('='))
        wasi_env.map_directory('.', '.')
        wasi_env = wasi_env.finalize()

        import_object = wasi_env.generate_import_object(
            store, wasi_version)
        instance = Instance(module, import_object)

        instance.exports._start()

    def receive(self):
        msg = socket_read(self.socket)

        if msg.h1 & 0x80 == 0:
            # stdin
            pass
        else:
            # Create
            if msg.h2 == 0:
                pass
            # Delete
            elif msg.h2 == 1:
                pass
            else:
                pass

    def channel_write(self, payload):
        socket_write(self.socket, Message(self.index, 0, payload))
