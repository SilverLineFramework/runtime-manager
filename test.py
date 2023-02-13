from manager import Manager
from common import configure_log, MQTTServer
import interfaces


configure_log(log=None, level=0)

rt1 = interfaces.LinuxMinimal(name="min")
rt2 = interfaces.LinuxMinimalWAMR(name="wamr")
rt3 = interfaces.Benchmarking(name="bench")
rt4 = interfaces.OpcodeCount(name="opcodes")

mgr = Manager([rt4])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

input()

mgr.stop()
exit()
