# Copyright (c) 2010 Luke McCarthy <luke@iogopro.co.uk>
#
# This is free software released under the MIT license.
# See COPYING file for details, or visit:
# http://www.opensource.org/licenses/mit-license.php
#
# The file is part of FSMonitor, a file-system monitoring library.
# https://github.com/shaurz/fsmonitor

import os, threading
import win32file, win32con, pywintypes
import ctypes
from .common import FSEvent, FSMonitorError

# set to None when unloaded
module_loaded = True

FILE_LIST_DIRECTORY = 0x0001
FILE_NOTIFY_CHANGE_LAST_ACCESS = 0x20
FILE_NOTIFY_CHANGE_CREATION = 0x40

action_map = {
    1 : FSEvent.Create,
    2 : FSEvent.Delete,
    3 : FSEvent.Modify,
    4 : FSEvent.MoveFrom,
    5 : FSEvent.MoveTo,
}

flags_map = {
    FSEvent.Access     : FILE_NOTIFY_CHANGE_LAST_ACCESS,
    FSEvent.Modify     : win32con.FILE_NOTIFY_CHANGE_LAST_WRITE | win32con.FILE_NOTIFY_CHANGE_SIZE,
    FSEvent.Attrib     : win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES | win32con.FILE_NOTIFY_CHANGE_SECURITY,
    FSEvent.Create     : FILE_NOTIFY_CHANGE_CREATION,
    FSEvent.Delete     : win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_DIR_NAME,
    FSEvent.DeleteSelf : 0,
    FSEvent.MoveFrom   : win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_DIR_NAME,
    FSEvent.MoveTo     : win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_DIR_NAME,
}

def convert_flags(flags):
    os_flags = 0
    flag = 1
    while flag < FSEvent.All + 1:
        if flags & flag:
            os_flags |= flags_map[flag]
        flag <<= 1
    return os_flags

def get_dir_handle(path):
    return win32file.CreateFile(
        path,
        FILE_LIST_DIRECTORY,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None,
        win32con.OPEN_EXISTING,
        win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_OVERLAPPED,
        None)

class FSMonitorWindowsError(WindowsError, FSMonitorError):
    pass

class FSMonitorWatch(object):
    def __init__(self, path, flags, user, recursive):
        self.path = path
        self.flags = flags
        self.user = user
        self.enabled = True
        self._recursive = recursive
        self._win32_flags = convert_flags(flags)
        self._key = None
        self._hDir = None
        self._hDir = get_dir_handle(path)
        self._overlapped = pywintypes.OVERLAPPED()
        self._buf = ctypes.create_string_buffer(1024)
        self._removed = False

    def __del__(self):
        if module_loaded:
            close_watch(self)

    def __repr__(self):
        return "<FSMonitorWatch %r>" % self.path

def close_watch(watch):
    if watch._hDir is not None:
        win32file.CancelIo(watch._hDir)
        win32file.CloseHandle(watch._hDir)
        watch._hDir = None

def read_changes(watch):
    win32file.ReadDirectoryChangesW(
        watch._hDir, watch._buf, watch._recursive, watch._win32_flags,
        watch._overlapped, None)

def process_events(watch, num):
    for action, name in win32file.FILE_NOTIFY_INFORMATION(watch._buf.raw, num):
        action = action_map.get(action)
        if action is not None and (action & watch.flags):
            yield FSEvent(watch, action, name)
    try:
        read_changes(watch)
    except pywintypes.error, e:
        if e.args[0] == 5:
            close_watch(watch)
            yield FSEvent(watch, FSEvent.DeleteSelf)
        else:
            raise FSMonitorWindowsError(*e.args)

class FSMonitor(object):
    def __init__(self):
        self.__key_to_watch = {}
        self.__last_key = 0
        self.__lock = threading.Lock()
        self.__cphandle = win32file.CreateIoCompletionPort(-1, None, 0, 0)

    def __del__(self):
        if module_loaded:
            self.close()

    def close(self):
        if self.__cphandle is not None:
            win32file.CloseHandle(self.__cphandle)
            self.__cphandle = None

    def add_dir_watch(self, path, flags=FSEvent.All, user=None, recursive=False):
        try:
            flags |= FSEvent.DeleteSelf
            watch = FSMonitorWatch(path, flags, user, recursive)
            with self.__lock:
                key = self.__last_key
                win32file.CreateIoCompletionPort(watch._hDir, self.__cphandle, key, 0)
                self.__last_key += 1
                read_changes(watch)
                watch._key = key
                self.__key_to_watch[key] = watch
            return watch
        except pywintypes.error, e:
            raise FSMonitorWindowsError(*e.args)

    def add_file_watch(self, path, flags=FSEvent.All, user=None):
        raise NotImplementedError()

    def __remove_watch(self, watch):
        if not watch._removed:
            try:
                watch._removed = True
                close_watch(watch)
                return True
            except pywintypes.error:
                pass
        return False

    def remove_watch(self, watch):
        with self.__lock:
            return self.__remove_watch(watch)

    def remove_all_watches(self):
        with self.__lock:
            for watch in self.__key_to_watch.itervalues():
                self.__remove_watch(watch)

    def enable_watch(self, watch, enable=True):
        watch.enabled = enable

    def disable_watch(self, watch):
        watch.enabled = False

    def read_events(self, timeout=None):
        timeout_ms = timeout * 1000 if timeout is not None else 0xFFFFFFFF
        try:
            events = []
            rc, num, key, _ = win32file.GetQueuedCompletionStatus(self.__cphandle, timeout_ms)
            if rc == 0:
                with self.__lock:
                    watch = self.__key_to_watch.get(key)
                    if watch is not None and watch.enabled and not watch._removed:
                        for evt in process_events(watch, num):
                            events.append(evt)
            elif rc == 5:
                with self.__lock:
                    watch = self.__key_to_watch.get(key)
                    if watch is not None and watch.enabled:
                        close_watch(watch)
                        del self.__key_to_watch[key]
                        events.append(FSEvent(watch, FSEvent.DeleteSelf))
            return events
        except pywintypes.error, e:
            raise FSMonitorWindowsError(*e.args)

    @property
    def watches(self):
        with self.__lock:
            return self.__key_to_watch.values()
