"""Profiling server."""

import logging
import os
import argparse
import json
import traceback
import time

import numpy as np

from beartype import beartype
from beartype.typing import Optional, Union

from libsilverline import SilverlineClient, MQTTServer, configure_log


class ProfilerException(Exception):
    """Base class for profiling-related exceptions."""

    def __init__(self, msg):
        self.msg = msg


@beartype
class Profiler(SilverlineClient):
    """Profiling server."""

    _BANNER = r"""
     ___       _ _
    | _ ) __ _| | |___  ___ _ _
    | _ \/ _` | | / _ \/ _ \ ' \
    |___/\__,_|_|_\___/\___/_||_|
     Silverline: Data Collection
    """

    def __init__(
        self, name: str = "profiler", base_path: str = "data",
        api: str = "localhost:8000", server: Optional[MQTTServer] = None
    ) -> None:
        super().__init__(name=name, api=api, server=server)

        self.log = logging.getLogger("profile")
        self.name = name
        self.base_path = base_path
        self._modules = {}
        self._runtimes = {}

    @classmethod
    def from_config(cls, cfg: Union[str, dict], *args, **kwargs) -> "Profiler":
        """Create from configuration."""
        if isinstance(cfg, str):
            with open(cfg) as f:
                cfg = json.load(f)
        api = "http://{}:{}/api".format(
            cfg.get("http", "localhost"), cfg.get("http_port", 8000))
        data = cfg.get("data_dir", "data")
        return cls(
            *args, api=api, base_path=data, server=MQTTServer.from_config(cfg),
            **kwargs)

    def start(self) -> "Profiler":
        """Start profiling server."""
        print(self._BANNER)
        super().start()
        self.subscribe(self.control_topic("profile", "#"))
        return self

    def stop(self) -> "Profiler":
        """Stop profiling server."""
        super().stop()

        self.log.info(
            "Saving metadata for {} runtimes.".format(len(self._runtimes)))
        if len(self._runtimes) > 0:
            with open(os.path.join(self.base_path, "runtimes.json"), 'w') as f:
                json.dump(self._runtimes, f, indent=4)
        self.log.info(
            "Saving metadata for {} modules.".format(len(self._modules)))
        if len(self._modules) > 0:
            with open(os.path.join(self.base_path, "modules.json"), 'w') as f:
                json.dump(self._modules, f, indent=4)

        return self

    def decode(self, payload: bytes, mtype: str):
        """Decode message."""
        match mtype:
            case "benchmarking":
                data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 3)
                return {
                    "utime": data[:, 0],
                    "stime": data[:, 1],
                    "maxrss": data[:, 2]
                }
            case "opcodes":
                data = np.frombuffer(payload, dtype=np.uint64)
                return {"opcodes": data}
            case "instrumented":
                data = np.frombuffer(payload, dtype=np.uint32)
                return {"counts": data}
            case "deployed":
                data = np.frombuffer(payload, dtype=np.uint32).reshape(-1, 8)
                start = (
                    payload[:, 0].astype(np.uint64)
                    | (payload[:, 1].astype(np.uint64) << np.uint64(32)))
                return {
                    "start": start,
                    "wall": data[:, 2],
                    "utime": data[:, 3],
                    "stime": data[:, 4],
                    "maxrss": data[:, 5],
                    "ch_in": data[:, 6],
                    "ch_out": data[:, 7]
                }
            case _:
                raise ProfilerException("Invalid type: {}".format(mtype))

    def metadata(self, rtid, mid):
        """Get runtime/module metadata."""
        if rtid not in self._runtimes:
            self._runtimes[rtid] = self.get_runtime(rtid)
        if mid not in self._modules:
            self._modules[mid] = self.get_module(mid)
        return {
            "runtime": self._runtimes[rtid].get("name", ""),
            "module": self._modules[mid].get("name", ""),
            "filename": self._modules[mid].get("file", "")
        }

    def __on_message(self, msg) -> None:
        try:
            mtype, rtid, mid = msg.topic.replace(
                self.control_topic("profile") + "/", "").split('/')
        except ValueError:
            raise ProfilerException("Invalid topic: {}".format(msg.topic))

        decoded = self.decode(msg.payload, mtype)
        meta = self.metadata(rtid, mid)

        path = os.path.join(
            self.base_path, rtid, "{}.{}.npz".format(mid, mtype))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez(path, **meta, **decoded)
        self.log.info("Saved profiling data: {}".format(path))

    def on_message(self, client, userdata, msg):
        """Handle message."""
        self.log.debug("Received message on topic: {}".format(msg.topic))
        try:
            self.__on_message(msg)
        except ProfilerException as e:
            self.log.error(e.msg)
        except Exception as e:
            self.log.critical("Uncaught exception: {}".format(e))
            self.log.critical("\n".join(traceback.format_exception(e)))


if __name__ == '__main__':

    p = argparse.ArgumentParser("Balloon: Silverline profile collector.")
    p.add_argument(
        "-l", "--log_dir", default="log", help="Directory for log files.")
    p.add_argument(
        "-p", "--data_dir", default="data",
        help="Base directory for saving data.")
    p.add_argument(
        "-c", "--config", default="config.json", help="Configuration file.")
    args = p.parse_args()

    # log_dir = os.path.join(args.log_dir, "profile/")
    configure_log(log=None, level=0)

    path = os.path.join(args.data_dir, time.strftime("%Y-%m-%d.%H:%M:%S"))
    profiler = Profiler.from_config(
        args.config, name="profiler", base_path=path
    ).start().run_until_stop()
