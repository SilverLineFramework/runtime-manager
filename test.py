from manager import Manager, MQTTServer, configure_log
from interfaces import LinuxMinimalRuntime


configure_log(log=None, verbose=5)

rt1 = LinuxMinimalRuntime(name="min1")
rt2 = LinuxMinimalRuntime(name="min2")

mgr = Manager([rt1, rt2])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

input()
exit()
