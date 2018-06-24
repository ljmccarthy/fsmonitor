import os, time, errno
from utils import *
from fsmonitor import *

def test_3_errorno_enoent():
    try:
        fsm_test.add_dir_watch("/this/path/does/not/exist")
    except FSMonitorError as e:
        assert e.errno == errno.ENOENT
    else:
        assert False, "Expected exception"
