#!/usr/bin/python

##################
# genImageDialog.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import wx
import histLimits


class GenImageDialog(wx.Dialog):
    def __init__(self, parent, mode='current', defaultPixelSize=5.0, jitterVariables = [], jitterVarDefault=0, mcProbDefault = 1.0, colours = [], zvals=None, jitterVarDefaultZ=0):
        wx.Dialog.__init__(self, parent, title='Edit Filter ...')

        pixelSzs = ['%3.2f' % (defaultPixelSize*2**n) for n in range(6)]

        jitterPhrase = 'Jitter [nm]:'
        if mode in ['gaussian', '3Dgaussian']:
            jitterPhrase = 'Std. Dev. [nm]:'
        
        sizer1 = wx.BoxSizer(wx.VERTICAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        
        #we always want a pixel size
        sizer2.Add(wx.StaticText(self, -1, 'Pixel Size [nm]:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        self.cbPixelSize = wx.ComboBox(self, -1, value='%3.2f' % defaultPixelSize, choices=pixelSzs, style=wx.CB_DROPDOWN, size=(150, -1))


        sizer2.Add(self.cbPixelSize, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        

        #jitter parameter for gaussian and triangles
        if mode in ['gaussian', 'triangles', '3Dgaussian']:
            sizer2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer2.Add(wx.StaticText(self, -1, jitterPhrase), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.tJitterScale = wx.TextCtrl(self, -1, '1.0', size=(60, -1))
            sizer2.Add(self.tJitterScale, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            sizer2.Add(wx.StaticText(self, -1, 'x'), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP|wx.BOTTOM, 5)
    
            self.cJitterVariable = wx.Choice(self, -1, choices=jitterVariables, size=(150, -1))
            self.cJitterVariable.SetSelection(jitterVarDefault)
            sizer2.Add(self.cJitterVariable, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        #jitter parameter for gaussian in z
        if mode == '3Dgaussian':
            sizer2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer2.Add(wx.StaticText(self, -1, 'Z Std. Dev. [nm]:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.tJitterScaleZ = wx.TextCtrl(self, -1, '1.0', size=(60, -1))
            sizer2.Add(self.tJitterScaleZ, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            sizer2.Add(wx.StaticText(self, -1, 'x'), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP|wx.BOTTOM, 5)

            self.cJitterVariableZ = wx.Choice(self, -1, choices=jitterVariables, size=(150, -1))
            self.cJitterVariableZ.SetSelection(jitterVarDefaultZ)
            sizer2.Add(self.cJitterVariableZ, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        #MC subsampling parameter for triangles
        if mode == 'triangles':
            sizer2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer2.Add(wx.StaticText(self, -1, 'MC subsampling probability:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.tMCProb = wx.TextCtrl(self, -1, '%3.2f' % mcProbDefault, size=(60, -1))
            sizer2.Add(self.tMCProb, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

            sizer2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer2.Add(wx.StaticText(self, -1, '# Samples to average:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.tNumSamps = wx.TextCtrl(self, -1, '10', size=(60, -1))
            sizer2.Add(self.tNumSamps, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        if mode in ['3Dhistogram', '3Dgaussian']:
            sizer2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer2.Add(wx.StaticText(self, -1, 'Z slice thickness [nm]:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.tZThickness = wx.TextCtrl(self, -1, '100', size=(60, -1))
            sizer2.Add(self.tZThickness, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

            sizer2 = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Z range:'), wx.VERTICAL)

            self.hZRange = histLimits.HistLimitPanel(self, -1, zvals[::max(len(zvals)/1e4, 1)], zvals.min(), zvals.max(), size=(150, 80))

            sizer2.Add(self.hZRange, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL|wx.EXPAND, 5)

            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        #multiple colour channels
        if len(colours) > 0:
            sizer2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer2.Add(wx.StaticText(self, -1, 'Colour[s]:'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.colours = ['Everything'] + colours

            self.lColour = wx.ListBox(self, -1, choices=self.colours, size=(150, -1), style=wx.LB_MULTIPLE)

            for n in range(1, len(self.colours)):
                self.lColour.SetSelection(n)

            sizer2.Add(self.lColour, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            sizer1.Add(sizer2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5)

        
        btSizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()

        btSizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)

        btSizer.AddButton(btn)

        btSizer.Realize()

        sizer1.Add(btSizer, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer1)
        sizer1.Fit(self)

    def getPixelSize(self):
        return float(self.cbPixelSize.GetValue())

    def getJitterVariable(self):
        return self.cJitterVariable.GetStringSelection()

    def getJitterScale(self):
        return float(self.tJitterScale.GetValue())

    def getJitterVariableZ(self):
        return self.cJitterVariableZ.GetStringSelection()

    def getJitterScaleZ(self):
        return float(self.tJitterScaleZ.GetValue())

    def getMCProbability(self):
        return float(self.tMCProb.GetValue())

    def getNumSamples(self):
        return int(self.tNumSamps.GetValue())

    def getColour(self):
        if 'colours' in dir(self):
            return [self.lColour.GetString(n).encode() for n in self.lColour.GetSelections()]
        else:
            return [None]

    def getZSliceThickness(self):
        return float(self.tZThickness.GetValue())

    def getZBounds(self):
        return self.hZRange.GetValue()
