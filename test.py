from manager.manager import Manager, MQTTServer
from manager.runtime import TestRuntime
from manager.logging import configure_log


configure_log(log=None, verbose=5)


rt1 = TestRuntime()
rt2 = TestRuntime()
mgr = Manager({rt1.rtid: rt1, rt2.rtid: rt2}, server=MQTTServer(
    "localhost", 1883, "cli", "../mqtt_pwd.txt", False))
mgr.connect()
