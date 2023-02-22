"""Silverline HTTP Client."""

import json
import uuid
import requests

from beartype.typing import Optional, Union
from beartype import beartype

from .mqtt import MQTTClient, MQTTServer


@beartype
class SilverlineClient(MQTTClient):
    """Silverline HTTP Client."""

    def __init__(
        self, name: str = "cli", api: str = "localhost:8000",
        server: Optional[MQTTServer] = None
    ) -> None:
        super().__init__(
            client_id="{}:{}".format(name, str(uuid.uuid4())), server=server)
        self.api = api

    @classmethod
    def from_config(
        cls, cfg: Union[str, dict], *args, **kwargs
    ) -> "SilverlineClient":
        """Create from configuration."""
        if isinstance(cfg, str):
            with open(cfg) as f:
                cfg = json.load(f)
        api = "http://{}:{}/api".format(
            cfg.get("http", "localhost"), cfg.get("http_port", 8000))
        return cls(
            *args, api=api, server=MQTTServer.from_config(cfg), **kwargs)

    def create_module(
        self, runtime: str, name: str = "module",
        file: str = "wasm/apps/helloworld.wasm", argv: list[str] = [],
        env: list[str] = [], engine: Optional[list[str]] = None,
        period: int = 10 * 1000 * 1000, utilization: float = 0.0,
        repeat: Optional[int] = None
    ) -> str:
        """Create module.

        Parameters
        ----------
        runtime: Runtime ID.
        name: Module short (human-readable) name.
        file: Filepath to module binary/script, relative to the WASM/WASI base
            directory used by the runtime.
        argv: Argument passthrough to the module.
        env: Environment variables to set.
        engine: WASM engine to use for benchmarking.
        period: Period for sched_deadline, in nanoseconds.
        utilization: Utilization for sched_deadline. If 0.0, uses CFS.
        repeat: Number of times to run module if benchmarking.

        Returns
        -------
        UUID of created module.
        """
        module_uuid = str(uuid.uuid4())
        args = {"argv": [file] + argv, "env": env}
        if utilization > 0:
            c = int(utilization * period)
            args["resources"] = {"period": period, "runtime": c}
        if repeat != 0:
            args["repeat"] = repeat
        if engine is not None:
            args["engine"] = engine

        payload = self.control_message("create", {
            "type": "module",
            "parent": runtime,
            "uuid": module_uuid,
            "name": name,
            "file": file,
            "args": args
        })
        self.publish(self.control_topic("control"), payload, qos=2)

        return module_uuid

    def delete_module(self, module: str) -> None:
        """Delete module."""
        payload = self.control_message("delete", {
            "type": "module", "uuid": module})
        self.publish(self.control_topic("control"), payload, qos=2)

    def infer_runtime(self, runtime: str) -> Optional[str]:
        """Infer runtime UUIDs."""
        return self._get_json("{}/{}".format("runtimes", runtime)).get('uuid')

    def infer_module(self, module: str) -> Optional[str]:
        """Infer module UUIDs."""
        return self._get_json("{}/{}".format("modules", module)).get('uuid')

    def _get_json(self, address) -> dict:
        """Get JSON from REST API."""
        r = requests.get("{}/{}/".format(self.api, address))
        if r:
            try:
                return json.loads(r.text)
            except Exception as e:
                print(r.text)
                raise e
        return {}

    def get_runtimes(self) -> list[dict]:
        """Get runtimes from REST API."""
        return self._get_json("runtimes").get('results', [])

    def get_modules(self) -> list[dict]:
        """Get modules from REST API."""
        return self._get_json("modules").get('results', [])

    def get_runtime(self, rt) -> dict:
        """Get runtime full metadata from REST API."""
        return self._get_json("runtimes/{}".format(rt))

    def get_module(self, mod) -> dict:
        """Get module full metadata from REST API."""
        return self._get_json("modules/{}".format(mod))
