import sys
from threading import Thread
from .common import *

# set to None when unloaded
module_loaded = True

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

    def add_dir_watch(self, path, flags=FSEvent.All, user=None):
        return self.__monitor.add_dir_watch(path, flags=flags, user=user)

    def add_file_watch(self, path, flags=FSEvent.All, user=None):
        return self.__monitor.add_file_watch(path, flags=flags, user=user)

    def remove_watch(self, watch):
        self.__monitor.remove_watch(watch)

    def remove_all_watches(self):
        self.__monitor.remove_all_watches()

    def run(self):
        while module_loaded and self.__running:
            for event in self.__monitor.read_events():
                self.__callback(event)

    def stop(self):
        if self.__monitor.watches:
            self.remove_all_watches()
            self.__running = False
            self.join()

__all__ = (
    "FSMonitor",
    "FSMonitorThread",
    "FSMonitorError",
    "FSMonitorOSError",
    "FSEvent",
)
