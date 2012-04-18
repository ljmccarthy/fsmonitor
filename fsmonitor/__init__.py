# Copyright (c) 2010, 2012 Luke McCarthy <luke@iogopro.co.uk>
#
# This is free software released under the MIT license.
# See COPYING file for details, or visit:
# http://www.opensource.org/licenses/mit-license.php
#
# The file is part of FSMonitor, a file-system monitoring library.
# https://github.com/shaurz/fsmonitor

import sys
import threading
from .common import FSEvent, FSMonitorError, FSMonitorOSError

# set to None when unloaded
module_loaded = True

if sys.platform == "linux2":
    from .linux import FSMonitor
elif sys.platform == "win32":
    from .win32 import FSMonitor
else:
    from .polling import FSMonitor

class FSMonitorThread(threading.Thread):
    def __init__(self, callback=None):
        threading.Thread.__init__(self)
        self.monitor = FSMonitor()
        self.callback = callback
        self._running = True
        self._events = []
        self._events_lock = threading.Lock()
        self.daemon = True
        self.start()

    def add_dir_watch(self, path, flags=FSEvent.All, user=None):
        return self.monitor.add_dir_watch(path, flags=flags, user=user)

    def add_file_watch(self, path, flags=FSEvent.All, user=None):
        return self.monitor.add_file_watch(path, flags=flags, user=user)

    def remove_watch(self, watch):
        self.monitor.remove_watch(watch)

    def remove_all_watches(self):
        self.monitor.remove_all_watches()
        with self._events_lock:
            self._events = []

    def run(self):
        while module_loaded and self._running:
            try:
                events = self.monitor.read_events()
                if self.callback:
                    for event in events:
                        self.callback(event)
                else:
                    with self._events_lock:
                        self._events.extend(events)
            except Exception:
                pass

    def stop(self):
        if self.monitor.watches:
            self.remove_all_watches()
            self._running = False

    def read_events(self):
        with self._events_lock:
            events = self._events
            self._events = []
            return events

__all__ = (
    "FSMonitor",
    "FSMonitorThread",
    "FSMonitorError",
    "FSMonitorOSError",
    "FSEvent",
)
