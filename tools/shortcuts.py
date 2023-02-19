"""Command shortcuts / aliases."""

from . import command


class Alias:
    """Command alias."""

    def __init__(self, desc, base, args):
        self._desc = desc
        self.base = base
        self.args = args

    def _parse(self, p):
        return self.base._parse(p)

    def _main(self, args):
        for k, v in self.args.items():
            setattr(args, k, v)
        self.base._main(args)


start = Alias(
    desc="Start runtimes on cluster.", base=command,
    args={
        "command": (
            "screen -S runtime -dm bash -c cd runtime-manager; "
            "./env/bin/python start.py --name {name} --cfg config.json "
            "--runtimes linux/min/wasmer"),
        "sudo": True
    })

shutdown = Alias(
    desc="Shut down nodes.", base=command,
    args={"command": "shutdown now", "sudo": True})

reboot = Alias(
    desc="Reboot nodes.", base=command,
    args={"command": "shutdown -r now", "sudo": True})

update = Alias(
    desc="Update runtimes.", base=command,
    args={"command": (
        "cd runtime-manager; git pull; git submodule update --recursive; "
        "./env/bin/pip install; ./libsilverline/; make -C runtimes"
    )}
)

kill = Alias(
    desc="Stop runtimes on cluster.", base=command,
    args={"command": "screen -S runtime -X quit", "sudo": True})

version = Alias(
    desc="Get runtime version via commit hash.", base=command,
    args={"command": "cd runtime-linux; git log -n 1 --pretty=format:\"%H\""})
