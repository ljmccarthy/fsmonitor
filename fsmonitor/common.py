FSEVT_ACCESS      = 1
FSEVT_MODIFY      = 2
FSEVT_ATTRIB      = 3
FSEVT_CREATE      = 4
FSEVT_DELETE      = 5
FSEVT_DELETE_SELF = 6
FSEVT_MOVE_TO     = 7
FSEVT_MOVE_FROM   = 8

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
    def __init__(self, path, name, action, userobj):
        self.path = path
        self.name = name
        self.action = action
        self.action_name = fs_evt_name[action]
        self.userobj = userobj
