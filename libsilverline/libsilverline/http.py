"""Silverline HTTP Client."""

import json
import uuid
import requests
import logging

from beartype.typing import Optional, Union
from beartype import beartype

from .mqtt import MQTTClient, MQTTServer
from .util import dict_or_load


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
        self.__log = logging.getLogger("cli")

    @classmethod
    def from_config(
        cls, path_or_cfg: Union[str, dict], **kwargs
    ) -> "SilverlineClient":
        """Create from configuration."""
        cfg: dict = dict_or_load(path_or_cfg)
        api = "http://{}:{}/api".format(
            cfg.get("http", "localhost"), cfg.get("http_port", 8000))
        return cls(api=api, server=MQTTServer.from_config(cfg), **kwargs)

    def create_module(
        self, runtime: str, file: str, name: str = "module", args: dict = {}
    ) -> str:
        """Create module.

        Parameters
        ----------
        runtime: Runtime ID.
        file: Filepath to module binary/script, relative to the WASM/WASI base
            directory used by the runtime.
        name: Module short (human-readable) name.
        args: Additional execution args.

        Returns
        -------
        UUID of created module.
        """
        module = str(uuid.uuid4())
        payload = self.control_message("create", {
            "type": "module",
            "parent": runtime,
            "uuid": module,
            "name": name,
            "file": file,
            "args": args
        })
        self.publish(self.control_topic("control"), payload, qos=2)
        self.__log.info("Created module: {}:{} --> {}".format(
            module[-4:], file, runtime))
        return module

    def create_module_batch(
        self, runtime: str, file: Union[tuple[str], list[str]],
        name: Optional[Union[tuple[str], list[str]]] = None,
        args: Optional[Union[tuple[dict], list[dict]]] = None
    ) -> list[str]:
        """Create many modules in a single API call, all on a single runtime.

        Parameters
        ----------
        runtime: Runtime ID.
        file: Filepaths to module binary/script.
        name: Module short (human-readable) names.
        args: Additional execution args; leave None to pass `{}` to each.

        Returns
        -------
        UUID of each created module.
        """
        if args is None:
            args = [{} for _ in file]
        if name is None:
            name = file
        uuids = [str(uuid.uuid4()) for _ in file]
        payload = self.control_message("create_batch", {
            "modules": [{
                "type": "module", "uuid": u,
                "name": n, "file": f, "args": a
            } for u, n, f, a in zip(uuids, name, file, args)],
            "parent": runtime
        })
        self.publish(self.control_topic("control"), payload, qos=2)
        self.__log.info("Batch-created {} modules -> {}".format(
            len(file), runtime))
        return uuids

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

    def get_queued(self) -> list[dict]:
        """Get queued modules."""
        return self._get_json("queued/").get('results', [])
