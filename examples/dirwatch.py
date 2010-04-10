#!/usr/bin/env python

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from fsmonitor import FSMonitor

if len(sys.argv) < 2:
    print "usage: dirwatch.py [DIRS...]"
    sys.exit(1)

m = FSMonitor()
for arg in sys.argv[1:]:
    m.add_dir_watch(arg)

while True:
    for evt in m.read_events():
        print "%s %s %s" % (evt.action_name, evt.watch.path, evt.name)
