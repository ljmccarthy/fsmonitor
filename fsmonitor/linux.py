# Copyright (c) 2010 Luke McCarthy <luke@iogopro.co.uk>
#
# This is free software released under the MIT license.
# See COPYING file for details, or visit:
# http://www.opensource.org/licenses/mit-license.php
#
# The file is part of FSMonitor, a file-system monitoring library.
# https://github.com/shaurz/fsmonitor

import sys, os, struct, threading, errno, select
from ctypes import CDLL, CFUNCTYPE, POINTER, c_int, c_char_p, c_uint32, get_errno
from .common import FSEvent, FSMonitorOSError
from .compat import PY3

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
    IN_ACCESS      : FSEvent.Access,
    IN_MODIFY      : FSEvent.Modify,
    IN_ATTRIB      : FSEvent.Attrib,
    IN_MOVED_FROM  : FSEvent.MoveFrom,
    IN_MOVED_TO    : FSEvent.MoveTo,
    IN_CREATE      : FSEvent.Create,
    IN_DELETE      : FSEvent.Delete,
    IN_DELETE_SELF : FSEvent.DeleteSelf,
}

flags_map = {
    FSEvent.Access     : IN_ACCESS,
    FSEvent.Modify     : IN_MODIFY,
    FSEvent.Attrib     : IN_ATTRIB,
    FSEvent.Create     : IN_CREATE,
    FSEvent.Delete     : IN_DELETE,
    FSEvent.DeleteSelf : IN_DELETE_SELF,
    FSEvent.MoveFrom   : IN_MOVED_FROM,
    FSEvent.MoveTo     : IN_MOVED_TO,
}

def convert_flags(flags):
    os_flags = 0
    flag = 1
    while flag < FSEvent.All + 1:
        if flags & flag:
            os_flags |= flags_map[flag]
        flag <<= 1
    return os_flags

def parse_events(s):
    i = 0
    while i + 16 < len(s):
        wd, mask, cookie, length = struct.unpack_from("iIII", s, i)
        name = s[i+16:i+16+length].rstrip(b"\0")
        i += 16 + length
        yield wd, mask, cookie, name

class FSMonitorWatch(object):
    def __init__(self, wd, path, flags, user):
        self._wd = wd
        self.path = path
        self.flags = flags
        self.user = user
        self.enabled = True

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
        if self.__fd is not None:
            os.close(self.__fd)
            self.__fd = None

    def _add_watch(self, path, flags, user, inotify_flags=0):
        inotify_flags |= convert_flags(flags) | IN_DELETE_SELF
        if PY3 and not isinstance(path, bytes):
            path = path.encode(sys.getfilesystemencoding())
        wd = inotify_add_watch(self.__fd, path, inotify_flags)
        if wd == -1:
            errno = get_errno()
            raise FSMonitorOSError(errno, strerror(errno))
        watch = FSMonitorWatch(wd, path, flags, user)
        with self.__lock:
            self.__wd_to_watch[wd] = watch
        return watch

    def add_dir_watch(self, path, flags=FSEvent.All, user=None):
        return self._add_watch(path, flags, user, IN_ONLYDIR)

    def add_file_watch(self, path, flags=FSEvent.All, user=None):
        return self._add_watch(path, flags, user)

    def remove_watch(self, watch):
        return inotify_rm_watch(self.__fd, watch._wd) != -1

    def remove_all_watches(self):
        with self.__lock:
            for wd in self.__wd_to_watch.iterkeys():
                inotify_rm_watch(self.__fd, wd)

    def enable_watch(self, watch, enable=True):
        watch.enabled = enable

    def disable_watch(self, watch):
        watch.enabled = False

    def read_events(self, timeout=None):
        if timeout is not None:
            rs, ws, xs = select.select([self.__fd], [], [], timeout)
            if self.__fd not in rs:
                return []

        while True:
            try:
                s = os.read(self.__fd, 1024)
                break
            except OSError as e:
                if e.errno != errno.EINTR:
                    raise FSMonitorOSError(*e.args)

        events = []
        if not module_loaded:
            return events

        fsencoding = sys.getfilesystemencoding()
        for wd, mask, cookie, name in parse_events(s):
            with self.__lock:
                watch = self.__wd_to_watch.get(wd)
            if watch is not None and watch.enabled:
                bit = 1
                while bit < 0x10000:
                    if mask & bit:
                        action = action_map.get(bit)
                        if action is not None and (action & watch.flags):
                            if PY3 and isinstance(name, bytes):
                                name = name.decode(fsencoding)
                            events.append(FSEvent(watch, action, name))
                    bit <<= 1
                if mask & IN_IGNORED:
                    with self.__lock:
                        try:
                            del self.__wd_to_watch[wd]
                        except KeyError:
                            pass
        return events

    @property
    def watches(self):
        with self.__lock:
            return self.__wd_to_watch.values()
