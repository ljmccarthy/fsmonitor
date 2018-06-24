import sys, os, shutil, threading
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from fsmonitor import FSMonitorThread

class FSMonitorTest(object):
    def __init__(self):
        self.monitor = FSMonitorThread(self.__callback)
        self._lock = threading.Lock()
        self._events = []

    def __callback(self, evt):
        with self._lock:
            self._events.append(evt)

    @property
    def events(self):
        with self._lock:
            return list(self._events)

    def add_dir_watch(self, *args, **kwargs):
        return self.monitor.add_dir_watch(*args, **kwargs)

    def add_file_watch(self, *args, **kwargs):
        return self.monitor.add_file_watch(*args, **kwargs)

    def remove_watch(self, *args, **kwargs):
        self.monitor.remove_watch(*args, **kwargs)

    def event_happened(self, action=None, name=None, path=None):
        for evt in self.events:
            if (name is None or evt.name == name) \
            and (action is None or evt.action == action) \
            and (path is None or evt.path == path):
                return True
        return False


def mkdir(path):
    try:
        os.mkdir(path)
    except OSError:
        pass

def remove(path):
    try:
        os.remove(path)
    except OSError:
        pass

def touch(path):
    with open(path, "ab"):
        pass

def truncate(path):
    with open(path, "wb"):
        pass

if sys.platform == "win32":
    tempdir = os.getenv("TEMP", "C:\\Temp")
    mkdir(tempdir)
else:
    tempdir = "/tmp"

def get_testpath(*args):
    return os.path.join(tempdir, *args)

tempdir = os.path.join(tempdir, "fsmonitor-test")
shutil.rmtree(tempdir, ignore_errors=True)
mkdir(tempdir)

__all__ = (
    "FSMonitorTest",
    "mkdir",
    "remove",
    "touch",
    "truncate",
    "tempdir",
    "get_testpath"
)
