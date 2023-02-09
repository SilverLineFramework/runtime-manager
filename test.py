from manager import Manager, MQTTServer, configure_log
import interfaces


configure_log(log=None, verbose=5)

# rt1 = LinuxMinimalRuntime(name="min1")
# rt2 = LinuxMinimalRuntime(name="min2")
rt = interfaces.LinuxMinimalWAMR(name="wamr")

mgr = Manager([rt])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

input()
exit()
