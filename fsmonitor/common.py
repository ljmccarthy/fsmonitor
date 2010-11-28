# Copyright (c) 2010 Luke McCarthy <luke@iogopro.co.uk>
#
# This is free software released under the MIT license.
# See COPYING file for details, or visit:
# http://www.opensource.org/licenses/mit-license.php
#
# The file is part of FSMonitor, a file-system monitoring library.
# https://github.com/shaurz/fsmonitor

class FSMonitorError(Exception):
    pass

class FSMonitorOSError(OSError, FSMonitorError):
    pass

class FSEvent(object):
    def __init__(self, watch, action, name=""):
        self.watch = watch
        self.name = name
        self.action = action

    @property
    def action_name(self):
        return self.action_names[self.action]

    @property
    def path(self):
        return self.watch.path

    @property
    def user(self):
        return self.watch.user

    Access      = 0x01
    Modify      = 0x02
    Attrib      = 0x04
    Create      = 0x08
    Delete      = 0x10
    DeleteSelf  = 0x20
    MoveFrom    = 0x40
    MoveTo      = 0x80
    All         = 0xFF

    action_names = {
        Access     : "access",
        Modify     : "modify",
        Attrib     : "attrib",
        Create     : "create",
        Delete     : "delete",
        DeleteSelf : "delete self",
        MoveFrom   : "move from",
        MoveTo     : "move to",
    }
