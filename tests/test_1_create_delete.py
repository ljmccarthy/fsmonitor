import os, time
from utils import *
from fsmonitor import *
from fsmonitor.polling import FSMonitor as PollingFSMonitor

def test_1_create_delete():
    fsm_test = FSMonitorTest()
    w = fsm_test.add_dir_watch(tempdir)
    touch(get_testpath("x"))
    remove(get_testpath("x"))

    time.sleep(0.1)

    assert fsm_test.event_happened(FSEvent.Create, "x")
    assert fsm_test.event_happened(FSEvent.Delete, "x")

def test_1_create_delete_polling():
    fsm_test = FSMonitorTest(PollingFSMonitor)
    w = fsm_test.add_dir_watch(tempdir)
    touch(get_testpath("x"))
    remove(get_testpath("x"))

    time.sleep(0.1)

    assert fsm_test.event_happened(FSEvent.Create, "x")
    assert fsm_test.event_happened(FSEvent.Delete, "x")
