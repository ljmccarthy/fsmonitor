import sys, os, time, errno
from utils import *
from fsmonitor import *
from fsmonitor.compat import PY3
from fsmonitor.polling import FSMonitor as PollingFSMonitor

def test_3_errorno_enoent():
    fsm_test = FSMonitorTest()
    err_code = errno.ENOENT
    if PY3 and sys.platform == "win32":
        err_code = errno.ESRCH
    try:
        fsm_test.add_dir_watch("/this/path/does/not/exist")
    except FSMonitorError as e:
        assert e.errno == err_code
    else:
        assert False, "Expected exception"

def test_3_errorno_enoent_polling():
    fsm_test = FSMonitorTest(PollingFSMonitor)
    err_code = errno.ENOENT
    if PY3 and sys.platform == "win32":
        err_code = errno.ESRCH
    try:
        fsm_test.add_dir_watch("/this/path/does/not/exist")
    except FSMonitorError as e:
        assert e.errno == err_code
    else:
        assert False, "Expected exception"
