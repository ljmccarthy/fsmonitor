import os, struct, threading
from ctypes import CDLL, CFUNCTYPE, POINTER, c_int, c_char_p, c_uint32, get_errno
from .common import *

# set to None when unloaded
module_loaded = True

libc = CDLL("libc.so.6")

strerror = CFUNCTYPE(c_char_p, c_int)(
    ("strerror", libc))

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

# Special flags.
IN_ONLYDIR       = 0x01000000     # Only watch the path if it is a directory.
IN_DONT_FOLLOW   = 0x02000000     # Do not follow a sym link.
IN_MASK_ADD      = 0x20000000     # Add to the mask of an already existing watch.
IN_ISDIR         = 0x40000000     # Event occurred against dir.
IN_ONESHOT       = 0x80000000     # Only send event once.

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

flags_map = {
    FSEVT_ACCESS      : IN_ACCESS,
    FSEVT_MODIFY      : IN_MODIFY,
    FSEVT_ATTRIB      : IN_ATTRIB,
    FSEVT_CREATE      : IN_CREATE,
    FSEVT_DELETE      : IN_DELETE,
    FSEVT_DELETE_SELF : IN_DELETE_SELF,
    FSEVT_MOVE_FROM   : IN_MOVED_FROM,
    FSEVT_MOVE_TO     : IN_MOVED_TO,
}

def convert_flags(flags):
    os_flags = 0
    flag = 1
    while flag < FSEVT_ALL + 1:
        if flags & flag:
            os_flags |= flags_map[flag]
        flag <<= 1
    return os_flags

def parse_events(s):
    i = 0
    while i + 16 < len(s):
        wd, mask, cookie, length = struct.unpack_from("iIII", s, i)
        name = s[i+16:i+16+length].rstrip("\0")
        i += 16 + length
        yield wd, mask, cookie, name

class FSMonitorWatch(object):
    def __init__(self, wd, path, flags, user):
        self._wd = wd
        self.path = path
        self.flags = flags
        self.user = user

    def __repr__(self):
        return "<FSMonitorWatch %r>" % self.path

class FSMonitor(object):
    def __init__(self):
        fd = inotify_init()
        if fd == -1:
            errno = get_errno()
            raise FSMonitorOSError(errno, strerror(errno))
        self.__fd = fd
        self.__lock = threading.Lock()
        self.__wd_to_watch = {}

    def __del__(self):
        if module_loaded:
            self.close()

    def close(self):
        os.close(self.__fd)

    def add_dir_watch(self, path, flags=FSEVT_ALL, user=None):
        flags |= FSEVT_DELETE_SELF
        inotify_flags = convert_flags(flags)
        wd = inotify_add_watch(self.__fd, path, inotify_flags)
        if wd == -1:
            errno = get_errno()
            raise FSMonitorOSError(errno, strerror(errno))
        watch = FSMonitorWatch(wd, path, flags, user)
        with self.__lock:
            self.__wd_to_watch[wd] = watch
        return watch

    add_file_watch = add_dir_watch

    def remove_watch(self, watch):
        return inotify_rm_watch(self.__fd, watch._wd) != -1

    def read_events(self):
        try:
            s = os.read(self.__fd, 1024)
        except OSError, e:
            raise FSMonitorOSError(*e.args)
        if not module_loaded:
            return
        for wd, mask, cookie, name in parse_events(s):
            with self.__lock:
                watch = self.__wd_to_watch.get(wd)
            if watch is not None:
                bit = 1
                while bit < 0x10000:
                    if mask & bit:
                        action = action_map.get(bit)
                        if action is not None and (action & watch.flags):
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
