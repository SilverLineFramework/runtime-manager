"""Profiling server."""

import logging
import os
import argparse
import json
import traceback
import time
import threading

import numpy as np

from beartype import beartype
from beartype.typing import Optional, Union

from libsilverline import (
    SilverlineClient, MQTTServer, configure_log, dict_or_load)


class ProfilerException(Exception):
    """Base class for profiling-related exceptions."""

    def __init__(self, msg):
        self.msg = msg


def _tolist(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    else:
        return x


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
        self.log.info("Saving to directory: {}".format(self.base_path))
        self._runtimes: dict = {}

    @classmethod
    def from_config(
            cls, path_or_cfg: Union[str, dict], **kwargs) -> "Profiler":
        """Create from configuration."""
        cfg = dict_or_load(path_or_cfg)
        api = "http://{}:{}/api".format(
            cfg.get("http", "localhost"), cfg.get("http_port", 8000))
        return cls(api=api, server=MQTTServer.from_config(cfg), **kwargs)

    def start(self) -> "Profiler":
        """Start profiling server."""
        print(self._BANNER)
        super().start()
        self.subscribe(self.control_topic("profile", "#"))

        def _save():
            self.save_metadata()
            self.timer = threading.Timer(30.0, _save)
            self.timer.start()

        _save()
        return self

    def stop(self) -> "Profiler":
        """Stop profiling server."""
        super().stop()
        self.save_metadata()
        self.timer.cancel()
        return self

    def save_metadata(self):
        """Save metadata."""
        if len(self._runtimes) > 0:
            self.log.info(
                "Saving metadata for {} runtimes.".format(len(self._runtimes)))
            with open(os.path.join(self.base_path, "runtimes.json"), 'w') as f:
                json.dump(self._runtimes, f, indent=4)

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
                    data[:, 0].astype(np.uint64)
                    | (data[:, 1].astype(np.uint64) << np.uint64(32)))
                return {
                    "start": start,
                    "wall": data[:, 2],
                    "cpu_time": data[:, 3],
                    "memory": data[:, 4],
                    "ch_mqtt": data[:, 5],
                    "ch_local": data[:, 6],
                    "ch_out": data[:, 7]
                }
            case "interference":
                return json.loads(payload)
            case "raw32":
                data = np.frombuffer(payload, dtype=np.uint32)
                return {"data": data}
            case "raw64":
                data = np.frombuffer(payload, dtype=np.uint64)
                return {"data": data}
            case _:
                raise ProfilerException("Invalid type: {}".format(mtype))

    def __on_message(self, msg) -> None:
        try:
            mtype, rtid, mid = msg.topic.replace(
                self.control_topic("profile") + "/", "").split('/')
        except ValueError:
            raise ProfilerException("Invalid topic: {}".format(msg.topic))

        decoded = self.decode(msg.payload, mtype)

        if rtid not in self._runtimes:
            meta = self.get_runtime(rtid)
            del meta["children"]
            del meta["queued"]
            self._runtimes[rtid] = meta

        module = self.get_module(mid)
        path = os.path.join(
            self.base_path, self._runtimes[rtid].get("name", "unknown"),
            "{}.{}.{}.json".format(module.get("name", "unknown"), mid, mtype))
        os.makedirs(os.path.dirname(path), exist_ok=True)

        out = {k: _tolist(v) for k, v in decoded.items()}
        out["module"] = module
        with open(path, 'w') as f:
            json.dump(out, f)
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
        "-l", "--log", default=None, help="Directory for log files.")
    p.add_argument(
        "-p", "--data", default="data", help="Base directory for saving data.")
    p.add_argument(
        "-c", "--cfg", help="Config file.",
        default=os.environ.get('SL_CONFIG', 'config.json'))
    p.add_argument("-v", "--verbose", help="Logging level", default=20)
    args = p.parse_args()

    if args.log is not None:
        args.log = os.path.join(args.log, "profile/")
    configure_log(log=args.log, level=args.verbose)

    path = os.path.join(args.data, time.strftime("%Y-%m-%d.%H-%M-%S"))
    Profiler.from_config(
        args.cfg, name="profiler", base_path=path
    ).start().run_until_stop()
