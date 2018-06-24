import os, time
from utils import *
from fsmonitor import *

w = fsm_test.add_dir_watch(tempdir)
touch(get_testpath("x"))
fsm_test.remove_watch(w)
remove(get_testpath("x"))

time.sleep(0.1)

assert fsm_test.event_happened(FSEvent.Create, "x")
assert not fsm_test.event_happened(FSEvent.Delete, "x")
