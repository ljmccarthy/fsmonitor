import os, threading
import win32file, win32con, pywintypes
import ctypes
from .common import *

# set to None when unloaded
module_loaded = True

action_map = {
    1 : FSEVT_CREATE,
    2 : FSEVT_DELETE,
    3 : FSEVT_MODIFY,
    4 : FSEVT_MOVE_FROM,
    5 : FSEVT_MOVE_TO,
}

FILE_LIST_DIRECTORY = 0x0001
FILE_NOTIFY_CHANGE_LAST_ACCESS = 0x20
FILE_NOTIFY_CHANGE_CREATION = 0x40
INVALID_HANDLE_VALUE = -1

def GetDirHandle(path):
    return win32file.CreateFile(
        path,
        FILE_LIST_DIRECTORY,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None,
        win32con.OPEN_EXISTING,
        win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_OVERLAPPED,
        None)

def ReadDirChanges(hDir, buf, recursive, overlapped):
    return win32file.ReadDirectoryChangesW(
        hDir, buf, recursive,
        win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
        win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
        win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
        win32con.FILE_NOTIFY_CHANGE_SIZE |
        win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
        FILE_NOTIFY_CHANGE_LAST_ACCESS |
        FILE_NOTIFY_CHANGE_CREATION |
        win32con.FILE_NOTIFY_CHANGE_SECURITY,
        overlapped, None)

class FSMonitorWindowsError(WindowsError, FSMonitorError):
    pass

class FSMonitorWatch(object):
    def __init__(self, path, recursive, userobj):
        self.path = path
        self.userobj = userobj
        self._recursive = recursive
        self._key = None
        self._hDir = GetDirHandle(path)
        self._overlapped = pywintypes.OVERLAPPED()
        self._buf = ctypes.create_string_buffer(1024)
        self._removed = False

    def _close(self):
        win32file.CancelIo(self._hDir)
        win32file.CloseHandle(self._hDir)
        self._hDir = None

    def __del__(self):
        if module_loaded and self._hDir is not None:
            self._close()

    def __repr__(self):
        return "<FSMonitorWatch %r>" % self.path

def _process_events(watch, num):
    for action, name in win32file.FILE_NOTIFY_INFORMATION(watch._buf.raw, num):
        action = action_map.get(action)
        if action is not None:
            yield FSMonitorEvent(watch, action, name)
    try:
        ReadDirChanges(watch._hDir, watch._buf, watch._recursive, watch._overlapped)
    except pywintypes.error, e:
        if e.args[0] == 5:
            watch._close()
            yield FSMonitorEvent(watch, FSEVT_DELETE_SELF)
        else:
            raise FSMonitorWindowsError(*e.args)

class FSMonitor(object):
    def __init__(self, path=None, recursive=False):
        self.__key_to_watch = {}
        self.__last_key = 0
        self.__lock = threading.Lock()
        self.__cphandle = win32file.CreateIoCompletionPort(-1, None, 0, 0)
        if path:
            self.add_watch(path, recursive)

    def __del__(self):
        if module_loaded:
            self.close()

    def close(self):
        win32file.CloseHandle(self.__cphandle)
        del self.__cphandle

    def add_watch(self, path, userobj=None, recursive=False):
        try:
            watch = FSMonitorWatch(path, recursive, userobj)
            with self.__lock:
                key = self.__last_key
                win32file.CreateIoCompletionPort(watch._hDir, self.__cphandle, key, 0)
                self.__last_key += 1
                ReadDirChanges(watch._hDir, watch._buf, recursive, watch._overlapped)
                watch._key = key
                self.__key_to_watch[key] = watch
            return watch
        except pywintypes.error, e:
            raise FSMonitorWindowsError(*e.args)

    def remove_watch(self, watch):
        with self.__lock:
            if not watch._removed:
                try:
                    watch._removed = True
                    win32file.PostQueuedCompletionStatus(self.__cphandle, 0, watch._key, watch._overlapped)
                    watch._close()
                    return True
                except pywintypes.error:
                    pass
        return False

    def read_events(self):
        try:
            rc, num, key, _ = win32file.GetQueuedCompletionStatus(self.__cphandle, 1000)
            if rc == 0:
                with self.__lock:
                    watch = self.__key_to_watch.get(key)
                    if watch is not None:
                        if watch._removed:
                            del self.__key_to_watch[key]
                        else:
                            for evt in _process_events(watch, num):
                                yield evt
            elif rc == 5:
                with self.__lock:
                    watch = self.__key_to_watch.get(key)
                    if watch is not None:
                        watch._close()
                        yield FSMonitorEvent(watch, FSEVT_DELETE_SELF)
        except pywintypes.error, e:
            raise FSMonitorWindowsError(*e.args)

    @property
    def watches(self):
        with self.__lock:
            return self.__key_to_watch.values()
