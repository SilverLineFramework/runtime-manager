"""Miscellaneous utilities."""

import json

from beartype.typing import Union


def _dict_or_load(cfg: Union[str, dict]) -> dict:
    """Load json from file, or use settings dictionary if passed."""
    if isinstance(cfg, str):
        with open(cfg) as f:
            return json.load(f)
    else:
        return cfg
