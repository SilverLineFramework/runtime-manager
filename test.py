from manager import Manager
from common import configure_log, MQTTServer
import interfaces


configure_log(log="log/", level=0)

rt1 = interfaces.LinuxMinimal(name="min")
rt2 = interfaces.LinuxMinimalWAMR(name="wamr")
rt3 = interfaces.Benchmarking(name="bench")
rt4 = interfaces.OpcodeCount(name="intrp")

mgr = Manager([rt1, rt2, rt3, rt4])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

try:
    input()
except KeyboardInterrupt:
    print(" Exiting due to KeyboardInterrupt.\n")
    pass

mgr.stop()
exit()
