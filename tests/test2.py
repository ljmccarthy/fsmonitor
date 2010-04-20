import os, time
from test import *
from fsmonitor import *

w = test.add_dir_watch(tempdir)
touch(testpath("x"))
test.remove_watch(w)
remove(testpath("x"))

time.sleep(0.1)

assert test.event_happened(FSEvent.Create, "x")
assert not test.event_happened(FSEvent.Delete, "x")
