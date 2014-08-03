# Copyright (c) 2012 Luke McCarthy <luke@iogopro.co.uk>
#
# This is free software released under the MIT license.
# See COPYING file for details, or visit:
# http://www.opensource.org/licenses/mit-license.php
#
# The file is part of FSMonitor, a file-system monitoring library.
# https://github.com/shaurz/fsmonitor

import sys, os, time, threading, errno
from .common import FSEvent, FSMonitorError


def get_dir_contents(path):
    return [(filename, os.stat(os.path.join(path, filename)))
            for filename in os.listdir(path)]


class FSMonitorDirWatch(object):

    def __init__(self, path, flags, user):
        self.path = path
        self.flags = flags
        self.user = user
        self.enabled = True
        self._timestamp = time.time()
        try:
            self._contents = get_dir_contents(path)
            self._deleted = False
        except OSError, e:
            self._contents = []
            self._deleted = (e.errno == errno.ENOENT)

    def __repr__(self):
        return "<FSMonitorDirWatch %r>" % self.path

    @classmethod
    def new_state(cls, path):
        return [(filename, os.stat(os.path.join(path, filename)))
                for filename in os.listdir(path)]

    def getstate(self):
        return self._contents

    def delstate(self):
        self._contents = []
        self._deleted = True

    def setstate(self, state):
        self._contents = state
        self._deleted = False

    state = property(getstate, setstate, delstate)


class FSMonitorFileWatch(object):

    def __init__(self, path, flags, user):
        self.path = path
        self.flags = flags
        self.user = user
        self.enabled = True
        self._timestamp = time.time()
        try:
            self._stat = os.stat(path)
            self._deleted = False
        except OSError, e:
            self._stat = None
            self._deleted = (e.errno == errno.ENOENT)

    def __repr__(self):
        return "<FSMonitorFileWatch %r>" % self.path

    @classmethod
    def new_state(cls, path):
        return os.stat(path)

    def getstate(self):
        return self._stat

    def delstate(self):
        self._stat = None
        self._deleted = True

    def setstate(self, state):
        self._stat = state
        self._deleted = False

    state = property(getstate, setstate, delstate)


class FSMonitorWatch(object):
    def __init__(self, path, flags, user):
        self.path = path
        self.flags = flags
        self.user = user
        self.enabled = True
        self._timestamp = time.time()
        try:
            self._contents = get_dir_contents(path)
            self._deleted = False
        except OSError, e:
            self._contents = []
            self._deleted = (e.errno == errno.ENOENT)

    def __repr__(self):
        return "<FSMonitorWatch %r>" % self.path


def _compare_contents(watch, new_contents, events_out, before):
    name_to_new_stat = dict(new_contents)

    for name, old_stat in watch._contents:
        new_stat = name_to_new_stat.get(name)
        if new_stat:
            _compare_stat(watch, new_stat, events_out, before, old_stat, name)
        else:
            events_out.append(FSEvent(watch, FSEvent.Delete, name))

    old_names = frozenset(x[0] for x in watch._contents)
    for name, new_stat in new_contents:
        if name not in old_names:
            events_out.append(FSEvent(watch, FSEvent.Create, name))


def _compare_stat(watch, new_stat, events_out, before, old_stat, filename):
    if new_stat.st_atime != old_stat.st_atime and new_stat.st_atime < before:
        events_out.append(FSEvent(watch, FSEvent.Access, filename))

    if new_stat.st_mtime != old_stat.st_mtime:
        events_out.append(FSEvent(watch, FSEvent.Modify, filename))


def round_fs_resolution(t):
    if sys.platform == "win32":
        return t // 2 * 2
    else:
        return t // 1


class FSMonitor(object):

    def __init__(self):
        self.__lock = threading.Lock()
        self.__dir_watches = set()
        self.__file_watches = set()
        self.polling_interval = 0.5

    @property
    def watches(self):
        with self.__lock:
            return list(self.__dir_watches) + list(self.__file_watches)

    def add_dir_watch(self, path, flags=FSEvent.All, user=None):
        watch = FSMonitorDirWatch(path, flags, user)
        with self.__lock:
            self.__dir_watches.add(watch)
        return watch

    def add_file_watch(self, path, flags=FSEvent.All, user=None):
        watch = FSMonitorFileWatch(path, flags, user)
        with self.__lock:
            self.__file_watches.add(watch)
        return watch

    def remove_watch(self, watch):
        with self.__lock:
            if watch in self.__dir_watches:
                self.__dir_watches.discard(watch)
            elif watch in self.__file_watches:
                self.__file_watches.discard(watch)

    def remove_all_watches(self):
        with self.__lock:
            self.__dir_watches.clear()
            self.__file_watches.clear()

    def enable_watch(self, watch, enable=True):
        watch.enabled = enable

    def disable_watch(self, watch):
        watch.enabled = False

    def read_events(self, timeout=None):
        now = start_time = time.time()
        watches = self.watches
        watches.sort(key=lambda watch: abs(now - watch._timestamp), reverse=True)

        events = []
        for watch in watches:
            now = time.time()
            if watch._timestamp < now:
                tdiff = now - watch._timestamp
                if tdiff < self.polling_interval:
                    time.sleep(self.polling_interval - tdiff)
            watch._timestamp = now

            if not watch.enabled:
                continue

            before = round_fs_resolution(time.time())
            try:
                new_state = watch.new_state(watch.path)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    if not watch._deleted:
                        del watch.state
                        events.append(FSEvent(watch, FSEvent.DeleteSelf))
            else:
                if isinstance(watch, FSMonitorDirWatch):
                    _compare_contents(watch, new_state, events, before)
                elif isinstance(watch, FSMonitorFileWatch):
                    _compare_stat(watch, new_state, events, before,
                                  watch.state, watch.path)
                watch.state = new_state

        return events
