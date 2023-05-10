"""Runtime registration."""

from beartype.typing import Union

from django.conf import settings
from django.forms.models import model_to_dict

from orchestrator.models import Runtime, Module, Manager
from libsilverline import State

from orchestrator import messages
from .base import BaseHandler


class Registration(BaseHandler):
    """Runtime registration."""

    NAME = "reg"
    TOPIC = "proc/reg/#"

    def create_runtime(self, msg):
        """Create or resurrect runtime."""
        # Runtime UUID already exists -> resurrect
        try:
            runtime = self._set_status(
                msg, State.alive, action="Runtime resurrected", model=Runtime)
            modules = list(
                Module.objects.filter(parent=runtime, status=State.killed))
            self.log.warn("Respawning {} modules.".format(len(modules)))

            # Respawn dead modules
            for mod in modules:
                mod.status = State.alive
                mod.save()

            return [
                messages.Response(
                    msg.topic, msg.get('object_id'), model_to_dict(runtime))
            ] + [
                messages.Request(
                    "/".join([settings.REALM, "proc/control", runtime.uuid]),
                    "create", {"type": "module", **model_to_dict(mod)})
                for mod in modules]

        # Doesn't exist -> create new
        except messages.UUIDNotFound:
            runtime = self._object_from_dict(Runtime, msg.get('data'))
            try:
                mgr_uuid = msg.get('data', 'parent')
                runtime.parent = Manager.objects.get(uuid=mgr_uuid)
            except (Manager.DoesNotExist, messages.MissingField):
                pass
            runtime.save()
            self.log.info("Created runtime: {}".format(runtime.uuid))

            return messages.Response(
                msg.topic, msg.get('object_id'), model_to_dict(runtime))

    def delete_runtime(self, rt: Union[str, messages.Message]):
        """Delete runtime."""
        runtime = self._set_status(
            rt, State.dead, action="Runtime exited", model=Runtime)

        # Also mark all related modules as dead, but with respawn enabled
        killed = Module.objects.filter(parent=runtime, status=State.alive)
        for mod in killed:
            mod.status = State.killed
            mod.save()
        if len(killed) > 0:
            self.log.warn(
                "Runtime exited, killing {} modules; may be "
                "resurrected.".format(len(killed)))

        unqueued = Module.objects.filter(parent=runtime, status=State.queued)
        for mod in unqueued:
            mod.status = State.dead
            mod.save()
        if len(unqueued) > 0:
            self.log.warn(
                "Runtime exited with {} modules queued.".format(len(unqueued)))

    def create_manager(self, msg):
        """Create runtime manager."""
        manager = self._object_from_dict(Manager, msg.get('data'))
        manager.save()
        self.log.info("Registered runtime manager: {}".format(manager.uuid))
        return messages.Response(
            msg.topic, msg.get('object_id'), model_to_dict(manager))

    def delete_manager(self, msg):
        """Delete runtime manager."""
        manager = self._set_status(
            msg, State.dead, action="Manager exited", model=Manager)

        # Also kill the runtimes
        killed = Runtime.objects.filter(parent=manager, status=State.alive)
        for rt in killed:
            self.delete_runtime(rt.uuid)
        if len(killed) > 0:
            self.log.warn(
                "Manager exited, killing {} runtimes".format(len(killed)))

    def handle(self, msg):
        """Handle registration message."""
        if msg.get('type') == 'arts_resp':
            return None

        self.log.debug(msg.payload)
        match (msg.get('action'), msg.get('data', 'type')):
            case ("create", "runtime"):
                return self.create_runtime(msg)
            case ("delete", "runtime"):
                return self.delete_runtime(msg)
            case ("create", "manager"):
                return self.create_manager(msg)
            case ("delete", "manager"):
                return self.delete_manager(msg)
            case unknown:
                raise messages.InvalidArgument("action/type", unknown)
