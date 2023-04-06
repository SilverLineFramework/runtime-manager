# Creating Runtimes

## Runtime Manager

Runtime interfaces should extend `RuntimeManager`. Three methods need to be implemented:
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

    TYPE: str = "abstract"
    APIS: list[str] = []
    MAX_NMODULES: int = 0
    DEFAULT_NAME: str = "runtime"
    DEFAULT_SHORTNAME: str = "rt"

    # ...
```

- `TYPE`: the `runtime_type` reported to the orchestrator, i.e. "linux/minimal".
- `APIS`: available local APIs; exact specifications are **TODO**.
- `MAX_NMODULES`: maximum number of modules supported; should usually be 128 for fully-featured runtimes, or 1 for minimum-viable-runtimes without multi-module support.
- `DEFAULT_NAME`, `DEFAULT_SHORTNAME`: default names for display, logging, and other UI.

Optionally, runtime managers can also overwrite the `create_module`, `delete_module`, and `cleanup_module` methods to perform different/additional actions on create/delete/exit:

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

##  Example

The `linux/minimal` runtime is the minimal code required to run WebAssembly modules and receive the output. The minimal linux runtime uses the `SLSocket` communication channel, with packet format:
```
[ -- len:2 -- ][h1:1][h2:1][ ------ payload:len ------ ]
```
The header has total size 4 bytes. Note that the length item in the header corresponds to the length of the payload portion, not the entire message.

See `runtimes/linux_minimal.py` (runtime-side) and `interfaces/linux_minimal.py` (manager-side) for a minimal example.
