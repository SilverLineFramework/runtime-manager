from manager import Manager
from common import configure_log, MQTTServer
import interfaces


configure_log(log="log/", level=0)

rt1 = interfaces.LinuxMinimal(name="min")
rt2 = interfaces.LinuxMinimalWAMR(name="wamr")
rt3 = interfaces.Benchmarking(name="bench")
rt4 = interfaces.OpcodeCount(name="intrp")

mgr = Manager([rt3])
mgr.start(MQTTServer.from_config("config.json"))

try:
    input()
except KeyboardInterrupt:
    print(" Exiting due to KeyboardInterrupt.\n")
    pass

mgr.stop()
exit()
