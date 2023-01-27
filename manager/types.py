"""SilverLine Messaging and Types."""

import json
from beartype.typing import NamedTuple, Union


class Header:
    """Header enum."""

    keepalive = 0x00
    log_runtime = 0x01
    exited = 0x02
    ch_open = 0x03
    ch_close = 0x04
    log_module = 0x05
    profile = 0x06

    create = 0x00
    delete = 0x01
    stop = 0x02


class Message(NamedTuple):
    """Runtime-manager message.

    | Sender  | Header    | Socket      | Message          | Data   |
    | ------- | --------- | ----------- | -----------------| ------ |
    | Manager | 1{m}.x00  | sl/{rt}     | Create Module    | json   |
    | Manager | 1{m}.x01  | sl/{rt}     | Delete Module    | null   |
    | Manager | 1{-}.x02  | sl/{rt}     | Stop Runtime     | null   |
    | Manager | 0{m}.{fd} | sl/{rt}/{m} | Receive Message  | u8[]   |
    | Runtime | 1{-}.x00  | sl/{rt}     | Keepalive        | json   |
    | Runtime | 1{-}.x01  | sl/{rt}     | Runtime Logging  | char[] |
    | Runtime | 1{m}.x02  | sl/{rt}     | Module Exited    | json   |
    | Runtime | 1{m}.x03  | sl/{rt}     | Open Channel     | char[] |
    | Runtime | 1{m}.x04  | sl/{rt}     | Close Channel    | u8     |
    | Runtime | 1{m}.x05  | sl/{rt}     | Module Logging   | char[] |
    | Runtime | 1{m}.x06  | sl/{rt}     | Profiling Data   | char[] |
    | Runtime | 0{m}.{fd} | sl/{rt}     | Publish Message  | u8[]   |

    Notes
    -----
    - Channel open has the target channel index as the first value.
    - The module index ({m}) is a 7-bit integer (0<=i<128); this index is
      controlled and enforced by the runtime manager.
    - The channel index is a 8-bit integer (0<=j<256); this index is controlled
      by the runtime interface. The limit is enforced by physical limits on the
      value.

    Add "dir" (list[str]) -- WASI dirs -- attribute to CreateModuleMsg/data
    Add "reason" (object) attribute to ModuleExitMsg/data

    Attributes
    ----------
    h1: first header value.
    h2: second header value.
    payload: message contents.
    """

    h1: int
    h2: int
    payload: bytes

    def __init__(self, h1: int, h2: int, payload: Union[bytes, str, dict]):
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        if isinstance(payload, str):
            payload = bytes(payload, encoding='utf-8')
        super().__init__(h1, h2, payload)


class MQTTServer(NamedTuple):
    """MQTT login.

    Attributes
    ----------
    host: MQTT server web address.
    port: Server port number (usually 1883 or 8883 if using SSL).
    user: Username.
    pwd: Password.
    ssl: Whether server has TLS/SSL enabled.
    """

    host: str
    port: int
    user: str
    pwd: str
    ssl: bool


class Channel(NamedTuple):
    """Open Channel.

    Attributes
    ----------
    runtime: Runtime index.
    module: Module index for this runtime.
    fd: Channel index for this module.
    topic: Topic name.
    """

    runtime: int
    module: int
    fd: int
    topic: str
