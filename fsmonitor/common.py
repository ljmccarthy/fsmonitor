FSEVT_ACCESS      = 0x01
FSEVT_MODIFY      = 0x02
FSEVT_ATTRIB      = 0x04
FSEVT_CREATE      = 0x08
FSEVT_DELETE      = 0x10
FSEVT_DELETE_SELF = 0x20
FSEVT_MOVE_FROM   = 0x40
FSEVT_MOVE_TO     = 0x80
FSEVT_ALL         = 0xFF

fs_evt_name = {
    FSEVT_ACCESS      : "access",
    FSEVT_MODIFY      : "modify",
    FSEVT_ATTRIB      : "attrib",
    FSEVT_CREATE      : "create",
    FSEVT_DELETE      : "delete",
    FSEVT_DELETE_SELF : "delete self",
    FSEVT_MOVE_TO     : "move to",
    FSEVT_MOVE_FROM   : "move from",
}

class FSMonitorError(Exception):
    pass

class FSMonitorOSError(OSError, FSMonitorError):
    pass

class FSMonitorEvent(object):
    def __init__(self, watch, action, name=""):
        self.watch = watch
        self.name = name
        self.action = action

    @property
    def action_name(self):
        return fs_evt_name[self.action]

    @property
    def path(self):
        return self.watch.path

    @property
    def user(self):
        return self.watch.user
