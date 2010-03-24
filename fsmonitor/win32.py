import os, threading
import win32file, win32con, pywintypes
import ctypes
from .common import *

# set to None when unloaded
module_loaded = True

FILE_LIST_DIRECTORY = 0x0001
FILE_NOTIFY_CHANGE_LAST_ACCESS = 0x20
FILE_NOTIFY_CHANGE_CREATION = 0x40

action_map = {
    1 : FSEVT_CREATE,
    2 : FSEVT_DELETE,
    3 : FSEVT_MODIFY,
    4 : FSEVT_MOVE_FROM,
    5 : FSEVT_MOVE_TO,
}

flags_map = {
    FSEVT_ACCESS      : FILE_NOTIFY_CHANGE_LAST_ACCESS,
    FSEVT_MODIFY      : win32con.FILE_NOTIFY_CHANGE_LAST_WRITE | win32con.FILE_NOTIFY_CHANGE_SIZE,
    FSEVT_ATTRIB      : win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES | win32con.FILE_NOTIFY_CHANGE_SECURITY,
    FSEVT_CREATE      : FILE_NOTIFY_CHANGE_CREATION,
    FSEVT_DELETE      : win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_DIR_NAME,
    FSEVT_DELETE_SELF : 0,
    FSEVT_MOVE_FROM   : win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_DIR_NAME,
    FSEVT_MOVE_TO     : win32con.FILE_NOTIFY_CHANGE_FILE_NAME | win32con.FILE_NOTIFY_CHANGE_DIR_NAME,
}

def convert_flags(flags):
    os_flags = 0
    flag = 1
    while flag < FSEVT_ALL + 1:
        if flags & flag:
            os_flags |= flags_map[flag]
        flag <<= 1
    return os_flags

def GetDirHandle(path):
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
        self._recursive = recursive
        self._win32_flags = convert_flags(flags)
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
        if action is not None and (action & watch.flags):
            yield FSMonitorEvent(watch, action, name)
    try:
        win32file.ReadDirectoryChangesW(
            watch._hDir, watch._buf, watch._recursive, watch._win32_flags,
            watch._overlapped, None)
    except pywintypes.error, e:
        if e.args[0] == 5:
            watch._close()
            yield FSMonitorEvent(watch, FSEVT_DELETE_SELF)
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
        win32file.CloseHandle(self.__cphandle)
        del self.__cphandle

    def add_dir_watch(self, path, flags=FSEVT_ALL, user=None, recursive=False):
        try:
            flags |= FSEVT_DELETE_SELF
            watch = FSMonitorWatch(path, flags, user, recursive)
            with self.__lock:
                key = self.__last_key
                win32file.CreateIoCompletionPort(watch._hDir, self.__cphandle, key, 0)
                self.__last_key += 1
                win32file.ReadDirectoryChangesW(
                    watch._hDir, watch._buf, watch._recursive, watch._win32_flags,
                    watch._overlapped, None)
                watch._key = key
                self.__key_to_watch[key] = watch
            return watch
        except pywintypes.error, e:
            raise FSMonitorWindowsError(*e.args)

    def add_file_watch(self, path, flags=FSEVT_ALL, user=None):
        raise NotImplementedError()

    def remove_watch(self, watch):
        with self.__lock:
            if not watch._removed:
                try:
                    watch._removed = True
                    win32file.PostQueuedCompletionStatus(
                        self.__cphandle, 0, watch._key, watch._overlapped)
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
                    if watch is not None and not watch._removed:
                        for evt in _process_events(watch, num):
                            yield evt
            elif rc == 5:
                with self.__lock:
                    watch = self.__key_to_watch.get(key)
                    if watch is not None:
                        watch._close()
                        del self.__key_to_watch[key]
                        yield FSMonitorEvent(watch, FSEVT_DELETE_SELF)
        except pywintypes.error, e:
            raise FSMonitorWindowsError(*e.args)

    @property
    def watches(self):
        with self.__lock:
            return self.__key_to_watch.values()
