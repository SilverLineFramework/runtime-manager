"""Data traces."""

import os
import json
import numpy as np
from functools import partial

from beartype.typing import Optional, NamedTuple
from beartype import beartype
from jaxtyping import Float32, Integer

from utils import Index, Matrix, apply_recursive


@beartype
def load_result(path: str, runtimes: dict = {}) -> Optional[dict]:
    """Load single result."""
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("Invalid JSON: {}".format(path))
        return None

    t = np.array(data["utime"]) + np.array(data["stime"])
    m = np.array(data["maxrss"])
    m = m[t > 0]
    t = t[t > 0]

    # Remove containing folder (wasm/, aot/, ...) and extension (.wasm, .aot)
    benchmark_ext = data["module"]["file"].split(os.path.sep)[1:]
    module = os.path.splitext(os.path.join(*benchmark_ext))[0]

    if len(t) < 2:
        return None
    else:
        return {
            "device": runtimes.get(data["module"]["parent"])["name"],
            "module": module,
            "runtime": data["module"]["name"].split('.')[-1],
            "t_init": t[0],
            "t_mean": np.mean(t[1:]),
            "t_std": np.std(t[1:]),
            "m_init": m[0],
            "m_mean": np.mean(m[1:]),
            "m_std": np.std(m[1:]),
            "n": len(t) - 1
        }


class Dataset(NamedTuple):
    """Runtimes x Devices x Modules dataset."""

    KEYS = ["t_init", "t_mean", "t_std", "m_init", "m_mean", "m_std", "n"]
    INDICES = ["runtime", "devices", "modules"]

    t_init: Float32[np.ndarray, "i j k"]
    t_mean: Float32[np.ndarray, "i j k"]
    t_std: Float32[np.ndarray, "i j k"]
    m_init: Float32[np.ndarray, "i j k"]
    m_mean: Float32[np.ndarray, "i j k"]
    m_std: Float32[np.ndarray, "i j k"]
    n: Integer[np.ndarray, "i j k"]

    devices: Index
    runtimes: Index
    modules: Index

    @classmethod
    def from_sessions(cls, path: list[str]):
        """Create dataset from sessions."""
        runtimes = {}
        for p in path:
            with open(os.path.join(p, "runtimes.json")) as f:
                runtimes.update(json.load(f))

        data = []
        for p in path:
            data += apply_recursive(
                p, partial(load_result, runtimes=runtimes),
                exclude={"runtimes.json", "README.md"})

        devices = Index.from_objects(data, "device")
        runtimes = Index.from_objects(data, "runtime")
        modules = Index.from_objects(data, "module")

        shape = (len(runtimes), len(devices), len(modules))
        mat = {k: np.zeros(shape, dtype=np.float32) for k in Dataset.KEYS}
        for d in data:
            i = runtimes[d["runtime"]]
            j = devices[d["device"]]
            k = modules[d["module"]]
            for key in Dataset.KEYS:
                mat[key][i, j, k] = d[key]

        return cls(devices=devices, runtimes=runtimes, modules=modules, **mat)

    @classmethod
    def from_npz(cls, path: str):
        """Create dataset from saved npz."""
        npz = np.load(path)
        indices = {k: Index(list(npz[k])) for k in Dataset.INDICES}
        data = {k: npz[k] for k in Dataset.KEYS}
        return cls(**indices, **data)

    def save(self, path: str) -> None:
        """Save dataset to .npz file."""
        data = {k: getattr(self, k) for k in Dataset.KEYS}
        indices = {k: np.array(getattr(self, k).key) for k in Dataset.INDICES}
        np.savez(path, **indices, **data)

    def to_matrix(self) -> Matrix:
        """Convert to data matrix."""
        return Matrix(
            data=self.t_mean.reshape(-1, self.t_mean.shape[-1]),
            rows=self.runtimes @ self.devices,
            cols=self.modules)
