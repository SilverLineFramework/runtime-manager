from manager import Manager, MQTTServer, runtimes, configure_log


configure_log(log=None, verbose=5)

rt1 = runtimes.LinuxMinimalRuntime(name="minimal")
# rt2 = runtimes.RegistrationOnlyRuntime(name="debug")

mgr = Manager([rt1])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

# mgr.stop()
rt1.loop()
exit()
