"""Inner runtime.

This needs to be a completely separate process from the runtime communication
layer since we want to capture stdin/stdout without help from the inner WASM
runtime.
"""

import os
import json

from wasmer import wasi, Store, Module, Instance


def run():
    """Run module with WASI.

    Steps taken from:
    https://github.com/wasmerio/wasmer-python/blob/master/examples/wasi.py
    """
    # Fetch start message from stdin
    msg = json.loads(input(''))

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


if __name__ == '__main__':
    run()
