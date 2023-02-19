"""Cluster management."""

import json
import argparse
import os

from beartype.typing import NamedTuple, Union
from beartype import beartype


@beartype
class SilverlineCluster(NamedTuple):
    """Silverline Cluster Configuration.

    Attributes
    ----------
    manifest: Device manifest; should be a path to a TSV file.
    domain: Cluster domain to append to node names.
    username: Common username for cluster nodes.
    http: Orchestrator server address.
    http_port: Orchestrator port.
    file_store: File store server.
    file_store_port: File store port.
    """

    manifest: str
    domain: str
    username: str
    http: str
    http_port: int
    file_store: str
    file_store_port: int

    @classmethod
    def from_config(cls, cfg: Union[str, dict]):
        """Load settings from configuration file or dict."""
        if isinstance(cfg, str):
            with open(cfg) as f:
                cfg = json.load(f)

        return cls(
            manifest=cfg.get("manifest", None),
            domain=cfg.get("domain", ""),
            username=cfg.get("username", "cli"),
            http=cfg.get("http", "localhost"),
            http_port=cfg.get("http_port", 8000),
            file_store=cfg.get("file_store", "localhost"),
            file_store_port=cfg.get("file_store_port", 8001)
        )

    @staticmethod
    def make_args(p: argparse.ArgumentParser) -> None:
        """Add Silverline cluster to argument parser."""
        g = p.add_argument_group("Cluster")
        g.add_argument(
            "--manifest", default=None, help="Device manifest file path.")
        g.add_argument(
            "--domain", default="",
            help="Cluster domain to append to node names.")
        g.add_argument(
            "--username", default="cli",
            help="Common username for cluster nodes.")
        g.add_argument(
            "--http", default="localhost:8000", help="Orchestrator server.")
        g.add_argument(
            "--file_store", help="File Store server", default="localhost:8001")

    @staticmethod
    def make_config(args: argparse.Namespace) -> dict:
        """Get config from argparse parsed args."""
        def _expandpath(p):
            if p is None:
                return None
            else:
                return os.path.abspath(os.path.expanduser((p)))

        return {
            "manifest": _expandpath(args.manifest),
            "domain": args.domain,
            "username": args.username,
            "http": args.http.split(":")[0],
            "http_port": int(args.http.split(":")[1]),
            "file_store": args.file_store.split(":")[0],
            "file_store_port": int(args.file_store.split(":")[1])
        }
