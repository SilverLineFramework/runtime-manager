# Manager-based Runtime Refactor

![Manager Architecture](manager_architecture.PNG)

## Creating Runtimes

### Runtime Manager

Runtime interfaces should extend ```RuntimeManager```. Three methods need to be implemented:
```python
class RuntimeManager:
    # ...

    @abstractmethod
    def start(self) -> dict:
        """Start runtime, and return the registration config."""
        pass

    @abstractmethod
    def send(self, msg: Message) -> None:
        """Send message to runtime."""
        pass

    @abstractmethod
    def receive(self) -> Optional[Message]:
        """Poll interface and receive message; return None on timeout."""
        pass

    # ...
```

Then, set the runtime configuration:
```python
class RuntimeManager:
    # ...

    TYPE = "abstract"
    APIS = []
    MAX_NMODULES = 0

    # ...
```

- ```TYPE```: the ```runtime_type``` reported to the orchestrator, i.e. "linux/minimal".
- ```APIS```: available local APIs; exact specifications are **TODO**.
- ```MAX_NMODULES```: maximum number of modules supported; should usually be 128 for fully-featured runtimes, or 1 for minimum-viable-runtimes without multi-module support.

Optionally, runtime managers can also overwrite the ```create_module```, ```delete_module```, and ```cleanup_module``` methods to perform different/additional actions on create/delete/exit:

```python
class RuntimeManager:
    # ...

    def create_module(self, data: dict) -> None:
        """Create module; overwrite this method to add additional steps."""
        index = self.modules.insert(data)
        data["index"] = index
        self.send(Message.from_dict(
            Header.control | index, Header.create, data))

    def delete_module(self, module_id: str) -> None:
        """Delete module."""
        try:
            index = self.modules.get(module_id)
            self.send(Message(Header.control | index, Header.delete, bytes()))
        except KeyError:
            raise exceptions.ModuleException("Nonexisting module.", module_id)

    def cleanup_module(self, idx: int, mid: str, msg: Message) -> None:
        """Clean up module after exiting."""
        self.mgr.publish(
            self.control_topic("control"),
            self.mgr.control_message("exited", {
                "type": "module", "uuid": mid, **json.loads(msg.payload)}))
        self.mgr.channels.cleanup(self.index, idx)
        self.modules.remove(idx)

    # ...
```

###  Example

The ```linux/minimal``` runtime is the minimal code required to run WebAssembly modules and receive the output. The minimal linux runtime uses the ```SLSocket``` communication channel:
```
[ -- len:4 -- ][h1:1][h2:1][ ------ payload:len ------ ]
```

See ```runtimes/linux_minimal.py``` (runtime-side) and ```manager/runtimes/linux_minimal.py``` (manager-side) for a minimal example.

## Messaging

The manager reads messages from MQTT, and parses them before passing on a corresponding message to the relevant runtime(s) if required. Each runtime is assumed to have its own communication channel, or communicate over a shared channel which can specify the runtime.

Messages have two header bytes (h1, h2), and are designed for arbitrary communication streams.
- The first byte indicates the module index `{m}` with the lower 7 bits, and whether the message is an ordinary channels message or a control message with the upper bit.

    **NOTE**: this creates a 128 modules per runtime limit, though this can be increased by increasing the header size.

- The second byte indicates an argument, which is the message type for control messages, and the channel index for channel messages.

    **NOTE**: This limits modules to opening 256 channels, which can again be increased through a larger header.

The following messages are currently specified:

