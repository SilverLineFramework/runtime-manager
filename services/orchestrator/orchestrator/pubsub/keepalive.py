"""Keepalive handler."""

from .base import BaseHandler


class Keepalive(BaseHandler):
    """Keepalive message."""

    NAME = "ka"
    TOPIC = "proc/keepalive/#"

    def handle(self, msg):
        """Handle keepalive message."""
        # Currently unused
        return None
