#!/usr/bin/python

##################
# DisplayOptionsPanel.py
#
# Copyright David Baddeley, 2010
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import wx
import pylab
from PYME.misc import extraCMaps
#from matplotlib import cm
from PYME.Analysis.LMVis import histLimits
from displayOptions import DisplayOpts, fast_grey

class OptionsPanel(wx.Panel):
    def __init__(self, parent, displayOpts, horizOrientation=False, thresholdControls=True, **kwargs):
        kwargs['style'] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, parent, **kwargs)

        #self.parent = parent
        self.do = displayOpts

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.hIds = []
        self.cIds = []
        self.cbIds = []
        self.hcs = []

        cmapnames = pylab.cm.cmapnames + ['fastGrey']# + [n + '_r' for n in pylab.cm.cmapnames]
        cmapnames.sort()
        ##do = parent.do

        dispSize = (120, 80)

        if horizOrientation:
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            dispSize = (100, 80)

        for i in range(len(self.do.Chans)):
            ssizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, self.do.names[i]), wx.VERTICAL)

            id = wx.NewId()
            self.hIds.append(id)
            c = self.do.ds[:,:,self.do.zp, self.do.Chans[i]].ravel()
            hClim = histLimits.HistLimitPanel(self, id, c[::max(1, len(c)/1e4)], self.do.Offs[i], self.do.Offs[i] + 1./self.do.Gains[i], size=dispSize, log=True)

            hClim.Bind(histLimits.EVT_LIMIT_CHANGE, self.OnCLimChanged)
            self.hcs.append(hClim)

            ssizer.Add(hClim, 0, wx.ALL, 2)

            id = wx.NewId()
            self.cIds.append(id)
            cCmap = wx.Choice(self, id, choices=cmapnames, size=(80, -1))
            cCmap.SetSelection(cmapnames.index(self.do.cmaps[i].name))
            cCmap.Bind(wx.EVT_CHOICE, self.OnCMapChanged)
            ssizer.Add(cCmap, 0, wx.ALL|wx.EXPAND, 2)

            if horizOrientation:
                hsizer.Add(ssizer, 0, wx.ALL, 2)
            else:
                vsizer.Add(ssizer, 0, wx.ALL, 5)

        self.bOptimise = wx.Button(self, -1, "Stretch", style=wx.BU_EXACTFIT)

        self.cbScale = wx.Choice(self, -1, choices=["1:4", "1:2", "1:1", "2:1", "4:1"])
        self.cbScale.SetSelection(2)

        if horizOrientation:
            vsizer.Add(hsizer, 0, wx.ALL, 0)
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            hsizer.Add(self.bOptimise, 0, wx.ALL|wx.ALIGN_CENTER, 5)
            hsizer.Add(self.cbScale, 0, wx.ALL|wx.ALIGN_CENTER, 5)
            vsizer.Add(hsizer, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        else:
            vsizer.Add(self.bOptimise, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_CENTER|wx.EXPAND, 5)

            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            #ssizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Slice'), wx.VERTICAL)
            self.cbSlice = wx.Choice(self, -1, choices=["X-Y", "X-Z", "Y-Z"])
            self.cbSlice.SetSelection(0)
            hsizer.Add(self.cbSlice, 1, wx.ALL|wx.EXPAND, 5)

            #vsizer.Add(ssizer, 0, wx.ALL|wx.EXPAND, 5)

            #ssizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Scale'), wx.VERTICAL)
            hsizer.Add(self.cbScale, 1, wx.ALL|wx.EXPAND, 5)

            vsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

            self.cbSlice.Bind(wx.EVT_CHOICE, self.OnSliceChanged)

        
        #self.cbSlice.Bind(wx.EVT_CHOICE, self.OnSliceChanged)
        self.cbScale.Bind(wx.EVT_CHOICE, self.OnScaleChanged)

        self.bOptimise.Bind(wx.EVT_BUTTON, self.OnOptimise)

        if thresholdControls:
            ssizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Segmentation'), wx.VERTICAL)

            self.cbShowThreshold = wx.CheckBox(self, -1, 'Threshold mode')
            self.cbShowThreshold.Bind(wx.EVT_CHECKBOX, self.OnShowThreshold)
            ssizer.Add(self.cbShowThreshold, 0, wx.ALL, 5)

            self.bIsodataThresh = wx.Button(self, -1, 'Isodata')
            self.bIsodataThresh.Bind(wx.EVT_BUTTON, self.OnIsodataThresh)
            self.bIsodataThresh.Enable(False)
            ssizer.Add(self.bIsodataThresh, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)


            hsizer=wx.BoxSizer(wx.HORIZONTAL)
            self.tPercThresh = wx.TextCtrl(self, -1, '.80', size=[30, -1])
            self.tPercThresh.Enable(False)
            hsizer.Add(self.tPercThresh, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 1)
            self.bPercThresh = wx.Button(self, -1, 'Signal Fraction')
            self.bPercThresh.Bind(wx.EVT_BUTTON, self.OnSignalFracThresh)
            self.bPercThresh.Enable(False)
            hsizer.Add(self.bPercThresh, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 1)
            ssizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 5)

            vsizer.Add(ssizer, 0, wx.ALL|wx.EXPAND, 5)

        self.SetSizer(vsizer)

    def OnOptimise(self, event):
        self.do.Optimise()
        self.RefreshHists()

    #constants for slice selection
    sliceChoices = [DisplayOpts.SLICE_XY,DisplayOpts.SLICE_XZ, DisplayOpts.SLICE_YZ]
    orientationChoices = [DisplayOpts.UPRIGHT,DisplayOpts.UPRIGHT,DisplayOpts.UPRIGHT]

    def OnSliceChanged(self, event):
        sel = self.cbSlice.GetSelection()

        self.do.SetSlice(self.sliceChoices[sel])
        self.do.SetOrientation(self.orientationChoices[sel])


    def OnScaleChanged(self, event):
        self.do.SetScale(self.cbScale.GetSelection())

    def OnCLimChanged(self, event):
        ind = self.hIds.index(event.GetId())
        self.do.SetOffset(ind, event.lower)
        self.do.SetGain(ind,1./(event.upper- event.lower))

    def OnCMapChanged(self, event):
        #print event.GetId()
        ind = self.cIds.index(event.GetId())

        cmn = event.GetString()
        if cmn == 'fastGrey':
            self.do.SetCMap(ind, fast_grey)
        else:
            self.do.SetCMap(ind, pylab.cm.__getattribute__(cmn))

    def OnShowThreshold(self, event):
        tMode = self.cbShowThreshold.GetValue()
        for hClim in self.hcs:
            hClim.SetThresholdMode(tMode)

        self.bIsodataThresh.Enable(tMode)
        self.tPercThresh.Enable(tMode)
        self.bPercThresh.Enable(tMode)


    def OnIsodataThresh(self, event):
        from PYME.Analysis import thresholding
        for i, hClim in enumerate(self.hcs):
            t = thresholding.isodata_f(self.do.ds[:,:,:,i])
            hClim.SetValueAndFire((t,t))

    def OnSignalFracThresh(self, event):
        from PYME.Analysis import thresholding
        frac = max(0., min(1., float(self.tPercThresh.GetValue())))
        for i, hClim in enumerate(self.hcs):
            t = thresholding.signalFraction(self.do.ds[:,:,:,i], frac)
            hClim.SetValueAndFire((t,t))


    def RefreshHists(self):
        for i in range(len(self.do.Chans)):
            c = self.do.ds[:,:,self.do.zp, self.do.Chans[i]].ravel()
            self.hcs[i].SetData(c[::max(1, len(c)/1e4)], self.do.Offs[i], self.do.Offs[i] + 1./self.do.Gains[i])



