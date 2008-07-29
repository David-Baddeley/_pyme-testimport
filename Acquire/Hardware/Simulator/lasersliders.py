#!/usr/bin/env python
# generated by wxGlade 0.3.3 on Thu Sep 23 08:22:22 2004


import wx

#redefine wxFrame with a version that hides when someone tries to close it
#dirty trick, but lets the Boa gui builder still work with frames we do this to
#from noclosefr import * 

class LaserSliders(wx.Frame):
    def __init__(self, cam, laserNames=['405', '488'], parent=None, winid=-1, title="Laser Power"):
        # begin wxGlade: MyFrame1.__init__
        #kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, winid, title)

        self.cam = cam
        self.laserNames=laserNames
        self.panel_1 = wx.Panel(self, -1)
        self.sliders = []
        #self.SetTitle("Piezo Control")
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)

        for c in range(len(self.cam.laserPowers)):
            sl = wx.Slider(self.panel_1, -1, self.cam.laserPowers[c], 0, 1000, size=wx.Size(800,50),style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
            #sl.SetSize((800,20))
            sl.SetTickFreq(100,1)
            sz = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, -1, self.laserNames[c] + " [mW]"), wx.HORIZONTAL)
            sz.Add(sl, 0, wx.ALL, 5)
            sizer_2.Add(sz,1,0,0)

            self.sliders.append(sl)

        wx.EVT_SCROLL(self,self.onSlide)
                
       
        self.panel_1.SetAutoLayout(1)
        self.panel_1.SetSizer(sizer_2)
        sizer_2.Fit(self.panel_1)
        sizer_2.SetSizeHints(self.panel_1)
        sizer_1.Add(self.panel_1, 1, wx.EXPAND, 0)
        self.SetAutoLayout(1)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        sizer_1.SetSizeHints(self)
        self.Layout()
        # end wxGlade

    def onSlide(self, event):
        sl = event.GetEventObject()
        ind = self.sliders.index(sl)
        self.sl = sl
        self.ind = ind
        self.cam.laserPowers[ind] = sl.GetValue()

    def update(self):
        for ind in range(len(self.piezos)):
            self.sliders[ind].SetValue(self.cam.laserPowers[ind])

            


