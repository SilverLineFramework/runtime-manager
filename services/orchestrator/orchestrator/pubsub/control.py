"""Handler for module control messages."""

from django.forms.models import model_to_dict
from django.conf import settings

from orchestrator.models import Runtime, Module
from libsilverline import State

from orchestrator import messages
from .base import BaseHandler


class Control(BaseHandler):
    """Runtime control messages."""

    NAME = "ctrl"
    TOPIC = "proc/control/#"

    # if parent is not given will default to schedule on this runtime
    __DFT_RUNTIME_NAME = "pyruntime"

    def create_module_ack(self, msg):
        """Handle ACK sent after scheduling module.

        TODO: Should update a flag if ok and reschedule otherwise; currently
        not implemented in the runtime.
        """
        return None

    def __get_runtime_or_schedule(self, msg):
        """Get parent runtime, or allocate target runtime."""
        try:
            return self._get_object(msg.get('data', 'parent'), model=Runtime)
        except messages.MissingField:
            return self._get_object(Control.__DFT_RUNTIME_NAME, model=Runtime)

    def create_module(self, msg):
        """Handle create message."""
        try:
            module = self._get_object(msg.get('data', 'uuid'), model=Module)
            if module.status == State.alive:
                # module is running, will error out with a duplicate UUID
                raise messages.DuplicateUUID(msg, obj_type='module')
            else:
                module.delete()
        # No conflict or UUID not specified
        except (messages.UUIDNotFound, messages.MissingField):
            pass

        module = self._object_from_dict(Module, msg.get('data'))
        parent = self.__get_runtime_or_schedule(msg)
        module.parent = parent

        active = Module.objects.filter(parent=parent, status=State.alive)
        if active.count() >= parent.max_nmodules:
            module.status = State.queued
            module.save()
            self.log.info("Module queued: {}".format(module.uuid))
        else:
            module.status = State.alive
            module.save()
            self.log.info("Created module: {}".format(module.uuid))
            return messages.Request(
                "/".join([settings.REALM, "proc/control", module.parent.uuid]),
                "create", {"type": "module", **model_to_dict(module)})

    def create_module_batch(self, msg):
        """Create modules in batch."""
        modules = [
            self._object_from_dict(Module, m)
            for m in msg.get('data', 'modules')]

        parent = self._get_object(msg.get('data', 'parent'), model=Runtime)
        active = Module.objects.filter(parent=parent, status=State.alive)

        start = parent.max_nmodules - active.count()
        for module in modules[:start]:
            module.status = State.alive
        for module in modules[start:]:
            module.status = State.queued
        for module in modules:
            module.parent = parent
            module.save()
        self.log.info("Batch-created {} modules -> {} ({} queued).".format(
            len(modules), parent.uuid, len(modules[start:])))

        return [
            messages.Request(
                "/".join([settings.REALM, "proc/control", module.parent.uuid]),
                "create", {"type": "module", **model_to_dict(module)})
            for module in modules[:start]]

    def delete_module(self, msg):
        """Handle delete message."""
        module = self._set_status(
            msg, State.exiting, action="Deleting module", model=Module)
        return messages.Request(
            "/".join([settings.REALM, "proc/control", module.parent.uuid]),
            "delete", {"type": "module", "uuid": module.uuid})

    def exited_module(self, msg):
        """Remove module from database."""
        module = self._set_status(
            msg, State.dead, action="Module exited", model=Module)

        q = Module.objects.filter(parent=module.parent, status=State.queued)
        if q.count() > 0:
            head = q.order_by('index')[0]
            head.status = State.alive
            head.save()
            self.log.info("Queued module now executing: {}".format(head.uuid))
            return messages.Request(
                "/".join([settings.REALM, "proc/control", head.parent.uuid]),
                "create", {"type": "module", **model_to_dict(head)})

    def handle(self, msg):
        """Handle per-module control message."""
        self.log.debug(msg.payload)
        match (msg.get('action'), msg.get('type')):
            case ('create', 'resp'):
                return self.create_module_ack(msg)
            case ('create', 'req'):
                return self.create_module(msg)
            case ('create_batch', 'req'):
                return self.create_module_batch(msg)
            case ('delete', 'req'):
                return self.delete_module(msg)
            case ('exited', 'req'):
                return self.exited_module(msg)
            case unknown:
                raise messages.InvalidArgument('action/type', unknown)
