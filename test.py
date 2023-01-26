from manager.manager import Manager
from manager.types import MQTTServer
from manager.runtimes import TestRuntime
from manager.logging import configure_log


configure_log(log=None, verbose=5)


rt1 = TestRuntime(name="debug1")
rt2 = TestRuntime(name="debug2")
mgr = Manager([rt1, rt2])
mgr.start(MQTTServer("localhost", 1883, "cli", "../mqtt_pwd.txt", False))

import time
time.sleep(10)

mgr.stop()
exit()
