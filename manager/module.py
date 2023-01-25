"""SilverLine Modules."""

import json

from beartype.typing import Optional, NamedTuple


class InvalidModuleSpec(ValueError):
    """Missing or invalid module specifications."""

    pass


class Module(NamedTuple):
    """Module-related metadata.

    uuid: Module ID.
    name: Module short name.
    index: Module index (assigned by the runtime manager).
    path: Binary file name / path.
    func: Function call entry point (if applicable).
    args: Argv to pass to main (if applicable).
    env: Environment variables; format is "{name}={value}".
    dirs: WASI allowed directories.
    resources: Resource allocations and scheduling.
    """

    uuid: str
    name: str
    path: str
    func: Optional[str]
    args: list[str]
    env: list[str]
    dirs: list[str]
    resources: Optional[dict]

    @classmethod
    def from_dict(cls, data: dict):
        """Parse dictionary."""
        try:
            return cls(
                uuid=data['uuid'],
                path=data['path'],
                func=data.get('func'),
                args=data.get('args', []),
                env=data.get('env', []),
                dirs=data.get('dirs', []),
                resources=data.get('resources', {}))
        except KeyError as e:
            raise InvalidModuleSpec(
                "Missing key: {} in {}".format(str(e), str(data)))

    def to_json(self, index: int):
        """Encode as json to send to module."""
        keys = [
            'uuid', 'name', 'path', 'func', 'args', 'env', 'dirs', 'resources']
        res = {k: getattr(self, k) for k in keys}
        res['index'] = index
        return json.dumps(res)
