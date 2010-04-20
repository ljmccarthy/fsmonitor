#!/usr/bin/env python

import sys, os, wx
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from fsmonitor import FSMonitorThread

class DemoFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="FSMonitor wxWidgets Demo", size=(600, 800))

        self.monitor = FSMonitorThread(
            lambda evt: wx.CallAfter(self.OnFileSystemChanged, evt))

        self.list = wx.ListBox(self)
        btn_add = wx.Button(self, label="&Add")
        btn_remove = wx.Button(self, label="&Remove")
        btn_clear = wx.Button(self, label="&Clear")
        self.log = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_DONTWRAP)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.AddStretchSpacer()
        btnsizer.Add(btn_add, 0, wx.ALL, 5)
        btnsizer.Add(btn_remove, 0, wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="Directories to monitor:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(btnsizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(wx.StaticText(self, label="Monitor log:"), 0, wx.LEFT | wx.RIGHT, 5)
        sizer.Add(self.log, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(btn_clear, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_BUTTON, self.OnAdd, btn_add)
        self.Bind(wx.EVT_BUTTON, self.OnRemove, btn_remove)
        self.Bind(wx.EVT_BUTTON, self.OnClear, btn_clear)

    def OnClose(self, evt):
        self.Hide()
        wx.CallAfter(self.Shutdown)

    def Shutdown(self):
        self.monitor.stop()
        self.Destroy()

    def AddPath(self, path):
        try:
            watch = self.monitor.add_dir_watch(path)
        except OSError, e:
            dlg = wx.MessageDialog(self, str(e), "Error", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            self.list.Append(path, watch)

    def OnAdd(self, evt):
        dlg = wx.DirDialog(self)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.AddPath(dlg.GetPath())
        finally:
            dlg.Destroy()

    def OnRemove(self, evt):
        selection = self.list.GetSelection()
        if selection != wx.NOT_FOUND:
            watch = self.list.GetClientData(selection)
            self.monitor.remove_watch(watch)
            self.list.Delete(selection)

    def OnClear(self, evt):
        self.log.Clear()

    def OnFileSystemChanged(self, evt):
        if isinstance(self, wx._core._wxPyDeadObject):
            return
        path = os.path.join(evt.watch.path, evt.name)
        message = "%s %s\n" % (evt.action_name, path)
        self.log.AppendText(message)

if __name__ == "__main__":
    app = wx.PySimpleApp()
    frame = DemoFrame()
    frame.Show()
    app.MainLoop()
