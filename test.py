from manager import Manager, MQTTServer, configure_log
import interfaces


configure_log(log=None, verbose=5)

rt1 = interfaces.LinuxMinimal(name="min")
rt2 = interfaces.LinuxMinimalWAMR(name="wamr")
rt3 = interfaces.Benchmarking(name="bench")

mgr = Manager([rt1, rt2, rt3])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

input()

mgr.stop()
exit()