| Sender  | Header    | Message          | Data         | Topic            |
| ------- | --------- | -----------------| ------------ | ---------------- |
| Manager | 1{m}.x00  | Create Module    | json         | .../control/{rt} |
| Manager | 1{m}.x01  | Delete Module    | null         | .../control/{rt} |
| Manager | 1{-}.x02  | Stop Runtime     | null         | .../control/{rt} |
| Manager | 0{m}.{fd} | Receive Message  | u8[]         | {topic}          |
| Runtime | 1{-}.x00  | Keepalive        | json         | .../control/{rt} |
| Runtime | 1{-}.x01  | Runtime Logging  | char[]       | .../control/{rt} |
| Runtime | 1{m}.x02  | Module Exited    | json         | .../control/{rt} |
| Runtime | 1{m}.x03  | Open Channel     | u8,u8,char[] | n/a              |
| Runtime | 1{m}.x04  | Close Channel    | u8           | n/a              |
| Runtime | 1{m}.x05  | Module Logging   | char[]       | .../log/{m}      |
| Runtime | 1{m}.x06  | Profiling Data   | char[]       | .../profile/...  |
| Runtime | 0{m}.{fd} | Publish Message  | u8[]         | {topic}          |

### Create Module

The create module message is encoded as a ```json```, which passes on fields sent by the orchestrator. Individual runtimes can overwrite ```RuntimeManager.create_module``` to encode messages differently.

From orchestrator:
```json
{
    "object_id": "fcb2780b-abdd-43b6-bc13-895baa2075a3",
    "action": "create",
    "type": "arts_req",
    "data": {
        "type": "module",
        "uuid": "44c72c87-c4ec-4759-b587-30ddc8590f6b",
        "name": "test",
        ... other fields ...
    }
}
```

To runtime:
```json
{
    "index": 0,
    "uuid": "44c72c87-c4ec-4759-b587-30ddc8590f6b",
    "name": "test",
    ... other fields ...
}
```

Here, ``index`` indicates the module index to be used in the communication header. The ```other fields``` are provided by the orchestrator, and can vary per runtime.

### Delete Module

The delete module message has no payload; the index in the header specifies the target module.

### Stop Runtime

The stop runtime message has no payload or module index.

### Receive Message

Channel messages are passed without any encoding, i.e. passing the MQTT ```msg.payload``` directly as the payload.

### Keepalive

Runtimes can publish arbitrary JSON for keepalive messages:

```json
{
    "object_id": "50c2f088-a5b6-48c5-bbc7-4a693b0117a2",
    "action": "update",
    "type": "arts_req",
    "data": {
        "type": "runtime",
        "uuid": "5f937916-d29d-4f66-801e-3d69f57728e2",
        "name": "rt1",
        "apis": ["wasi:unstable", "wasi:snapshot_preview1"],
        ... other fields ...
}
```

The ```other fields``` can be any JSON passed by the runtime; the keys inside the json (which must have a dict as the outer-most layer) are added to the ```data``` attribute.

### Runtime Logging

Runtime logging messages are forwarded to ```{realm}/proc/log/{runtime_id}``` with no additional processing.

### Module Exited

On module exit, any metadata (```other fields```) returned as a JSON is forwarded to the orchestrator:

```json
{
    "object_id": "fcb2780b-abdd-43b6-bc13-895baa2075b4",
    "action": "exited",
    "type": "arts_req",
    "data": {
        "type": "module",
        "uuid": "44c72c87-c4ec-4759-b587-30ddc8590f6b",
        ... other fields ...
    }
}
```

### Open Channel

The open channel message is a binary format, with two header bytes:

```
| channel index | channel flags | ... topic name ... |
```

The channel index is an unsigned byte used to index the channel (the same as the header in publish and receive messages); the channel flags (bitwise) indicate the read/write mode, as well as MQTT QoS:

```python
read      = 0b0001
write     = 0b0010
readwrite = 0b0011

qos0      = 0b0000
qos1      = 0b0100
qos2      = 0b1000
```

### Close Channel

The close channel message takes a single argument - the channel index (unsigned byte).

### Module Logging

Logging messages are directly forwarded to ```{realm}/proc/log/{module_id}```.

### Profiling

Profiling messages are forwarded to ```{realm}/proc/profile/{profile_type}/{module_id}```.

### Publish Message

Published messages are passed to their corresponding topic. Any runtimes with the same manager with channels subscribed to this topic also receive the published message as a loopback; the manager is configured as a gateway, so will not receive messages that it sends.

## Todos

- Add wasi dirs "dir" (list[str]) attribute to Create Module
- Add "status" (object) attribute to Module Exited

