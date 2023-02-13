"""Profiling server."""

import uuid
import logging
import os
import argparse

import numpy as np

from beartype import beartype
from beartype.typing import Optional

from common import MQTTClient, MQTTServer, configure_log


@beartype
class Profile(MQTTClient):
    """Profiling server."""

    _BANNER = r"""
     ___       _ _ 
    | _ ) __ _| | |___  ___ _ _
    | _ \/ _` | | / _ \/ _ \ ' \
    |___/\__,_|_|_\___/\___/_||_|
     Silverline: Data Collection
    """

    def __init__(
        self, name: str = "profile", profiler_id: Optional[str] = None,
        realm: str = "realm", base_path: str = "data"
    ) -> None:
        self.log = logging.getLogger("profile")
        self.name = name
        self.uuid = str(uuid.uuid4()) if profiler_id is None else profiler_id
        self.realm = realm
        self.base_topic = "{}/proc/profile/".format(self.realm)
        self.base_path = base_path
        super().__init__(name="{}:{}".format(self.name, self.uuid))

    def start(self, server: Optional[MQTTServer] = None) -> None:
        """Start profiling server."""
        print(self._BANNER)
        self.connect(server)

        self.subscribe("{}#".format(self.base_topic))
        self.message_callback_add(
            "{}control".format(self.base_topic), self.on_control_message)

    def stop(self):
        """Stop profiling server."""
        self.loop_stop()
        self.disconnect()

    def on_control_message(self, client, userdata, msg):
        """Control messages."""
        pass

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
                return None

    def on_message(self, client, userdata, msg):
        """Handle message."""
        self.log.debug("Received message on topic: {}".format(msg.topic))
        try:
            mtype, rtid, mid = msg.topic.replace(
                self.base_topic, "").split('/')
        except ValueError:
            self.log.error("Invalid topic: {}".format(msg.topic))

        decoded = self.decode(msg.payload, mtype)
        if decoded is None:
            self.log.error("Invalid message type: {}. Topic was: {}".format(
                mtype, msg.topic))
        else:
            path = os.path.join(
                self.base_path, rtid, "{}.{}.npz".format(mid, mtype))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            np.savez(path, **decoded)
            self.log.info("Saved profiling data: {}".format(path))


if __name__ == '__main__':

    p = argparse.ArgumentParser("Balloon: Silverline profile collector.")
    p.add_argument(
        "-l", "--log_dir", default="log", help="Directory for log files.")
    p.add_argument(
        "-c", "--config", default="config.json", help="Configuration file.")
    args = p.parse_args()

    # log_dir = os.path.join(args.log_dir, "profile/")
    # os.makedirs(log_dir, exist_ok=True)
    configure_log(log=None, level=0)

    profiler = Profile(name="profiler", realm="realm", base_path="data")
    # profiler.start(MQTTServer.from_json(args.config))
    profiler.start(None)

    input()
