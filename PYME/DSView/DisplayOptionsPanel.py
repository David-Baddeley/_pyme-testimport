#!/usr/bin/python

##################
# DisplayOptionsPanel.py
#
# Copyright David Baddeley, 2010
# d.baddeley@auckland.ac.nz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##################

import wx
import wx.lib.agw.aui as aui
import pylab
try:
    from PYME.misc import extraCMaps
except:
    pass
import numpy as np
#from matplotlib import cm
from PYME.Analysis.LMVis import histLimits
from displayOptions import DisplayOpts, fast_grey, labeled

import os
dirname = os.path.dirname(__file__)

#windows complains if bitmaps are loaded before wx.App exists - defer loading to first use
bmCrosshairs = None #wx.Bitmap(os.path.join(dirname, 'icons/crosshairs.png'))
bmRectSelect = None #wx.Bitmap(os.path.join(dirname, 'icons/rect_select.png'))
bmLineSelect = None #wx.Bitmap(os.path.join(dirname, 'icons/line_select.png'))
bmSquiggleSelect = None

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
        self.shIds = []

        cmapnames = pylab.cm.cmapnames + ['fastGrey', 'labeled']# + [n + '_r' for n in pylab.cm.cmapnames]
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
            c = self.do.ds[:,:,self.do.zp, self.do.Chans[i]].real.ravel()
            if np.iscomplexobj(c):
                if self.do.complexMode == 'real':
                    c = c.real
                elif self.do.complexMode == 'imag':
                    c = c.imag
                elif self.do.complexMode == 'angle':
                    c = np.angle(c)
                else:
                    c = np.abs(c)
                    
            hClim = histLimits.HistLimitPanel(self, id, c[::max(1, len(c)/1e4)], self.do.Offs[i], self.do.Offs[i] + 1./self.do.Gains[i], size=dispSize, log=True)

            hClim.Bind(histLimits.EVT_LIMIT_CHANGE, self.OnCLimChanged)
            self.hcs.append(hClim)

            ssizer.Add(hClim, 0, wx.ALL, 2)
            
            hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

            id = wx.NewId()
            self.cIds.append(id)
            cCmap = wx.Choice(self, id, choices=cmapnames, size=(80, -1))
            cCmap.SetSelection(cmapnames.index(self.do.cmaps[i].name))
            cCmap.Bind(wx.EVT_CHOICE, self.OnCMapChanged)
            hsizer2.Add(cCmap, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
            
            id = wx.NewId()
            self.shIds.append(id)            
            cbShow = wx.CheckBox(self, id)
            cbShow.SetValue(self.do.show[i])
            cbShow.Bind(wx.EVT_CHECKBOX, self.OnShowChanged)
            hsizer2.Add(cbShow, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL,2)
            
            ssizer.Add(hsizer2, 0, wx.ALL|wx.EXPAND, 0)

            if horizOrientation:
                hsizer.Add(ssizer, 0, wx.ALL, 2)
            else:
                vsizer.Add(ssizer, 0, wx.ALL, 5)

        self.bOptimise = wx.Button(self, -1, "Stretch", style=wx.BU_EXACTFIT)

        self.cbScale = wx.Choice(self, -1, choices=["1:16", "1:8", "1:4", "1:2", "1:1", "2:1", "4:1", "8:1", "16:1"])
        self.cbScale.SetSelection(4)
        self.scale_11 = 4

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
        
        if self.do.ds.shape[2] > 1:        
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            hsizer.Add(wx.StaticText(self, -1, 'Projection:'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
            self.czProject = wx.Choice(self, -1, choices=['None', 'Standard', 'Colour Coded'])
            self.czProject.SetSelection(0)
            self.czProject.Bind(wx.EVT_CHOICE, self.OnZProjChanged)
            hsizer.Add(self.czProject, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
            vsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)
            
        if np.iscomplexobj(self.do.ds[0,0,0,0]):        
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            #hsizer.Add(wx.StaticText(self, -1, 'Projection:'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
            self.cComplex = wx.Choice(self, -1, choices=['colored', 'real', 'imag', 'angle', 'abs'])
            self.cComplex.SetSelection(0)
            self.cComplex.Bind(wx.EVT_CHOICE, self.OnComplexChanged)
            hsizer.Add(self.cComplex, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
            vsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)
            

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
        
        self.do.WantChangeNotification.append(self.OnDoChange)

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
        self.do.SetScale(self.cbScale.GetSelection() - self.scale_11)

    def OnCLimChanged(self, event):
        #print 'clc'
        ind = self.hIds.index(event.GetId())
        self.do.SetOffset(ind, event.lower)
        self.do.SetGain(ind,1./(event.upper- event.lower + 1e-4))

    def OnCMapChanged(self, event):
        #print event.GetId()
        ind = self.cIds.index(event.GetId())

        cmn = event.GetString()
        if cmn == 'fastGrey':
            self.do.SetCMap(ind, fast_grey)

        elif cmn == 'labeled':
            self.do.SetCMap(ind, labeled)
        else:
            self.do.SetCMap(ind, pylab.cm.__getattribute__(cmn))
            
    def OnComplexChanged(self, event):
        #print event.GetId()
        #ind = self.cIds.index(event.GetId())

        cmn = event.GetString()
        self.do.complexMode = cmn
        self.RefreshHists()
            
    def OnShowChanged(self, event):
        #print event.GetId()
        ind = self.shIds.index(event.GetId())
        
        self.do.Show(ind,event.IsChecked())


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
            if np.iscomplexobj(c):
                if self.do.complexMode == 'real':
                    c = c.real
                elif self.do.complexMode == 'imag':
                    c = c.imag
                elif self.do.complexMode == 'angle':
                    c = np.angle(c)
                else:
                    c = np.abs(c)
            self.hcs[i].SetData(c[::max(1, len(c)/1e4)], self.do.Offs[i], self.do.Offs[i] + 1./self.do.Gains[i])

    def CreateToolBar(self, wind):
        global bmCrosshairs, bmRectSelect, bmLineSelect, bmSquiggleSelect

        if bmCrosshairs == None: #load bitmaps on first use
            bmCrosshairs = wx.Bitmap(os.path.join(dirname, 'icons/crosshairs.png'))
            bmRectSelect = wx.Bitmap(os.path.join(dirname, 'icons/rect_select.png'))
            bmLineSelect = wx.Bitmap(os.path.join(dirname, 'icons/line_select.png'))
            bmSquiggleSelect = wx.Bitmap(os.path.join(dirname, 'icons/squiggle_select.png'))

        self.toolB = aui.AuiToolBar(wind, -1, wx.DefaultPosition, wx.DefaultSize, agwStyle=aui.AUI_TB_DEFAULT_STYLE | aui.AUI_TB_OVERFLOW | aui.AUI_TB_VERTICAL)
        self.toolB.SetToolBitmapSize(wx.Size(16, 16))

        #ID_POINTER = wx.NewId()
        ID_CROSSHAIRS = wx.NewId()
        ID_RECTSELECT = wx.NewId()
        ID_LINESELECT = wx.NewId()
        ID_SQUIGGLESELECT = wx.NewId()

        self.toolB.AddRadioTool(ID_CROSSHAIRS, "Point selection", bmCrosshairs, bmCrosshairs)
        self.toolB.AddRadioTool(ID_RECTSELECT, "Rectangle selection", bmRectSelect, bmRectSelect)
        self.toolB.AddRadioTool(ID_LINESELECT, "Line selection", bmLineSelect, bmLineSelect)
        self.toolB.AddRadioTool(ID_SQUIGGLESELECT, "Freeform selection", bmSquiggleSelect, bmSquiggleSelect)

        self.toolB.Realize()

        #self._mgr.AddPane(tb5, aui.AuiPaneInfo().Name("tb5").Caption("Sample Vertical Toolbar").
        #                  ToolbarPane().Left().GripperTop())

        self.toolB.ToggleTool(ID_CROSSHAIRS, True)

        wind.Bind(wx.EVT_TOOL, self.OnSelectCrosshairs, id=ID_CROSSHAIRS)
        wind.Bind(wx.EVT_TOOL, self.OnSelectRectangle, id=ID_RECTSELECT)
        wind.Bind(wx.EVT_TOOL, self.OnSelectLine, id=ID_LINESELECT)
        wind.Bind(aui.EVT_AUITOOLBAR_RIGHT_CLICK, self.OnLineThickness, id=ID_LINESELECT)
        wind.Bind(wx.EVT_TOOL, self.OnSelectSquiggle, id=ID_SQUIGGLESELECT)

        return self.toolB

    def OnSelectCrosshairs(self, event):
        self.do.leftButtonAction = DisplayOpts.ACTION_POSITION
        self.do.selectionMode = DisplayOpts.SELECTION_RECTANGLE
        self.do.showSelection = False

        #self.Refresh()
        self.do.OnChange()

    def OnSelectRectangle(self, event):
        self.do.leftButtonAction = DisplayOpts.ACTION_SELECTION
        self.do.selectionMode = DisplayOpts.SELECTION_RECTANGLE
        self.do.showSelection = True

        #self.Refresh()
        self.do.OnChange()

    def OnSelectLine(self, event):
        self.do.leftButtonAction = DisplayOpts.ACTION_SELECTION
        self.do.selectionMode = DisplayOpts.SELECTION_LINE
        self.do.showSelection = True

        #self.Refresh()
        self.do.OnChange()
        
    def OnSelectSquiggle(self, event):
        self.do.leftButtonAction = DisplayOpts.ACTION_SELECTION
        self.do.selectionMode = DisplayOpts.SELECTION_SQUIGLE
        self.do.showSelection = True

        #self.Refresh()
        self.do.OnChange()
        
    def OnZProjChanged(self, event):
        state = self.czProject.GetSelection()
        if state == 0: #no projection
            self.do.maximumProjection = False
        if state == 1:
            self.do.maximumProjection = True
            self.do.colourMax = False
        if state == 2:
            self.do.maximumProjection = True
            self.do.colourMax = True    

        #self.Refresh()
        self.do.OnChange()

    def OnLineThickness(self, event):
        print('foo')
        dlg = wx.TextEntryDialog(self, 'Line Thickness', 'Set width of line selection', '%d' % self.do.selectionWidth)

        if dlg.ShowModal() == wx.ID_OK:
            self.do.selectionWidth = int(dlg.GetValue())

        dlg.Destroy()

        self.do.OnChange()

        #self.Refresh()
        
    def OnDoChange(self):
        #print 'c'
        self.cbScale.SetSelection(self.do.scale + self.scale_11)



