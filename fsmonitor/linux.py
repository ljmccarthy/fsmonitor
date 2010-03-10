import os, struct, threading
from ctypes import CDLL, CFUNCTYPE, POINTER, c_int, c_char_p, c_uint32
from .common import *

libc = CDLL("libc.so.6")

errno_location = CFUNCTYPE(POINTER(c_int))(("__errno_location", libc))
def get_errno():
    return errno_location().contents.value

inotify_init = CFUNCTYPE(c_int, use_errno=True)(
    ("inotify_init", libc))
inotify_add_watch = CFUNCTYPE(c_int, c_int, c_char_p, c_uint32, use_errno=True)(
    ("inotify_add_watch", libc))
inotify_rm_watch = CFUNCTYPE(c_int, c_int, c_int, use_errno=True)(
    ("inotify_rm_watch", libc))

# Supported events suitable for MASK parameter of INOTIFY_ADD_WATCH.
IN_ACCESS        = 0x00000001     # File was accessed.
IN_MODIFY        = 0x00000002     # File was modified.
IN_ATTRIB        = 0x00000004     # Metadata changed.
IN_CLOSE_WRITE   = 0x00000008     # Writtable file was closed.
IN_CLOSE_NOWRITE = 0x00000010     # Unwrittable file closed.
IN_CLOSE         = IN_CLOSE_WRITE | IN_CLOSE_NOWRITE  # Close.
IN_OPEN          = 0x00000020     # File was opened.
IN_MOVED_FROM    = 0x00000040     # File was moved from X.
IN_MOVED_TO      = 0x00000080     # File was moved to Y.
IN_MOVE          = IN_MOVED_FROM | IN_MOVED_TO  # Moves.
IN_CREATE        = 0x00000100     # Subfile was created.
IN_DELETE        = 0x00000200     # Subfile was deleted.
IN_DELETE_SELF   = 0x00000400     # Self was deleted.
IN_MOVE_SELF     = 0x00000800     # Self was moved.

# Events sent by the kernel.
IN_UNMOUNT       = 0x00002000     # Backing fs was unmounted.
IN_Q_OVERFLOW    = 0x00004000     # Event queued overflowed.
IN_IGNORED       = 0x00008000     # File was ignored.

# Helper events.
IN_CLOSE         = IN_CLOSE_WRITE | IN_CLOSE_NOWRITE    # Close.
IN_MOVE          = IN_MOVED_FROM | IN_MOVED_TO          # Moves.

# Special flags.
IN_ONLYDIR       = 0x01000000     # Only watch the path if it is a directory.
IN_DONT_FOLLOW   = 0x02000000     # Do not follow a sym link.
IN_MASK_ADD      = 0x20000000     # Add to the mask of an already existing watch.
IN_ISDIR         = 0x40000000     # Event occurred against dir.
IN_ONESHOT       = 0x80000000     # Only send event once.

# All events which a program can wait on.
IN_ALL_EVENTS = (IN_ACCESS | IN_MODIFY | IN_ATTRIB | IN_CLOSE_WRITE
                | IN_CLOSE_NOWRITE | IN_OPEN | IN_MOVED_FROM
                | IN_MOVED_TO | IN_CREATE | IN_DELETE
                | IN_DELETE_SELF | IN_MOVE_SELF)

flags = IN_ALL_EVENTS & ~(IN_ACCESS | IN_OPEN)

action_map = {
    IN_ACCESS      : FSEVT_ACCESS,
    IN_MODIFY      : FSEVT_MODIFY,
    IN_ATTRIB      : FSEVT_ATTRIB,
    IN_MOVED_FROM  : FSEVT_MOVE_FROM,
    IN_MOVED_TO    : FSEVT_MOVE_TO,
    IN_CREATE      : FSEVT_CREATE,
    IN_DELETE      : FSEVT_DELETE,
    IN_DELETE_SELF : FSEVT_DELETE_SELF,
}

class FSMonitorWatch(object):
    def __init__(self, wd, path, userobj):
        self._wd = wd
        self.path = path
        self.userobj = userobj

    def __repr__(self):
        return "<FSMonitorWatch %r>" % self.path

class FSMonitor(object):
    def __init__(self, path=None):
        fd = inotify_init()
        if fd == -1:
            raise FSMonitorOSError(get_errno(), "inotify_init failed")
        self.__fd = fd
        self.__lock = threading.Lock()
        self.__wd_to_watch = {}
        if path is not None:
            self.add_watch(path)

    def __del__(self):
        import os
        os.close(self.__fd)

    def add_watch(self, path, userobj=None):
        wd = inotify_add_watch(self.__fd, path, flags)
        if wd == -1:
            raise FSMonitorOSError(get_errno(), "inotify_add_watch failed")
        watch = FSMonitorWatch(wd, path, userobj)
        with self.__lock:
            self.__wd_to_watch[wd] = watch
        return watch

    def remove_watch(self, watch):
        return inotify_rm_watch(self.__fd, watch._wd) != -1

    def read_events(self):
        try:
            s = os.read(self.__fd, 1024)
        except OSError, e:
            raise FSMonitorOSError(*e.args)
        i = 0
        while i + 16 < len(s):
            wd, mask, cookie, length = struct.unpack_from("iIII", s, i)
            name = s[i+16:i+16+length].rstrip("\0")
            i += 16 + length
            with self.__lock:
                watch = self.__wd_to_watch.get(wd)
            if watch is not None:
                bit = 1
                while bit < 0x10000:
                    if mask & bit:
                        action = action_map.get(bit)
                        if action is not None:
                            yield FSMonitorEvent(watch, action, name)
                    bit <<= 1
                if mask & IN_IGNORED:
                    with self.__lock:
                        try:
                            del self.__wd_to_watch[wd]
                        except KeyError:
                            pass

    @property
    def watches(self):
        with self.__lock:
            return self.__wd_to_watch.values()
