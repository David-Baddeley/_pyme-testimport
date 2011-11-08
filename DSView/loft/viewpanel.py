#!/usr/bin/python

##################
# viewpanel.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

#!/usr/bin/env python
# generated by wxGlade 0.3.3 on Mon Jun 14 07:44:41 2004

import wx

class ViewPanel(wx.Panel):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ViewPanel.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.optionspanel = wx.ScrolledWindow(self, -1, style=wx.TAB_TRAVERSAL)
        self.imagepanel = wx.ScrolledWindow(self, -1, style=wx.SUNKEN_BORDER|wx.TAB_TRAVERSAL)
        self.bShowOpts = wx.Button(self, -1, "", size=wx.Size(7,-1))
        self.cbRedChan = wx.ComboBox(self.optionspanel, -1, choices=[], style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.label_1 = wx.StaticText(self.optionspanel, -1, "Gain:")
        self.tRedGain = wx.TextCtrl(self.optionspanel, -1, "")
        self.label_2 = wx.StaticText(self.optionspanel, -1, "Offset:")
        self.tRedOff = wx.TextCtrl(self.optionspanel, -1, "")
        self.cbGreenChan = wx.ComboBox(self.optionspanel, -1, choices=[], style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.label_1_copy = wx.StaticText(self.optionspanel, -1, "Gain:")
        self.tGreenGain = wx.TextCtrl(self.optionspanel, -1, "")
        self.label_2_copy = wx.StaticText(self.optionspanel, -1, "Offset:")
        self.tGreenOff = wx.TextCtrl(self.optionspanel, -1, "")
        self.cbBlueChan = wx.ComboBox(self.optionspanel, -1, choices=[], style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.label_1_copy_copy = wx.StaticText(self.optionspanel, -1, "Gain:")
        self.tBlueGain = wx.TextCtrl(self.optionspanel, -1, "")
        self.label_2_copy_copy = wx.StaticText(self.optionspanel, -1, "Offset:")
        self.tBlueOff = wx.TextCtrl(self.optionspanel, -1, "")
        self.bOptimise = wx.Button(self.optionspanel, -1, "Optimise")
        self.cbSlice = wx.ComboBox(self.optionspanel, -1, choices=["X-Y", "X-Y @ 90 Deg", "X-Z", "Y-Z"], style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.cbScale = wx.ComboBox(self.optionspanel, -1, choices=["1:4", "1:2", "1:1", "2:1", "4:1"], style=wx.CB_DROPDOWN|wx.CB_READONLY)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: ViewPanel.__set_properties
        #self.imagepanel.SetSize((504, 521))
        self.imagepanel.SetScrollRate(10, 10)
        self.bShowOpts.SetSize((7, -1))
        self.cbRedChan.SetSize((80, -1))
        self.cbRedChan.SetSelection(-1)
        self.label_1.SetSize((35, 13))
        self.tRedGain.SetSize((40, -1))
        self.tRedOff.SetSize((40, -1))
        self.cbGreenChan.SetSize((80, -1))
        self.cbGreenChan.SetSelection(-1)
        self.label_1_copy.SetSize((35, 13))
        self.tGreenGain.SetSize((40, -1))
        self.tGreenOff.SetSize((40, -1))
        self.cbBlueChan.SetSize((80, -1))
        self.cbBlueChan.SetSelection(-1)
        self.label_1_copy_copy.SetSize((35, 13))
        self.tBlueGain.SetSize((40, -1))
        self.tBlueOff.SetSize((40, -1))
        self.bOptimise.SetDefault()
        self.cbSlice.SetSize((80, -1))
        self.cbSlice.SetSelection(0)
        self.cbScale.SetSize((80, -1))
        self.cbScale.SetSelection(2)
        self.optionspanel.SetScrollRate(10, 10)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ViewPanel.__do_layout
        vpsizer = wx.BoxSizer(wx.HORIZONTAL)
        opsizer = wx.BoxSizer(wx.VERTICAL)
        scaleSizer = wx.StaticBoxSizer(wx.StaticBox(self.optionspanel, -1, "Scale"), wx.HORIZONTAL)
        sliceSizer = wx.StaticBoxSizer(wx.StaticBox(self.optionspanel, -1, "Slice"), wx.HORIZONTAL)
        blueSizer1 = wx.StaticBoxSizer(wx.StaticBox(self.optionspanel, -1, "Blue"), wx.VERTICAL)
        blueSizer2 = wx.FlexGridSizer(2, 2, 0, 5)
        greenSizer1 = wx.StaticBoxSizer(wx.StaticBox(self.optionspanel, -1, "Green"), wx.VERTICAL)
        greenSizer2 = wx.FlexGridSizer(2, 2, 0, 5)
        redSizer1 = wx.StaticBoxSizer(wx.StaticBox(self.optionspanel, -1, "Red"), wx.VERTICAL)
        redSizer2 = wx.FlexGridSizer(2, 2, 0, 5)
        vpsizer.Add(self.imagepanel, 1, wx.EXPAND, 0)
        vpsizer.Add(self.bShowOpts, 0, wx.EXPAND, 0)
        redSizer1.Add(self.cbRedChan, 0, wx.TOP, 3)
        redSizer2.Add(self.label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        redSizer2.Add(self.tRedGain, 0, 0, 0)
        redSizer2.Add(self.label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        redSizer2.Add(self.tRedOff, 0, 0, 0)
        redSizer1.Add(redSizer2, 0, 0, 0)
        opsizer.Add(redSizer1, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        greenSizer1.Add(self.cbGreenChan, 0, wx.TOP, 3)
        greenSizer2.Add(self.label_1_copy, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        greenSizer2.Add(self.tGreenGain, 0, 0, 0)
        greenSizer2.Add(self.label_2_copy, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        greenSizer2.Add(self.tGreenOff, 0, 0, 0)
        greenSizer1.Add(greenSizer2, 0, 0, 0)
        opsizer.Add(greenSizer1, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        blueSizer1.Add(self.cbBlueChan, 0, wx.TOP, 3)
        blueSizer2.Add(self.label_1_copy_copy, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        blueSizer2.Add(self.tBlueGain, 0, 0, 0)
        blueSizer2.Add(self.label_2_copy_copy, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        blueSizer2.Add(self.tBlueOff, 0, 0, 0)
        blueSizer1.Add(blueSizer2, 0, 0, 0)
        opsizer.Add(blueSizer1, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        opsizer.Add(self.bOptimise, 0, wx.TOP|wx.ALIGN_CENTER_HORIZONTAL, 5)
        opsizer.Add((20, 15), 1, 0, 0)
        sliceSizer.Add(self.cbSlice, 0, wx.TOP, 3)
        opsizer.Add(sliceSizer, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_BOTTOM, 5)
        scaleSizer.Add(self.cbScale, 0, wx.TOP, 3)
        opsizer.Add(scaleSizer, 0, wx.ALL|wx.ALIGN_BOTTOM, 5)
        self.optionspanel.SetAutoLayout(1)
        self.optionspanel.SetSizer(opsizer)
        opsizer.Fit(self.optionspanel)
        opsizer.SetSizeHints(self.optionspanel)
        vpsizer.Add(self.optionspanel, 0, wx.EXPAND, 0)
        self.SetAutoLayout(1)
        self.SetSizer(vpsizer)
        vpsizer.Fit(self)
        vpsizer.SetSizeHints(self)
        # end wxGlade

# end of class ViewPanel


