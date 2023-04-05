"""Module tracking."""

from beartype.typing import Union
from beartype import beartype

from manager.exceptions import ModuleException


@beartype
class ModuleLookup:
    """Module lookup by index and by UUID."""

    def __init__(self, max: int = 128):
        self.modules_idx: dict = {}
        self.modules_uuid: dict = {}
        self.max_nmodules = max

    def add(self, data: dict) -> None:
        """Add item."""
        self.modules_idx[data["index"]] = data
        self.modules_uuid[data["uuid"]] = data

    def get(self, x: Union[int, str]) -> dict:
        """Get item by index or UUID."""
        if isinstance(x, int):
            return self.modules_idx[x]
        else:
            return self.modules_uuid[x]

    def uuid(self, x: int) -> str:
        """Get UUID by index."""
        return self.modules_idx[x]["uuid"]

    def free_index(self) -> int:
        """Get first free index."""
        for i in range(self.max_nmodules):
            if i not in self.modules_idx:
                return i
        raise ModuleException(
            "Module limit (max={}) exceeded.".format(self.max_nmodules))

    def insert(self, data: dict) -> int:
        """Insert item."""
        idx = self.free_index()
        data["index"] = idx
        self.add(data)
        return idx

    def remove(self, x: Union[int, str]) -> None:
        """Remove item by index or UUID."""
        if isinstance(x, int):
            index = x
            module_id = self.modules_idx[index]["uuid"]
        else:
            module_id = x
            index = self.modules_uuid[x]["index"]
        del self.modules_idx[index]
        del self.modules_uuid[module_id]
