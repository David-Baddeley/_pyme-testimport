#!/usr/bin/env python
# generated by wxGlade 0.3.3 on Thu Oct 07 06:57:02 2004

import wx

class sPanel(wx.Panel):
    def __init__(self, *args, **kwds):
        # begin wxGlade: sPanel.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.rbStartEnd = wx.RadioButton(self, -1, "Start and End")
        self.rbMidNum = wx.RadioButton(self, -1, "Middle and #")
        self.cPiezo = wx.Choice(self, -1, choices=[])
        self.label_6 = wx.StaticText(self, -1, "Start Pos:")
        self.tStart = wx.TextCtrl(self, -1, "")
        self.bSetStart = wx.Button(self, -1, "Set")
        self.label_7 = wx.StaticText(self, -1, "End Pos:")
        self.tEnd = wx.TextCtrl(self, -1, "")
        self.bSetEnd = wx.Button(self, -1, "Set")
        self.tStepSize = wx.TextCtrl(self, -1, "")
        self.tNumSlices = wx.TextCtrl(self, -1, "")
        self.bStart = wx.Button(self, -1, "Start")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: sPanel.__set_properties
        self.rbStartEnd.SetValue(1)
        self.cPiezo.SetSize((80, 20))
        self.cPiezo.SetSelection(0)
        self.tStart.SetSize((50, -1))
        self.bSetStart.SetSize((40, -1))
        self.tEnd.SetSize((50, -1))
        self.bSetEnd.SetSize((40, -1))
        self.tStepSize.SetSize((50, -1))
        self.tNumSlices.SetSize((50, -1))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: sPanel.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Num Slices:"), wx.HORIZONTAL)
        sizer_8 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Step Size:"), wx.HORIZONTAL)
        grid_sizer_1 = wx.FlexGridSizer(2, 3, 5, 5)
        sizer_7 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Piezo Channel:"), wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Scan Type"), wx.VERTICAL)
        sizer_6.Add(self.rbStartEnd, 0, wx.ALL, 5)
        sizer_6.Add(self.rbMidNum, 0, wx.ALL, 5)
        sizer_2.Add(sizer_6, 1, 0, 5)
        sizer_1.Add(sizer_2, 0, wx.EXPAND, 0)
        sizer_7.Add(self.cPiezo, 0, wx.ALL, 3)
        sizer_1.Add(sizer_7, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.label_6, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        grid_sizer_1.Add(self.tStart, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        grid_sizer_1.Add(self.bSetStart, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        grid_sizer_1.Add(self.label_7, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        grid_sizer_1.Add(self.tEnd, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        grid_sizer_1.Add(self.bSetEnd, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_1.Add(grid_sizer_1, 0, wx.TOP|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_8.Add(self.tStepSize, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 3)
        sizer_5.Add(sizer_8, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        sizer_9.Add(self.tNumSlices, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 3)
        sizer_5.Add(sizer_9, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        sizer_1.Add(sizer_5, 0, wx.TOP|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer_1.Add(self.bStart, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
        self.SetAutoLayout(1)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        sizer_1.SetSizeHints(self)
        # end wxGlade

# end of class sPanel


class SDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: SDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.panel_1 = sPanel(self, -1)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: SDialog.__set_properties
        self.SetTitle("Sequence ...")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: SDialog.__do_layout
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(self.panel_1, 1, wx.EXPAND, 0)
        self.SetAutoLayout(1)
        self.SetSizer(sizer_10)
        sizer_10.Fit(self)
        sizer_10.SetSizeHints(self)
        self.Layout()
        # end wxGlade

# end of class SDialog


class MyApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        seqDialog = SDialog(None, -1, "")
        self.SetTopWindow(seqDialog)
        seqDialog.Show(1)
        return 1

# end of class MyApp

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()
