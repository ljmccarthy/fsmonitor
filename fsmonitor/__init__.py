import sys
from threading import Thread
from .common import *

if sys.platform == "linux2":
    from .linux import FSMonitor
elif sys.platform == "win32":
    from .win32 import FSMonitor
else:
    raise ImportError("Unsupported platform: %s" % sys.platform)

class FSMonitorThread(Thread):
    def __init__(self, callback, *args, **kwargs):
        Thread.__init__(self)
        self.__callback = callback
        self.__running = True
        self.__monitor = FSMonitor(*args, **kwargs)
        self.daemon = True
        self.start()

    def add_watch(self, path, userobj=None):
        return self.__monitor.add_watch(path, userobj)

    def remove_watch(self, watch):
        self.__monitor.remove_watch(watch)

    def run(self):
        while self.__running:
            for event in self.__monitor.read_events():
                self.__callback(event)

    def stop(self):
        self.__running = False
        self.join()

__all__ = (
    "FSMonitor",
    "FSMonitorThread",
    "FSMonitorError",
    "FSMonitorOSError",
    "FSEVT_ACCESS",
    "FSEVT_MODIFY",
    "FSEVT_ATTRIB",
    "FSEVT_CREATE",
    "FSEVT_DELETE",
    "FSEVT_DELETE_SELF",
    "FSEVT_MOVE_TO",
    "FSEVT_MOVE_FROM",
)
