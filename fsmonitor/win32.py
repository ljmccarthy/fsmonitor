import os, threading
import win32file, win32con, pywintypes
import ctypes
from .common import *

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

class FSMonitorWatch(object):
    def __init__(self, path, recursive, userobj):
        self.path = path
        self.recursive = recursive
        self.userobj = userobj
        self.key = None
        self.hDir = GetDirHandle(path)
        self.overlapped = pywintypes.OVERLAPPED()
        self.buf = ctypes.create_string_buffer(1024)
        self.removed = False

    def __del__(self):
        if hasattr(self, "hDir"):
            import win32file
            win32file.CloseHandle(self.hDir)
            del self.hDir

class FSMonitor(object):
    def __init__(self, path=None, recursive=False):
        self.__path_to_watch = {}
        self.__key_to_watch = {}
        self.__last_key = 0
        self.__lock = threading.Lock()
        self.__cphandle = win32file.CreateIoCompletionPort(-1, None, 0, 0)
        if path:
            self.add_watch(path, recursive)

    def __del__(self):
        self.close()

    def close(self):
        import win32file
        win32file.CloseHandle(self.__cphandle)
        del self.__cphandle

    def add_watch(self, path, userobj=None, recursive=False):
        watch = FSMonitorWatch(path, recursive, userobj)
        with self.__lock:
            key = self.__last_key
            win32file.CreateIoCompletionPort(watch.hDir, self.__cphandle, key, 0)
            self.__last_key += 1
            ReadDirChanges(watch.hDir, watch.buf, recursive, watch.overlapped)
            watch.key = key
            self.__key_to_watch[key] = watch
            self.__path_to_watch[path] = watch

    def remove_watch(self, path):
        with self.__lock:
            watch = self.__path_to_watch.get(path)
            if watch is not None and not watch.removed:
                watch.removed = True
                win32file.CancelIo(watch.hDir)
                win32file.PostQueuedCompletionStatus(self.__cphandle, 0, watch.key, watch.overlapped)
                return True
        return False

    def __remove(self, watch):
        del self.__key_to_watch[watch.key]
        del self.__path_to_watch[watch.path]

    def read_events(self, timeout=None):
        if timeout is not None and timeout < 0:
            raise FSMonitorError("Timeout must be positive or None")
        if timeout is None:
            timeout = -1
        rc, num, key, _ = win32file.GetQueuedCompletionStatus(self.__cphandle, timeout)
        if rc == 0:
            with self.__lock:
                watch = self.__key_to_watch.get(key)
                if watch is not None:
                    if watch.removed:
                        self.__remove(watch)
                        yield FSMonitorEvent(watch.path, "", FSEVT_DELETE_SELF, watch.userobj)
                    else:
                        for action, name in win32file.FILE_NOTIFY_INFORMATION(watch.buf.raw, num):
                            action = action_map.get(action)
                            if action is not None:
                                yield FSMonitorEvent(watch.path, name, action, watch.userobj)
                        ReadDirChanges(watch.hDir, watch.buf, watch.recursive, watch.overlapped)
        elif rc == 5:
            with self.__lock:
                watch = self.__key_to_watch.get(key)
                if watch is not None:
                    self.__remove(watch)
                    yield FSMonitorEvent(watch.path, "", FSEVT_DELETE_SELF, watch.userobj)

    @property
    def watches(self):
        with self.__lock:
            return self.__path_to_watch.values()
