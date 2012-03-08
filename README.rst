fsmonitor - Filesystem Monitoring for Python
============================================

Supported Platforms
-------------------

* Linux 2.6 (inotify)
* Windows (ReadDirectoryChangesW with I/O completion ports)
* Any other platform (polling)

Installation
------------

$ python setup.py install

Introduction
------------

The fsmonitor module provides live filesystem monitoring. It can be used to monitor for
events such as file creation, deletion, modification and so on::

    from fsmonitor import FSMonitor

The FSMonitor class manages filesystem watches and is used to receive events. Call the
add_dir_watch() method to add a directory watch to the monitor::

    m = FSMonitor()
    watch = m.add_dir_watch("/dir/to/watch")

Once a watch has been added, you can call read_events() to read a list of filesystem
events. This is a blocking call and in some cases it might return an empty list, so it
needs to be re-called repeatedly to get more events::

    while True:
        for evt in m.read_events():
            print evt.action_name, evt.name

The FSMonitorThread class can be used to receive events asynchronously with a callback.
The callback will be called from another thread so it is responsible for thread-safety.
If a callback is not specified, the thread will collect events in a list which can be
read by calling read_events().

More Details
------------

See the example code in the examples directory.

Contact Details
---------------

Please send any comments or questions to: luke@iogopro.co.uk

Please report bugs on the `github issue tracker <http://github.com/shaurz/fsmonitor/issues>`_.

-- Luke McCarthy
