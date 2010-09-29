#!/usr/bin/python

##################
# VisGUI.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

#!/usr/bin/python
import os.path
import wx
import wx.py.shell

import PYME.misc.autoFoldPanel as afp
import wx.lib.agw.aui as aui

from PYME.Analysis.LMVis import gl_render
from PYME.Analysis.LMVis import workspaceTree
import sys
from PYME.Analysis.LMVis import inpFilt
from PYME.Analysis.LMVis import editFilterDialog
import pylab
from PYME.misc import extraCMaps
from PYME.FileUtils import nameUtils

from PYME.Analysis.EdgeDB import edges

import os
import gl_render3D

#try:
#    import delaunay as delny
#except:
#    pass

from matplotlib import delaunay

from PYME.Analysis.QuadTree import pointQT, QTrend
#import Image

from PYME.Analysis.LMVis import genImageDialog
from PYME.Analysis.LMVis import importTextDialog
from PYME.Analysis.LMVis import visHelpers
from PYME.Analysis.LMVis import imageView
from PYME.Analysis.LMVis import histLimits
from PYME.Analysis.LMVis import colourPanel
try:
#    from PYME.Analysis.LMVis import gen3DTriangs
    from PYME.Analysis.LMVis import recArrayView
    from PYME.Analysis.LMVis import objectMeasure
except:
    pass

from PYME.Analysis import intelliFit
from PYME.Analysis import piecewiseMapping
from PYME.Analysis import MetadataTree

#import time
import numpy as np
import scipy.special

import tables
from PYME.Analysis import MetaData
from PYME.Acquire import MetaDataHandler

from PYME.DSView import eventLogViewer

#import threading

from PYME.misc import editList
from PYME.misc.auiFloatBook import AuiNotebookWithFloatingPages

from PYME.Analysis.LMVis import statusLog
from PYME.Analysis.LMVis.visHelpers import ImageBounds, GeneratedImage


class VisGUIFrame(wx.Frame):    
    def __init__(self, parent, filename=None, id=wx.ID_ANY, title="PYME Visualise", pos=wx.DefaultPosition,
                 size=(700,650), style=wx.DEFAULT_FRAME_STYLE):

        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        self._mgr = aui.AuiManager(agwFlags = aui.AUI_MGR_DEFAULT | aui.AUI_MGR_AUTONB_NO_CAPTION)
        self._mgr.SetManagedWindow(self)

        self._flags = 0
               
        self.SetMenuBar(self.CreateMenuBar())

        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)
        #self.statusbar.SetStatusWidths([-4, -4])
        self.statusbar.SetStatusText("", 0)
       
        self._leftWindow1 = wx.Panel(self, -1, size = wx.Size(220, 1000))
        self._pnl = 0
        
        self.notebook = AuiNotebookWithFloatingPages(id=-1, parent=self, style=wx.aui.AUI_NB_TAB_SPLIT)

        self.MainWindow = self #so we can access from shell
        self.sh = wx.py.shell.Shell(id=-1,
              parent=self.notebook, size=wx.Size(-1, -1), style=0, locals=self.__dict__,
              introText='Python SMI bindings - note that help, license etc below is for Python, not PySMI\n\n')

        self.elv = None
        self.colp = None
        self.mdp = None
        self.rav = None

        self._pc_clim_change = False

        self.filesToClose = []
        self.generatedImages = []

        self.dataSources = []
        self.selectedDataSource = None
        self.filterKeys = {'error_x': (0,30), 'A':(5,2000), 'sig' : (95, 200)}

        self.filter = None
        self.mapping = None
        self.colourFilter = None

        self.driftCorrParams = {}
        self.driftCorrFcn = None
        self.optimiseFcn = 'fmin'
        self.driftExprX = 'x + a*t'
        self.driftExprY = 'y + b*t'
        self.driftExprZ = 'z + c*t'
        self.fitZDrift = False

        self.fluorSpecies = {}
        self.chromaticShifts = {}
        self.t_p_dye = 0.1
        self.t_p_other = 0.1
        self.t_p_background = .01

        self.objThreshold = 30
        self.objMinSize = 10
        self.blobJitter = 0
        self.objects = None

        self.imageBounds = ImageBounds(0,0,0,0)

        #generated Quad-tree will allow visualisations with pixel sizes of self.QTGoalPixelSize*2^N for any N
        self.QTGoalPixelSize = 5 #nm

        self.scaleBarLengths = {'<None>':None, '50nm':50,'200nm':200, '500nm':500, '1um':1000, '5um':5000}


        self.viewMode = 'points' #one of points, triangles, quads, or voronoi
        self.Triangles = None
        self.edb = None
        self.GeneratedMeasures = {}
        self.Quads = None
        #self.pointColour = None
        self.colData = '<None>'

        #self.sh = WxController(self.notebook)
        #print self.sh.shell.user_ns
        #self.__dict__.update(self.sh.shell.user_ns)
        #self.sh.shell.user_ns = self.__dict__

        self.notebook.AddPage(page=self.sh, select=True, caption='Console')

        #self.sh.execute_command('from pylab import *', hidden=True)
        #self.sh.execute_command('from PYME.DSView.dsviewer_npy import View3D', hidden=True)

        self.sh.Execute('from pylab import *')
        self.sh.Execute('from PYME.DSView.dsviewer_npy import View3D')
        #self.sh.runfile(os.path.join(os.path.dirname(__file__),'driftutil.py'))

        self.workspace = workspaceTree.WorkWrap(self.__dict__)

        ##### Make certain things visible in the workspace tree

        #components of the pipeline
        col = self.workspace.newColour()
        self.workspace.addKey('dataSources', col)
        self.workspace.addKey('selectedDataSource', col)
        self.workspace.addKey('filter', col)
        self.workspace.addKey('mapping', col)
        self.workspace.addKey('colourFilter', col)

        #Generated stuff
        col = self.workspace.newColour()
        self.workspace.addKey('GeneratedMeasures', col)
        self.workspace.addKey('generatedImages', col)
        self.workspace.addKey('objects', col)

        #main window, so we can get everything else if needed
        col = self.workspace.newColour()
        self.workspace.addKey('MainWindow', col)

        ######

        self.workspaceView = workspaceTree.WorkspaceTree(self.notebook, workspace=self.workspace, shell=self.sh)
        self.notebook.AddPage(page=self.workspaceView, select=False, caption='Workspace')

        self.glCanvas = gl_render.LMGLCanvas(self.notebook)
        self.notebook.AddPage(page=self.glCanvas, select=True, caption='View')
        self.glCanvas.cmap = pylab.cm.hot

        #self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_MOVE, self.OnMove)

        statusLog.SetStatusDispFcn(self.SetStatus)

        self.CreateFoldPanel()
        self._mgr.AddPane(self._leftWindow1, aui.AuiPaneInfo().
                          Name("sidebar").Left().CloseButton(False).CaptionVisible(False))

        self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().
                          Name("shell").Centre().CaptionVisible(False).CloseButton(False))

        self._mgr.Update()

        if not filename==None:
            #self.glCanvas.OnPaint(None)
            self.OpenFile(filename)


        print 'about to refresh'
        self.RefreshView()
        self.Refresh()      

    def OnSize(self, event):

        #wx.LayoutAlgorithm().LayoutWindow(self, self.notebook)
        event.Skip()

    def OnMove(self, event):
        #pass
        self.Refresh()
        event.Skip()
        

    def OnQuit(self, event):
        while len(self.filesToClose) > 0:
            self.filesToClose.pop().close()

        pylab.close('all')
        self.Destroy()


    def OnAbout(self, event):
        msg = "PYME Visualise\n\n Visualisation of localisation microscopy data\nDavid Baddeley 2009"
              
        dlg = wx.MessageDialog(self, msg, "About PYME Visualise",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.SetFont(wx.Font(8, wx.NORMAL, wx.NORMAL, wx.NORMAL, False, "Verdana"))
        dlg.ShowModal()
        dlg.Destroy()

    def OnToggleWindow(self, event):
        self._mgr.ShowPane(self._leftWindow1,not self._leftWindow1.IsShown())
        self.glCanvas.Refresh()    

    def CreateFoldPanel(self):
        # delete earlier panel
        self._leftWindow1.DestroyChildren()

        # recreate the foldpanelbar
        hsizer = wx.BoxSizer(wx.VERTICAL)

        s = self._leftWindow1.GetBestSize()

        self._pnl = afp.foldPanel(self._leftWindow1, -1, wx.DefaultPosition,s)

        self.GenDataSourcePanel()
        self.GenFilterPanel()
        self.GenDriftPanel()
        self.GenColourFilterPanel()
        self.GenDisplayPanel()
        
        if self.viewMode == 'quads':
            self.GenQuadTreePanel()

        if self.viewMode == 'points':
            self.GenPointsPanel()

        if self.viewMode == 'blobs':
            self.GenBlobPanel()

        if self.viewMode == 'interp_triangles':
            self.GenPointsPanel('Vertex Colours')

        hsizer.Add(self._pnl, 1, wx.EXPAND, 0)
        self._leftWindow1.SetSizerAndFit(hsizer)
        
        self.glCanvas.Refresh()

    def GenColourFilterPanel(self):
        item = afp.foldingPane(self._pnl, -1, caption="Colour", pinned = True)
        #panel.Reparent(item)
        #item.AddNewElement(panel)
        #self._pnl.AddPane(item)

        #item = self._pnl.AddFoldPanel("Colour", collapsed=False,
        #                              foldIcons=self.Images)

        cnames = ['Everything']

        if self.colourFilter:
            cnames += self.colourFilter.getColourChans()

        self.chColourFilterChan = wx.Choice(item, -1, choices=cnames, size=(170, -1))

        if self.colourFilter and self.colourFilter.currentColour in cnames:
            self.chColourFilterChan.SetSelection(cnames.index(self.colourFilter.currentColour))
        else:
            self.chColourFilterChan.SetSelection(0)

        self.chColourFilterChan.Bind(wx.EVT_CHOICE, self.OnColourFilterChange)
        #self._pnl.AddFoldPanelWindow(item, self.chColourFilterChan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)
        item.AddNewElement(self.chColourFilterChan)

        self._pnl.AddPane(item)


    def UpdateColourFilterChoices(self):
        cnames = ['Everything']

        if self.colourFilter:
            cnames += self.colourFilter.getColourChans()
            
        self.chColourFilterChan.Clear()
        for cn in cnames:
            self.chColourFilterChan.Append(cn)

        if self.colourFilter and self.colourFilter.currentColour in cnames:
            self.chColourFilterChan.SetSelection(cnames.index(self.colourFilter.currentColour))
        else:
            self.chColourFilterChan.SetSelection(0)


    def OnColourFilterChange(self, event):
        self.colourFilter.setColour(event.GetString())
        self.Triangles = None
        self.edb = None
        self.generatedMeasures = {}
        self.objects = None

        self.RefreshView()

    def GenDataSourcePanel(self):
        item = afp.foldingPane(self._pnl, -1, caption="Data Source", pinned = False)
        #item = self._pnl.AddFoldPanel("Data Source", collapsed=True,
        #                              foldIcons=self.Images)
        
        self.dsRadioIds = []
        for ds in self.dataSources:
            rbid = wx.NewId()
            self.dsRadioIds.append(rbid)
            rb = wx.RadioButton(item, rbid, ds._name)
            rb.SetValue(ds == self.selectedDataSource)

            rb.Bind(wx.EVT_RADIOBUTTON, self.OnSourceChange)
            item.AddNewElement(rb)
            #self._pnl.AddFoldPanelWindow(item, rb, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        self._pnl.AddPane(item)


    def OnSourceChange(self, event):
        dsind = self.dsRadioIds.index(event.GetId())
        self.selectedDataSource = self.dataSources[dsind]
        self.RegenFilter()

    def GenDisplayPanel(self):
        item = afp.foldingPane(self._pnl, -1, caption="Display", pinned = True)
#        item = self._pnl.AddFoldPanel("Display", collapsed=False,
#                                      foldIcons=self.Images)
        

        #Colourmap
        cmapnames = pylab.cm.cmapnames

        curCMapName = self.glCanvas.cmap.name
        #curCMapName = 'hot'

        cmapReversed = False
        
        if curCMapName[-2:] == '_r':
            cmapReversed = True
            curCMapName = curCMapName[:-2]

        cmInd = cmapnames.index(curCMapName)


        ##
        pan = wx.Panel(item, -1)

        box = wx.StaticBox(pan, -1, 'Colourmap:')
        bsizer = wx.StaticBoxSizer(box)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.cColourmap = wx.Choice(pan, -1, choices=cmapnames)
        self.cColourmap.SetSelection(cmInd)

        hsizer.Add(self.cColourmap, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.cbCmapReverse = wx.CheckBox(pan, -1, 'Invert')
        self.cbCmapReverse.SetValue(cmapReversed)

        hsizer.Add(self.cbCmapReverse, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL, 0)

        bdsizer = wx.BoxSizer()
        bdsizer.Add(bsizer, 1, wx.EXPAND|wx.ALL, 0)

        pan.SetSizer(bdsizer)
        bdsizer.Fit(pan)

        
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)
        item.AddNewElement(pan)

        self.cColourmap.Bind(wx.EVT_CHOICE, self.OnCMapChange)
        self.cbCmapReverse.Bind(wx.EVT_CHECKBOX, self.OnCMapChange)
        
        
        #CLim
        pan = wx.Panel(item, -1)

        box = wx.StaticBox(pan, -1, 'CLim:')
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Min: '), 0, wx.LEFT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tCLimMin = wx.TextCtrl(pan, -1, '%3.2f' % self.glCanvas.clim[0], size=(40,-1))
        hsizer.Add(self.tCLimMin, 0,wx.RIGHT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 5)

        hsizer.Add(wx.StaticText(pan, -1, '  Max: '), 0, wx.LEFT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tCLimMax = wx.TextCtrl(pan, -1, '%3.2f' % self.glCanvas.clim[1], size=(40,-1))
        hsizer.Add(self.tCLimMax, 0, wx.RIGHT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 5)
 
        bsizer.Add(hsizer, 0, wx.ALL, 0)

        self.hlCLim = histLimits.HistLimitPanel(pan, -1, self.glCanvas.c, self.glCanvas.clim[0], self.glCanvas.clim[1], size=(150, 100))
        bsizer.Add(self.hlCLim, 0, wx.ALL|wx.EXPAND, 5)

        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.tPercentileCLim = wx.TextCtrl(pan, -1, '.95', size=(40,-1))
        hsizer.Add(self.tPercentileCLim, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        bPercentile = wx.Button(pan, -1, 'Set Percentile')
        hsizer.Add(bPercentile, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
 
        bsizer.Add(hsizer, 0, wx.ALL, 0)

        bdsizer = wx.BoxSizer()
        bdsizer.Add(bsizer, 1, wx.EXPAND|wx.ALL, 0)

        pan.SetSizer(bdsizer)
        bdsizer.Fit(pan)

        #self.hlCLim.Refresh()

        item.AddNewElement(pan)
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        self.tCLimMin.Bind(wx.EVT_TEXT, self.OnCLimChange)
        self.tCLimMax.Bind(wx.EVT_TEXT, self.OnCLimChange)

        self.hlCLim.Bind(histLimits.EVT_LIMIT_CHANGE, self.OnCLimHistChange)

        bPercentile.Bind(wx.EVT_BUTTON, self.OnPercentileCLim)
        
        #self._pnl.AddFoldPanelSeparator(item)


        #LUT
        cbLUTDraw = wx.CheckBox(item, -1, 'Show LUT')
        cbLUTDraw.SetValue(self.glCanvas.LUTDraw)
        item.AddNewElement(cbLUTDraw)
        #self._pnl.AddFoldPanelWindow(item, cbLUTDraw, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        cbLUTDraw.Bind(wx.EVT_CHECKBOX, self.OnLUTDrawCB)

        
        #Scale Bar
        pan = wx.Panel(item, -1)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Scale Bar: '), 0, wx.LEFT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 5)


        chInd = self.scaleBarLengths.values().index(self.glCanvas.scaleBarLength)
        
        chScaleBar = wx.Choice(pan, -1, choices = self.scaleBarLengths.keys())
        chScaleBar.SetSelection(chInd)
        hsizer.Add(chScaleBar, 0,wx.RIGHT|wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, 5)

        pan.SetSizer(hsizer)
        hsizer.Fit(pan)
        
        item.AddNewElement(pan)
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        chScaleBar.Bind(wx.EVT_CHOICE, self.OnChangeScaleBar)

        self._pnl.AddPane(item)

        
    def OnCMapChange(self, event):
        cmapname = pylab.cm.cmapnames[self.cColourmap.GetSelection()]
        if self.cbCmapReverse.GetValue():
            cmapname += '_r'

        self.glCanvas.setCMap(pylab.cm.__dict__[cmapname])
        self.OnGLViewChanged()

    def OnLUTDrawCB(self, event):
        self.glCanvas.LUTDraw = event.IsChecked()
        self.glCanvas.Refresh()
        
    def OnChangeScaleBar(self, event):
        self.glCanvas.scaleBarLength = self.scaleBarLengths[event.GetString()]
        self.glCanvas.Refresh()

    def OnCLimChange(self, event):
        if self._pc_clim_change: #avoid setting CLim twice
            self._pc_clim_change = False #clear flag
        else:
            cmin = float(self.tCLimMin.GetValue())
            cmax = float(self.tCLimMax.GetValue())

            self.hlCLim.SetValue((cmin, cmax))

            self.glCanvas.setCLim((cmin, cmax))

    def OnCLimHistChange(self, event):
        self.glCanvas.setCLim((event.lower, event.upper))
        self._pc_clim_change = True
        self.tCLimMax.SetValue('%3.2f' % self.glCanvas.clim[1])
        self._pc_clim_change = True
        self.tCLimMin.SetValue('%3.2f' % self.glCanvas.clim[0])

    def OnPercentileCLim(self, event):
        pc = float(self.tPercentileCLim.GetValue())

        self.glCanvas.setPercentileCLim(pc)

        self._pc_clim_change = True
        self.tCLimMax.SetValue('%3.2f' % self.glCanvas.clim[1])
        self._pc_clim_change = True
        self.tCLimMin.SetValue('%3.2f' % self.glCanvas.clim[0])

        self.hlCLim.SetValue(self.glCanvas.clim)

        
        
            
    def GenFilterPanel(self):
        item = afp.foldingPane(self._pnl, -1, caption="Filter", pinned = False)
#        item = self._pnl.AddFoldPanel("Filter", collapsed=True,
#                                      foldIcons=self.Images)

        self.lFiltKeys = wx.ListCtrl(item, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.SUNKEN_BORDER, size=(-1, 200))

        item.AddNewElement(self.lFiltKeys)
        #self._pnl.AddFoldPanelWindow(item, self.lFiltKeys, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        self.lFiltKeys.InsertColumn(0, 'Key')
        self.lFiltKeys.InsertColumn(1, 'Min')
        self.lFiltKeys.InsertColumn(2, 'Max')

        for key, value in self.filterKeys.items():
            ind = self.lFiltKeys.InsertStringItem(sys.maxint, key)
            self.lFiltKeys.SetStringItem(ind,1, '%3.2f' % value[0])
            self.lFiltKeys.SetStringItem(ind,2, '%3.2f' % value[1])

        self.lFiltKeys.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.lFiltKeys.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        self.lFiltKeys.SetColumnWidth(2, wx.LIST_AUTOSIZE)

        # only do this part the first time so the events are only bound once
        if not hasattr(self, "ID_FILT_ADD"):
            self.ID_FILT_ADD = wx.NewId()
            self.ID_FILT_DELETE = wx.NewId()
            self.ID_FILT_EDIT = wx.NewId()
           
            self.Bind(wx.EVT_MENU, self.OnFilterAdd, id=self.ID_FILT_ADD)
            self.Bind(wx.EVT_MENU, self.OnFilterDelete, id=self.ID_FILT_DELETE)
            self.Bind(wx.EVT_MENU, self.OnFilterEdit, id=self.ID_FILT_EDIT)

        # for wxMSW
        self.lFiltKeys.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.OnFilterListRightClick)

        # for wxGTK
        self.lFiltKeys.Bind(wx.EVT_RIGHT_UP, self.OnFilterListRightClick)

        self.lFiltKeys.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFilterItemSelected)
        self.lFiltKeys.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnFilterItemDeselected)
        self.lFiltKeys.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnFilterEdit)

        self.stFilterNumPoints = wx.StaticText(item, -1, '')

        if not self.filter == None:
            self.stFilterNumPoints.SetLabel('%d of %d events' % (len(self.filter['x']), len(self.selectedDataSource['x'])))

        item.AddNewElement(self.stFilterNumPoints)
        #self._pnl.AddFoldPanelWindow(item, self.stFilterNumPoints, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        self.bClipToSelection = wx.Button(item, -1, 'Clip to selection')
        item.AddNewElement(self.bClipToSelection)
        #self._pnl.AddFoldPanelWindow(item, self.bClipToSelection, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        self.bClipToSelection.Bind(wx.EVT_BUTTON, self.OnFilterClipToSelection)

        self._pnl.AddPane(item)
        
    def OnFilterListRightClick(self, event):

        x = event.GetX()
        y = event.GetY()

        item, flags = self.lFiltKeys.HitTest((x, y))

 
        # make a menu
        menu = wx.Menu()
        # add some items
        menu.Append(self.ID_FILT_ADD, "Add")

        if item != wx.NOT_FOUND and flags & wx.LIST_HITTEST_ONITEM:
            self.currentFilterItem = item
            self.lFiltKeys.Select(item)
        
            menu.Append(self.ID_FILT_DELETE, "Delete")
            menu.Append(self.ID_FILT_EDIT, "Edit")

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()

    def OnFilterItemSelected(self, event):
        self.currentFilterItem = event.m_itemIndex

        event.Skip()

    def OnFilterItemDeselected(self, event):
        self.currentFilterItem = None

        event.Skip()

    def OnFilterClipToSelection(self, event):
        if 'x' in self.filterKeys.keys() or 'y' in self.filterKeys.keys():
            if 'x' in self.filterKeys.keys():
                i = 0
                while not self.lFiltKeys.GetItemText(i) == 'x':
                    i +=1
                self.lFiltKeys.DeleteItem(i)
                self.filterKeys.pop('x')
            if 'y' in self.filterKeys.keys():
                i = 0
                while not self.lFiltKeys.GetItemText(i) == 'y':
                    i +=1
                self.lFiltKeys.DeleteItem(i)
                self.filterKeys.pop('y')

            self.bClipToSelection.SetLabel('Clip to Selection')
        else:
            x0, y0 = self.glCanvas.selectionStart
            x1, y1 = self.glCanvas.selectionFinish

            if not 'x' in self.filterKeys.keys():
                indx = self.lFiltKeys.InsertStringItem(sys.maxint, 'x')
            else:
                indx = [self.lFiltKeys.GetItemText(i) for i in range(self.lFiltKeys.GetItemCount())].index('x')

            if not 'y' in self.filterKeys.keys():
                indy = self.lFiltKeys.InsertStringItem(sys.maxint, 'y')
            else:
                indy = [self.lFiltKeys.GetItemText(i) for i in range(self.lFiltKeys.GetItemCount())].index('y')


            self.filterKeys['x'] = (min(x0, x1), max(x0, x1))
            self.filterKeys['y'] = (min(y0, y1), max(y0,y1))

            self.lFiltKeys.SetStringItem(indx,1, '%3.2f' % min(x0, x1))
            self.lFiltKeys.SetStringItem(indx,2, '%3.2f' % max(x0, x1))

            self.lFiltKeys.SetStringItem(indy,1, '%3.2f' % min(y0, y1))
            self.lFiltKeys.SetStringItem(indy,2, '%3.2f' % max(y0, y1))

            self.bClipToSelection.SetLabel('Clear Clipping ROI')

        self.RegenFilter()

    def OnFilterAdd(self, event):
        #key = self.lFiltKeys.GetItem(self.currentFilterItem).GetText()

        possibleKeys = []
        if not self.selectedDataSource == None:
            possibleKeys = self.selectedDataSource.keys()

        dlg = editFilterDialog.FilterEditDialog(self, mode='new', possibleKeys=possibleKeys)

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            minVal = float(dlg.tMin.GetValue())
            maxVal = float(dlg.tMax.GetValue())

            key = dlg.cbKey.GetValue().encode()

            if key == "":
                return

            self.filterKeys[key] = (minVal, maxVal)

            ind = self.lFiltKeys.InsertStringItem(sys.maxint, key)
            self.lFiltKeys.SetStringItem(ind,1, '%3.2f' % minVal)
            self.lFiltKeys.SetStringItem(ind,2, '%3.2f' % maxVal)

        dlg.Destroy()

        self.RegenFilter()

    def OnFilterDelete(self, event):
        it = self.lFiltKeys.GetItem(self.currentFilterItem)
        self.lFiltKeys.DeleteItem(self.currentFilterItem)
        self.filterKeys.pop(it.GetText())

        self.RegenFilter()
        
    def OnFilterEdit(self, event):
        key = self.lFiltKeys.GetItem(self.currentFilterItem).GetText()

        #dlg = editFilterDialog.FilterEditDialog(self, mode='edit', possibleKeys=[], key=key, minVal=self.filterKeys[key][0], maxVal=self.filterKeys[key][1])
        dlg = histLimits.HistLimitDialog(self, self.selectedDataSource[key], self.filterKeys[key][0], self.filterKeys[key][1], title=key)
        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            #minVal = float(dlg.tMin.GetValue())
            #maxVal = float(dlg.tMax.GetValue())
            minVal, maxVal = dlg.GetLimits()

            self.filterKeys[key] = (minVal, maxVal)

            self.lFiltKeys.SetStringItem(self.currentFilterItem,1, '%3.2f' % minVal)
            self.lFiltKeys.SetStringItem(self.currentFilterItem,2, '%3.2f' % maxVal)

        dlg.Destroy()
        self.RegenFilter()

    
    def GenQuadTreePanel(self):
        item = afp.foldingPane(self._pnl, -1, caption="QuadTree", pinned = True)
#        item = self._pnl.AddFoldPanel("QuadTree", collapsed=False,
#                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)
        bsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Leaf Size:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tQTLeafSize = wx.TextCtrl(pan, -1, '%d' % pointQT.QT_MAXRECORDS)
        hsizer.Add(self.tQTLeafSize, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL, 0)

        self.stQTSNR = wx.StaticText(pan, -1, 'Effective SNR = %3.2f' % pylab.sqrt(pointQT.QT_MAXRECORDS/2.0))
        bsizer.Add(self.stQTSNR, 0, wx.ALL, 5)

        #hsizer = wx.BoxSizer(wx.HORIZONTAL)
        #hsizer.Add(wx.StaticText(pan, -1, 'Goal pixel size [nm]:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        #self.tQTSize = wx.TextCtrl(pan, -1, '20000')
        #hsizer.Add(self.tQTLeafSize, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        #bsizer.Add(hsizer, 0, wx.ALL, 0)
        
        pan.SetSizer(bsizer)
        bsizer.Fit(pan)

        
        item.AddNewElement(pan)
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        self.tQTLeafSize.Bind(wx.EVT_TEXT, self.OnQTLeafChange)

        self._pnl.AddPane(item)

    

    def OnQTLeafChange(self, event):
        leafSize = int(self.tQTLeafSize.GetValue())
        if not leafSize >= 1:
            raise 'QuadTree leaves must be able to contain at least 1 item'

        pointQT.QT_MAXRECORDS = leafSize
        self.stQTSNR.SetLabel('Effective SNR = %3.2f' % pylab.sqrt(pointQT.QT_MAXRECORDS/2.0))

        self.Quads = None
        self.RefreshView()


    def GenBlobPanel(self):
#        item = self._pnl.AddFoldPanel("Objects", collapsed=False,
#                                      foldIcons=self.Images)
        item = afp.foldingPane(self._pnl, -1, caption="Objects", pinned = True)

        pan = wx.Panel(item, -1)
        bsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Threshold [nm]:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tBlobDist = wx.TextCtrl(pan, -1, '%3.0f' % self.objThreshold,size=(40,-1))
        hsizer.Add(self.tBlobDist, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Min Size [events]:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tMinObjSize = wx.TextCtrl(pan, -1, '%d' % self.objMinSize, size=(40, -1))
        hsizer.Add(self.tMinObjSize, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Jittering:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tObjJitter = wx.TextCtrl(pan, -1, '%d' % self.blobJitter, size=(40, -1))
        hsizer.Add(self.tObjJitter, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        self.bApplyThreshold = wx.Button(pan, -1, 'Apply')
        bsizer.Add(self.bApplyThreshold, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)

        self.bObjMeasure = wx.Button(pan, -1, 'Measure')
        #self.bObjMeasure.Enable(False)
        bsizer.Add(self.bObjMeasure, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Object Colour:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.cBlobColour = wx.Choice(pan, -1, choices=['Index', 'Random'])
        self.cBlobColour.SetSelection(0)
        self.cBlobColour.Bind(wx.EVT_CHOICE, self.OnSetBlobColour)

        hsizer.Add(self.cBlobColour, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        pan.SetSizer(bsizer)
        bsizer.Fit(pan)


        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)
        item.AddNewElement(pan)

        self.bApplyThreshold.Bind(wx.EVT_BUTTON, self.OnObjApplyThreshold)
        self.bObjMeasure.Bind(wx.EVT_BUTTON, self.OnObjMeasure)

        self._pnl.AddPane(item)

    def OnSetBlobColour(self, event):
        bcolour = self.cBlobColour.GetStringSelection()

        if bcolour == 'Index':
            c = self.objCInd.astype('f')
        elif bcolour == 'Random':
            r = pylab.rand(self.objCInd.max() + 1)
            c = r[self.objCInd.astype('i')]
        else:
            c = self.objectMeasures[bcolour][self.objCInd.astype('i')]

        self.glCanvas.c = c
        self.glCanvas.setColour()
        self.OnGLViewChanged()
        
        self.hlCLim.SetData(self.glCanvas.c, self.glCanvas.clim[0], self.glCanvas.clim[1])

    def OnObjApplyThreshold(self, event):
        self.objects = None
        self.objThreshold = float(self.tBlobDist.GetValue())
        self.objMinSize = int(self.tMinObjSize.GetValue())
        self.blobJitter = int(self.tObjJitter.GetValue())

        #self.bObjMeasure.Enable(True)

        self.RefreshView()

    def OnObjMeasure(self, event):
        self.objectMeasures = objectMeasure.measureObjects(self.objects, self.objThreshold)
        if self.rav == None:
            self.rav = recArrayView.recArrayPanel(self.notebook, self.objectMeasures)
            self.notebook.AddPage(self.rav, 'Measurements')
        else:
            self.rav.grid.SetData(self.objectMeasures)

        self.cBlobColour.Clear()
        self.cBlobColour.Append('Index')

        for n in self.objectMeasures.dtype.names:
            self.cBlobColour.Append(n)

        self.RefreshView()


    def GenPointsPanel(self, title='Points'):
        item = afp.foldingPane(self._pnl, -1, caption=title, pinned = True)
#        item = self._pnl.AddFoldPanel(title, collapsed=False,
#                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)
        bsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Size [nm]:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tPointSize = wx.TextCtrl(pan, -1, '%3.2f' % self.glCanvas.pointSize)
        hsizer.Add(self.tPointSize, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL, 0)

        
        colData = ['<None>']

        if not self.colourFilter == None:
            colData += self.colourFilter.keys()

        colData += self.GeneratedMeasures.keys()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Colour:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.chPointColour = wx.Choice(pan, -1, choices=colData, size=(100, -1))
        if self.colData in colData:
            self.chPointColour.SetSelection(colData.index(self.colData))
        hsizer.Add(self.chPointColour, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL, 0)
        
        pan.SetSizer(bsizer)
        bsizer.Fit(pan)

        item.AddNewElement(pan)
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        self.tPointSize.Bind(wx.EVT_TEXT, self.OnPointSizeChange)
        self.chPointColour.Bind(wx.EVT_CHOICE, self.OnChangePointColour)

        self._pnl.AddPane(item)

    def UpdatePointColourChoices(self):
        if self.viewMode == 'points': #only change if we are in points mode
            colData = ['<None>']

            if not self.colourFilter == None:
                colData += self.colourFilter.keys()

            colData += self.GeneratedMeasures.keys()

            self.chPointColour.Clear()
            for cd in colData:
                self.chPointColour.Append(cd)

            if self.colData in colData:
                self.chPointColour.SetSelection(colData.index(self.colData))

    def OnPointSizeChange(self, event):
        self.glCanvas.pointSize = float(self.tPointSize.GetValue())
        self.glCanvas.Refresh()

    def OnChangePointColour(self, event):
        self.colData = event.GetString()
        
        self.RefreshView()

    def pointColour(self):
        pointColour = None
        
        if self.colData == '<None>':
            pointColour = None
        elif not self.colourFilter == None:
            if self.colData in self.colourFilter.keys():
                pointColour = self.colourFilter[self.colData]
            elif self.colData in self.GeneratedMeasures.keys():
                pointColour = self.GeneratedMeasures[self.colData]
            else:
                pointColour = None

        return pointColour

    def GenDriftPanel(self):
        item = afp.foldingPane(self._pnl, -1, caption="Drift Correction", pinned = False)
#        item = self._pnl.AddFoldPanel("Drift Correction", collapsed=True,
#                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)
        bsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, "x' = "), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tXExpr = wx.TextCtrl(pan, -1, self.driftExprX, size=(130, -1))
        hsizer.Add(self.tXExpr, 2,wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 5)

        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, "y' = "), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tYExpr = wx.TextCtrl(pan, -1, self.driftExprY, size=(130,-1))
        hsizer.Add(self.tYExpr, 2,wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 5)
        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, "z' = "), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tZExpr = wx.TextCtrl(pan, -1, self.driftExprZ, size=(100,-1))
        self.tZExpr.Enable(False)
        hsizer.Add(self.tZExpr, 2,wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 5)
       
        self.cbDriftFitZ = wx.CheckBox(pan, -1, 'Fit')
        hsizer.Add(self.cbDriftFitZ, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        #bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        bDriftBruteZ = wx.Button(pan, -1, 'BF', style=wx.BU_EXACTFIT)
        hsizer.Add(bDriftBruteZ, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)
        

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, "Presets:"), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.cDriftPresets = wx.Choice(pan, -1, choices=['', 'Linear', 'Piecewise Linear'], size=(120,-1))
        hsizer.Add(self.cDriftPresets, 2,wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 5)

        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

       

        pan.SetSizer(bsizer)
        bsizer.Fit(pan)


        item.AddNewElement(pan)
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        self.tXExpr.Bind(wx.EVT_TEXT, self.OnDriftExprChange)
        self.tYExpr.Bind(wx.EVT_TEXT, self.OnDriftExprChange)
        self.tZExpr.Bind(wx.EVT_TEXT, self.OnDriftExprChange)
        self.cbDriftFitZ.Bind(wx.EVT_CHECKBOX, self.OnDriftZToggle)
        self.cDriftPresets.Bind(wx.EVT_CHOICE, self.OnDriftPreset)


        self.lDriftParams = editList.EditListCtrl(item, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.SUNKEN_BORDER, size=(-1, 100))

        item.AddNewElement(self.lDriftParams)
        #self._pnl.AddFoldPanelWindow(item, self.lDriftParams, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        self.lDriftParams.InsertColumn(0, 'Parameter')
        self.lDriftParams.InsertColumn(1, 'Value')

        self.lDriftParams.makeColumnEditable(1)

        #self.RefreshDriftParameters()

        self.OnDriftExprChange()

        self.lDriftParams.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnDriftParameterChange)

        pan = wx.Panel(item, -1)
        bsizer = wx.BoxSizer(wx.VERTICAL)

        bZero = wx.Button(pan, -1, 'Zero Parameters', style=wx.BU_EXACTFIT)
        bsizer.Add(bZero, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        bFit = wx.Button(pan, -1, 'Fit', size=(30,-1))
        hsizer.Add(bFit, 0,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        bPlot = wx.Button(pan, -1, 'Plt', size=(30,-1))
        hsizer.Add(bPlot, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bApply = wx.Button(pan, -1, 'Apply', size=(50,-1))
        hsizer.Add(bApply, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bRevert = wx.Button(pan, -1, 'Revert', size=(50,-1))
        hsizer.Add(bRevert, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bsizer.Add(hsizer, 0, wx.ALL|wx.EXPAND, 0)

        

        pan.SetSizer(bsizer)
        bsizer.Fit(pan)

        item.AddNewElement(pan)
        #self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        bFit.Bind(wx.EVT_BUTTON, self.OnDriftFit)
        bApply.Bind(wx.EVT_BUTTON, self.OnDriftApply)
        bRevert.Bind(wx.EVT_BUTTON, self.OnDriftRevert)
        bPlot.Bind(wx.EVT_BUTTON, self.OnDriftPlot)
        bZero.Bind(wx.EVT_BUTTON, self.OnDriftZeroParams)
        bDriftBruteZ.Bind(wx.EVT_BUTTON, self.OnDriftZBruteForce)


        self._pnl.AddPane(item)

    def OnDriftFit(self, event):
        self.driftCorrParams.update(intelliFit.doFitT(self.driftCorrFcn, self.driftCorrParams, self.filter, self.fitZDrift, self.optimiseFcn))
        self.RefreshDriftParameters()

    def OnDriftZBruteForce(self, event):
        self.driftCorrParams.update(intelliFit.bruteForceZ(self.driftCorrFcn, self.driftCorrParams, self.filter))
        self.RefreshDriftParameters()

    def OnDriftZeroParams(self, event):
        for p in self.driftCorrFcn[0] + self.driftCorrFcn[-3]:
            self.driftCorrParams[p] = 0
        
        self.RefreshDriftParameters()

    def OnDriftPreset(self, event):
        sel = self.cDriftPresets.GetStringSelection()
        driftExprX = self.driftExprX
        driftExprY = self.driftExprY

        if sel == 'Linear':
            driftExprX = 'x + a*t'
            driftExprY = 'y + b*t'
        elif sel == 'Piecewise Linear':
            dlg = wx.TextEntryDialog(self, 'Please enter number of segments', 'Piecewise Linear', '5')
            if dlg.ShowModal() == wx.ID_OK:
                nSegs = int(dlg.GetValue())

                #generate segments evenly spaced in point density
                t = self.colourFilter['t'].copy()
                t.sort()
                tvals = t[np.linspace(0, len(t)-1, nSegs+1).astype('i')][1:-1]

                stvals = '[' + ', '.join(['%1.1e' % tv for tv in tvals]) + ']'
                sgxvals = '[' + ', '.join(['a%d' % i for i in range(nSegs)]) + ']'
                sgyvals = '[' + ', '.join(['b%d' % i for i in range(nSegs)]) + ']'

                driftExprX = 'x + piecewiseLinear(t, %s, %s)' % (stvals, sgxvals)
                driftExprY = 'y + piecewiseLinear(t, %s, %s)' % (stvals, sgyvals)

        self.tXExpr.SetValue(driftExprX)
        self.tYExpr.SetValue(driftExprY)

        self.cDriftPresets.SetSelection(0)

#        if self.filter == None:
#            filtKeys = []
#        else:
#            filtKeys = self.filter.keys()
#
#        self.driftCorrFcn = intelliFit.genFcnCodeT(self.driftExprX,self.driftExprY, filtKeys)
#
#        #self.driftCorrParams = {}
#        for p in self.driftCorrFcn[0]:
#            if not p in self.driftCorrParams.keys():
#                self.driftCorrParams[p] = 0
#
#        self.RefreshDriftParameters()

    def OnDriftApply(self, event):
        self.mapping.setMapping('x', self.driftCorrFcn[2])
        self.mapping.setMapping('y', self.driftCorrFcn[3])

        if True: #self.fitZDrift:
            self.mapping.setMapping('z', self.driftCorrFcn[4])

        self.mapping.__dict__.update(self.driftCorrParams)

        self.Triangles = None
        self.edb = None
        self.GeneratedMeasures = {}
        self.Quads = None
        
        self.RefreshView()

    def OnDriftRevert(self, event):
        self.mapping.mappings.pop('x')
        self.mapping.mappings.pop('y')
        if 'z' in self.mapping.mappings.keys():
            self.mapping.mappings.pop('z')

        self.Triangles = None
        self.edb = None
        self.GeneratedMeasures = {}
        self.Quads = None

        self.RefreshView()

    def OnDriftPlot(self, event):
        intelliFit.plotDriftResultT(self.driftCorrFcn, self.driftCorrParams, self.filter)

    def OnDriftZToggle(self, event=None):
        self.fitZDrift = self.cbDriftFitZ.GetValue()
        self.tZExpr.Enable(self.fitZDrift)

    def OnDriftExprChange(self, event=None):
        self.driftExprX = self.tXExpr.GetValue()
        self.driftExprY = self.tYExpr.GetValue()
        self.driftExprZ = self.tZExpr.GetValue()
        if self.filter == None:
            filtKeys = []
        else:
            filtKeys = self.filter.keys()

        self.driftCorrFcn = intelliFit.genFcnCodeT(self.driftExprX,self.driftExprY,self.driftExprZ, filtKeys)

        #self.driftCorrParams = {}
        for p in self.driftCorrFcn[0]+ self.driftCorrFcn[-3]:
            if not p in self.driftCorrParams.keys():
                self.driftCorrParams[p] = 0

        self.RefreshDriftParameters()

    def OnDriftParameterChange(self, event=None):
        parameterNames = self.driftCorrFcn[0] + self.driftCorrFcn[-3]

        pn = parameterNames[event.m_itemIndex]

        self.driftCorrParams[pn] = float(event.m_item.GetText())

    def RefreshDriftParameters(self):
        parameterNames = self.driftCorrFcn[0] + self.driftCorrFcn[-3]

        self.lDriftParams.DeleteAllItems()

        for pn in parameterNames:
            ind = self.lDriftParams.InsertStringItem(sys.maxint, pn)
            self.lDriftParams.SetStringItem(ind,1, '%1.3g' % self.driftCorrParams[pn])

        self.lDriftParams.SetColumnWidth(0, 80)
        self.lDriftParams.SetColumnWidth(1, 80)

    def CreateMenuBar(self):

        # Make a menubar
        file_menu = wx.Menu()

        ID_OPEN = wx.ID_OPEN
        ID_SAVE_MEASUREMENTS = wx.ID_SAVE
        ID_QUIT = wx.ID_EXIT

        ID_OPEN_RAW = wx.NewId()
        ID_OPEN_CHANNEL = wx.NewId()

        ID_VIEW_POINTS = wx.NewId()
        ID_VIEW_TRIANGS = wx.NewId()
        ID_VIEW_QUADS = wx.NewId()

        ID_VIEW_BLOBS = wx.NewId()

        ID_VIEW_VORONOI = wx.NewId()
        ID_VIEW_INTERP_TRIANGS = wx.NewId()

        ID_VIEW_FIT = wx.NewId()
        ID_VIEW_FIT_ROI = wx.NewId()
        
        ID_GEN_JIT_TRI = wx.NewId()
        ID_GEN_QUADS = wx.NewId()

        ID_GEN_GAUSS = wx.NewId()
        ID_GEN_HIST = wx.NewId()

        ID_GEN_3DHIST = wx.NewId()
        ID_GEN_3DGAUSS = wx.NewId()
        ID_GEN_3DTRI = wx.NewId()

        ID_GEN_CURRENT = wx.NewId()

        ID_TOGGLE_SETTINGS = wx.NewId()

        ID_GEN_SHIFTMAP = wx.NewId()
        ID_CORR_DRIFT = wx.NewId()
        ID_EXT_DRIFT = wx.NewId()
        ID_TRACK_MOLECULES = wx.NewId()
        ID_CALC_DECAYS = wx.NewId()
        ID_PLOT_TEMPERATURE = wx.NewId()
        ID_POINT_COLOC = wx.NewId()

        ID_ABOUT = wx.ID_ABOUT

        ID_VIEW_3D_POINTS = wx.NewId()
        ID_VIEW_3D_TRIANGS = wx.NewId()
        ID_VIEW_3D_BLOBS = wx.NewId()

        ID_VIEW_BLOBS = wx.NewId()
        
        
        file_menu.Append(ID_OPEN, "&Open")
        file_menu.Append(ID_OPEN_RAW, "Open &Raw/Prebleach Data")
        file_menu.Append(ID_OPEN_CHANNEL, "Open Extra &Channel")
        
        file_menu.AppendSeparator()
        file_menu.Append(ID_SAVE_MEASUREMENTS, "&Save Measurements")

        file_menu.AppendSeparator()
        
        file_menu.Append(ID_QUIT, "&Exit")

        self.view_menu = wx.Menu()

        try: #stop us bombing on Mac
            self.view_menu.AppendRadioItem(ID_VIEW_POINTS, '&Points')
            self.view_menu.AppendRadioItem(ID_VIEW_TRIANGS, '&Triangles')
            self.view_menu.AppendRadioItem(ID_VIEW_QUADS, '&Quad Tree')
            self.view_menu.AppendRadioItem(ID_VIEW_VORONOI, '&Voronoi')
            self.view_menu.AppendRadioItem(ID_VIEW_INTERP_TRIANGS, '&Interpolated Triangles')
            self.view_menu.AppendRadioItem(ID_VIEW_BLOBS, '&Blobs')
        except:
            self.view_menu.Append(ID_VIEW_POINTS, '&Points')
            self.view_menu.Append(ID_VIEW_TRIANGS, '&Triangles')
            self.view_menu.Append(ID_VIEW_QUADS, '&Quad Tree')
            self.view_menu.Append(ID_VIEW_VORONOI, '&Voronoi')
            self.view_menu.Append(ID_VIEW_INTERP_TRIANGS, '&Interpolated Triangles')
            self.view_menu.Append(ID_VIEW_BLOBS, '&Blobs')

        self.view_menu.Check(ID_VIEW_POINTS, True)
        #self.view_menu.Enable(ID_VIEW_QUADS, False)

        self.view_menu.AppendSeparator()
        self.view_menu.Append(ID_VIEW_FIT, '&Fit')
        self.view_menu.Append(ID_VIEW_FIT_ROI, 'Fit &ROI')

        self.view_menu.AppendSeparator()
        self.view_menu.AppendCheckItem(ID_TOGGLE_SETTINGS, "Show Settings")
        self.view_menu.Check(ID_TOGGLE_SETTINGS, True)

        self.view3d_menu = wx.Menu()

#        try: #stop us bombing on Mac
#            self.view3d_menu.AppendRadioItem(ID_VIEW_3D_POINTS, '&Points')
#            self.view3d_menu.AppendRadioItem(ID_VIEW_3D_TRIANGS, '&Triangles')
#            self.view3d_menu.AppendRadioItem(ID_VIEW_3D_BLOBS, '&Blobs')
#        except:
        self.view3d_menu.Append(ID_VIEW_3D_POINTS, '&Points')
        self.view3d_menu.Append(ID_VIEW_3D_TRIANGS, '&Triangles')
        self.view3d_menu.Append(ID_VIEW_3D_BLOBS, '&Blobs')

        #self.view3d_menu.Enable(ID_VIEW_3D_TRIANGS, False)
        self.view3d_menu.Enable(ID_VIEW_3D_BLOBS, False)

        #self.view_menu.Check(ID_VIEW_3D_POINTS, True)

        gen_menu = wx.Menu()
        gen_menu.Append(ID_GEN_CURRENT, "&Current")
        
        gen_menu.AppendSeparator()
        gen_menu.Append(ID_GEN_GAUSS, "&Gaussian")
        gen_menu.Append(ID_GEN_HIST, "&Histogram")

        gen_menu.AppendSeparator()
        gen_menu.Append(ID_GEN_JIT_TRI, "&Triangulation")
        gen_menu.Append(ID_GEN_QUADS, "&QuadTree")

        gen_menu.AppendSeparator()
        gen_menu.Append(ID_GEN_3DHIST, "3D Histogram")
        gen_menu.Append(ID_GEN_3DGAUSS, "3D Gaussian")
        gen_menu.Append(ID_GEN_3DTRI, "3D Triangulation")

        special_menu = wx.Menu()
        special_menu.Append(ID_GEN_SHIFTMAP, "Calculate &Shiftmap")
        special_menu.Append(ID_CORR_DRIFT, "Estimate drift using cross-correlation")
        special_menu.Append(ID_EXT_DRIFT, "Plot externally calculated drift trajectory")
        special_menu.Append(ID_TRACK_MOLECULES, "&Track single molecule trajectories")
        special_menu.Append(ID_CALC_DECAYS, "Estimate decay lifetimes")
        special_menu.Append(ID_PLOT_TEMPERATURE, "Plot temperature record")
        special_menu.Append(ID_POINT_COLOC, "Pointwise Colocalisation")

        help_menu = wx.Menu()
        help_menu.Append(ID_ABOUT, "&About")

        menu_bar = wx.MenuBar()

        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(self.view_menu, "&View")
        menu_bar.Append(gen_menu, "&Generate Image")
        menu_bar.Append(special_menu, "&Extras")
        menu_bar.Append(self.view3d_menu, "View &3D")
       
        

            
        menu_bar.Append(help_menu, "&Help")

        self.Bind(wx.EVT_MENU, self.OnAbout, id=ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=ID_QUIT)
        self.Bind(wx.EVT_MENU, self.OnToggleWindow, id=ID_TOGGLE_SETTINGS)

        self.Bind(wx.EVT_MENU, self.OnOpenFile, id=ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnOpenChannel, id=ID_OPEN_CHANNEL)
        self.Bind(wx.EVT_MENU, self.OnOpenRaw, id=ID_OPEN_RAW)

        self.Bind(wx.EVT_MENU, self.OnSaveMeasurements, id=ID_SAVE_MEASUREMENTS)

        self.Bind(wx.EVT_MENU, self.OnViewPoints, id=ID_VIEW_POINTS)
        self.Bind(wx.EVT_MENU, self.OnViewTriangles, id=ID_VIEW_TRIANGS)
        self.Bind(wx.EVT_MENU, self.OnViewQuads, id=ID_VIEW_QUADS)
        self.Bind(wx.EVT_MENU, self.OnViewVoronoi, id=ID_VIEW_VORONOI)
        self.Bind(wx.EVT_MENU, self.OnViewInterpTriangles, id=ID_VIEW_INTERP_TRIANGS)

        self.Bind(wx.EVT_MENU, self.OnViewBlobs, id=ID_VIEW_BLOBS)

        self.Bind(wx.EVT_MENU, self.SetFit, id=ID_VIEW_FIT)
        self.Bind(wx.EVT_MENU, self.OnFitROI, id=ID_VIEW_FIT_ROI)

        self.Bind(wx.EVT_MENU, self.OnGenCurrent, id=ID_GEN_CURRENT)
        self.Bind(wx.EVT_MENU, self.OnGenTriangles, id=ID_GEN_JIT_TRI)
        self.Bind(wx.EVT_MENU, self.OnGenGaussian, id=ID_GEN_GAUSS)
        self.Bind(wx.EVT_MENU, self.OnGenHistogram, id=ID_GEN_HIST)
        self.Bind(wx.EVT_MENU, self.OnGenQuadTree, id=ID_GEN_QUADS)

        self.Bind(wx.EVT_MENU, self.OnGen3DHistogram, id=ID_GEN_3DHIST)
        self.Bind(wx.EVT_MENU, self.OnGen3DGaussian, id=ID_GEN_3DGAUSS)
        self.Bind(wx.EVT_MENU, self.OnGen3DTriangles, id=ID_GEN_3DTRI)

        self.Bind(wx.EVT_MENU, self.OnGenShiftmap, id=ID_GEN_SHIFTMAP)
        self.Bind(wx.EVT_MENU, self.OnCalcCorrDrift, id=ID_CORR_DRIFT)
        self.Bind(wx.EVT_MENU, self.OnPlotExtDrift, id=ID_EXT_DRIFT)
        self.Bind(wx.EVT_MENU, self.OnTrackMolecules, id=ID_TRACK_MOLECULES)
        self.Bind(wx.EVT_MENU, self.OnCalcDecays, id=ID_CALC_DECAYS)
        self.Bind(wx.EVT_MENU, self.OnPlotTemperature, id=ID_PLOT_TEMPERATURE)
        self.Bind(wx.EVT_MENU, self.OnPointwiseColoc, id=ID_POINT_COLOC)

        self.Bind(wx.EVT_MENU, self.OnView3DPoints, id=ID_VIEW_3D_POINTS)
        self.Bind(wx.EVT_MENU, self.OnView3DTriangles, id=ID_VIEW_3D_TRIANGS)
        #self.Bind(wx.EVT_MENU, self.OnView3DBlobs, id=ID_VIEW_3D_BLOBS)

        return menu_bar

    def OnViewPoints(self,event):
        self.viewMode = 'points'
        #self.glCanvas.cmap = pylab.cm.hsv
        self.RefreshView()
        self.CreateFoldPanel()
        self.OnPercentileCLim(None)

    def OnViewBlobs(self,event):
        self.viewMode = 'blobs'
        self.RefreshView()
        self.CreateFoldPanel()
        #self.OnPercentileCLim(None)

    def OnViewTriangles(self,event):
        self.viewMode = 'triangles'
        self.RefreshView()
        self.CreateFoldPanel()
        self.OnPercentileCLim(None)

    def OnViewQuads(self,event):
        self.viewMode = 'quads'
        self.RefreshView()
        self.CreateFoldPanel()
        self.OnPercentileCLim(None)

    def OnViewVoronoi(self,event):
        self.viewMode = 'voronoi'
        self.RefreshView()
        self.CreateFoldPanel()
        self.OnPercentileCLim(None)

    def OnViewInterpTriangles(self,event):
        self.viewMode = 'interp_triangles'
        self.RefreshView()
        self.CreateFoldPanel()
        self.OnPercentileCLim(None)

    def OnView3DPoints(self,event):
        #self.viewMode = 'points'
        #self.glCanvas.cmap = pylab.cm.hsv
        #self.RefreshView()
        #self.CreateFoldPanel()
        #self.OnPercentileCLim(None)
        if 'z' in self.colourFilter.keys():
            if not 'glCanvas3D' in dir(self):
                self.glCanvas3D = gl_render3D.LMGLCanvas(self.notebook)
                self.notebook.AddPage(page=self.glCanvas3D, select=True, caption='3D')

            self.glCanvas3D.setPoints(self.colourFilter['x'], self.colourFilter['y'], self.colourFilter['z'], self.pointColour())
            self.glCanvas3D.setCLim(self.glCanvas.clim, (-5e5, -5e5))

    def OnView3DTriangles(self,event):
        #self.viewMode = 'points'
        #self.glCanvas.cmap = pylab.cm.hsv
        #self.RefreshView()
        #self.CreateFoldPanel()
        #self.OnPercentileCLim(None)
        if 'z' in self.colourFilter.keys():
            if not 'glCanvas3D' in dir(self):
                self.glCanvas3D = gl_render3D.LMGLCanvas(self.notebook)
                self.notebook.AddPage(page=self.glCanvas3D, select=True, caption='3D')

            self.glCanvas3D.setTriang(self.colourFilter['x'], self.colourFilter['y'], self.colourFilter['z'], 'z', sizeCutoff=self.glCanvas3D.edgeThreshold)
            self.glCanvas3D.setCLim(self.glCanvas3D.clim, (0, 5e-5))

    def OnGenCurrent(self, event):
        dlg = genImageDialog.GenImageDialog(self, mode='current')

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()
            
            bCurr = wx.BusyCursor()

            oldcmap = self.glCanvas.cmap 
            self.glCanvas.setCMap(pylab.cm.gray)

            
            im = self.glCanvas.getIm(pixelSize)

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)

            img = GeneratedImage(im,imb, pixelSize )
            imf = imageView.ImageViewFrame(self,img, self.glCanvas)
            self.generatedImages.append(imf)
            imf.Show()

            self.glCanvas.setCMap(oldcmap)
            self.RefreshView()

        dlg.Destroy()

    def genNeighbourDists(self, forceRetriang = False):
        bCurr = wx.BusyCursor()

        if self.Triangles == None or forceRetriang:
                statTri = statusLog.StatusLogger("Generating Triangulation ...")
                self.Triangles = delaunay.Triangulation(self.colourFilter['x'] + .1*np.random.normal(size=len(self.colourFilter['x'])), self.colourFilter['y']+ .1*np.random.normal(size=len(self.colourFilter['x'])))

        statNeigh = statusLog.StatusLogger("Calculating mean neighbour distances ...")
        self.GeneratedMeasures['neighbourDistances'] = pylab.array(visHelpers.calcNeighbourDists(self.Triangles))
        

    def OnGenTriangles(self, event): 
        jitVars = ['1.0']

        #if not 'neighbourDistances' in self.GeneratedMeasures.keys():
        #    self.genNeighbourDists()

        genMeas = self.GeneratedMeasures.keys()
        if not 'neighbourDistances' in genMeas:
            genMeas.append('neighbourDistances')

        jitVars += genMeas
        jitVars += self.colourFilter.keys()
        
        dlg = genImageDialog.GenImageDialog(self, mode='triangles', jitterVariables = jitVars, jitterVarDefault=genMeas.index('neighbourDistances')+1, colours=self.fluorSpecies.keys())

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            bCurr = wx.BusyCursor()
            pixelSize = dlg.getPixelSize()
            jitParamName = dlg.getJitterVariable()
            jitScale = dlg.getJitterScale()
            
            

            oldcmap = self.glCanvas.cmap 
            self.glCanvas.setCMap(pylab.cm.gray)

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            #imb = ImageBounds(x0, y0, x1, y1)

            status = statusLog.StatusLogger('Generating Triangulated Image ...')

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []

            for c in  colours:
                self.colourFilter.setColour(c)

                if jitParamName == '1.0':
                    jitVals = 1.0
                elif jitParamName in self.colourFilter.keys():
                    jitVals = self.colourFilter[jitParamName]
                elif jitParamName in genMeas:
                    if jitParamName == 'neighbourDistances':
                        self.genNeighbourDists(True)
                    jitVals = self.GeneratedMeasures[jitParamName]

                #print jitScale
                #print jitVals
                jitVals = jitScale*jitVals

                #print jitParamName, len(jitVals), len(self.colourFilter['x'])

                if dlg.getSoftRender():
                    status = statusLog.StatusLogger("Rendering triangles ...")
                    im = visHelpers.rendJitTriang(self.colourFilter['x'],self.colourFilter['y'], dlg.getNumSamples(), jitVals, dlg.getMCProbability(),imb, pixelSize)
                else:
                    im = self.glCanvas.genJitTim(dlg.getNumSamples(),self.colourFilter['x'],self.colourFilter['y'], jitVals, dlg.getMCProbability(),pixelSize)

                ims.append(GeneratedImage(im,imb, pixelSize ))

            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Jittered Triangulation - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()

            self.colourFilter.setColour(oldC)

            self.glCanvas.setCMap(oldcmap)
            self.RefreshView()

        dlg.Destroy()

    def OnGenGaussian(self, event):
        bCurr = wx.BusyCursor()
        jitVars = ['1.0']

        jitVars += self.colourFilter.keys()
        jitVars += self.GeneratedMeasures.keys()

        if 'error_x' in self.colourFilter.keys():
            jvd = self.colourFilter.keys().index('error_x')+1
        else:
            jvd = 0
        
        dlg = genImageDialog.GenImageDialog(self, mode='gaussian', jitterVariables = jitVars, jitterVarDefault=jvd, colours=self.fluorSpecies.keys())

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()
            jitParamName = dlg.getJitterVariable()
            jitScale = dlg.getJitterScale()
            
            

            status = statusLog.StatusLogger('Generating Gaussian Image ...')

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []


            for c in  colours:
                self.colourFilter.setColour(c)

                if jitParamName == '1.0':
                    jitVals = 1.0
                elif jitParamName in self.colourFilter.keys():
                    jitVals = self.colourFilter[jitParamName]
                elif jitParamName in self.GeneratedMeasures.keys():
                    if jitParamName == 'neighbourDistances':
                        self.genNeighbourDists()
                    jitVals = self.GeneratedMeasures[jitParamName]

                #print jitScale
                #print jitVals
                jitVals = jitScale*jitVals

                im = visHelpers.rendGauss(self.colourFilter['x'],self.colourFilter['y'], jitVals, imb, pixelSize)

                ims.append(GeneratedImage(im,imb, pixelSize ))
                
            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Gaussian Rendering - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()
            
            self.colourFilter.setColour(oldC)
            

        dlg.Destroy()

    def OnGenHistogram(self, event): 
        bCurr = wx.BusyCursor()
        dlg = genImageDialog.GenImageDialog(self, mode='histogram', colours=self.fluorSpecies.keys())

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()

            status = statusLog.StatusLogger('Generating Histogram Image ...')

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []

            for c in  colours:
                self.colourFilter.setColour(c)
                im = visHelpers.rendHist(self.colourFilter['x'],self.colourFilter['y'], imb, pixelSize)

                ims.append(GeneratedImage(im,imb, pixelSize ))

            #imfc = imageView.ColourImageViewFrame(self, self.glCanvas)

#            for im in ims:
#                img = GeneratedImage(im,imb, pixelSize )
#                imf = imageView.ImageViewFrame(self,img, self.glCanvas)
#                self.generatedImages.append(imf)
#                imf.Show()
#
#                imfc.ivp.ivps.append(imf.ivp)

            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Generated Histogram - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()

            self.colourFilter.setColour(oldC)

        dlg.Destroy()

    def OnGen3DHistogram(self, event):
        bCurr = wx.BusyCursor()

        dlg = genImageDialog.GenImageDialog(self, mode='3Dhistogram', colours=self.fluorSpecies.keys(), zvals = self.mapping['z'])

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()

            status = statusLog.StatusLogger('Generating Histogram Image ...')

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []

            for c in  colours:
                self.colourFilter.setColour(c)
                im = visHelpers.rendHist3D(self.colourFilter['x'],self.colourFilter['y'], self.colourFilter['z'], imb, pixelSize, dlg.getZBounds(), dlg.getZSliceThickness())

                ims.append(GeneratedImage(im,imb, pixelSize,  dlg.getZSliceThickness()))

            #imfc = imageView.ColourImageViewFrame(self, self.glCanvas)

#            for im in ims:
#                img = GeneratedImage(im,imb, pixelSize )
#                imf = imageView.ImageViewFrame(self,img, self.glCanvas)
#                self.generatedImages.append(imf)
#                imf.Show()
#
#                imfc.ivp.ivps.append(imf.ivp)

            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Generated 3D Histogram - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()

            self.colourFilter.setColour(oldC)

        dlg.Destroy()

    def OnGen3DGaussian(self, event):
        bCurr = wx.BusyCursor()

        jitVars = ['1.0']

        jitVars += self.colourFilter.keys()
        jitVars += self.GeneratedMeasures.keys()

        if 'error_x' in jitVars:
            jvi = jitVars.index('error_x')
        else:
            jvi = 0

        if 'fitError_z0' in jitVars:
            jvzi = jitVars.index('fitError_z0')
        else:
            jvzi = 0

        dlg = genImageDialog.GenImageDialog(self, mode='3Dgaussian', colours=self.fluorSpecies.keys(), zvals = self.mapping['z'], jitterVariables = jitVars, jitterVarDefault=jvi, jitterVarDefaultZ=jvzi)

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()
            jitParamName = dlg.getJitterVariable()
            jitScale = dlg.getJitterScale()
            jitParamNameZ = dlg.getJitterVariableZ()
            jitScaleZ = dlg.getJitterScaleZ()

            status = statusLog.StatusLogger('Generating 3D Gaussian Image ...')

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []

            for c in  colours:
                self.colourFilter.setColour(c)

                if jitParamName == '1.0':
                    jitVals = np.ones(self.colourFilter['x'].shape)
                elif jitParamName in self.colourFilter.keys():
                    jitVals = self.colourFilter[jitParamName]
                elif jitParamName in self.GeneratedMeasures.keys():
                    if jitParamName == 'neighbourDistances':
                        self.genNeighbourDists()
                    jitVals = self.GeneratedMeasures[jitParamName]

                if jitParamNameZ == '1.0':
                    jitValsZ = np.ones(self.colourFilter['x'].shape)
                elif jitParamNameZ in self.colourFilter.keys():
                    jitValsZ = self.colourFilter[jitParamName]
                elif jitParamNameZ in self.GeneratedMeasures.keys():
                    if jitParamNameZ == 'neighbourDistances':
                        self.genNeighbourDists()
                    jitValsZ = self.GeneratedMeasures[jitParamName]

                jitVals = jitScale*jitVals
                jitValsZ = jitScaleZ*jitValsZ

                im = visHelpers.rendGauss3D(self.colourFilter['x'],self.colourFilter['y'], self.colourFilter['z'], jitVals, jitValsZ, imb, pixelSize, dlg.getZBounds(), dlg.getZSliceThickness())

                ims.append(GeneratedImage(im,imb, pixelSize,  dlg.getZSliceThickness()))

            #imfc = imageView.ColourImageViewFrame(self, self.glCanvas)

#            for im in ims:
#                img = GeneratedImage(im,imb, pixelSize )
#                imf = imageView.ImageViewFrame(self,img, self.glCanvas)
#                self.generatedImages.append(imf)
#                imf.Show()
#
#                imfc.ivp.ivps.append(imf.ivp)

            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Generated 3D Histogram - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()

            self.colourFilter.setColour(oldC)

        dlg.Destroy()

    def OnGen3DTriangles(self, event):
        bCurr = wx.BusyCursor()

        jitVars = ['1.0']

        jitVars += self.colourFilter.keys()
        jitVars += self.GeneratedMeasures.keys()
        jitVars += ['neighbourDistances']

        if 'fitError_z0' in jitVars:
            jvzi = jitVars.index('fitError_z0')
        else:
            jvzi = 0

        dlg = genImageDialog.GenImageDialog(self, mode='3Dtriangles', colours=self.fluorSpecies.keys(), zvals = self.mapping['z'], jitterVariables = jitVars, jitterVarDefault=jitVars.index('neighbourDistances'), jitterVarDefaultZ=jvzi)

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()
            jitParamName = dlg.getJitterVariable()
            jitScale = dlg.getJitterScale()
            jitParamNameZ = dlg.getJitterVariableZ()
            jitScaleZ = dlg.getJitterScaleZ()

            status = statusLog.StatusLogger('Generating 3D Gaussian Image ...')

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []

            for c in  colours:
                self.colourFilter.setColour(c)

                if jitParamName == '1.0':
                    jitVals = np.ones(self.colourFilter['x'].shape)
                elif jitParamName in self.colourFilter.keys():
                    jitVals = self.colourFilter[jitParamName]
                else:
                    if jitParamName == 'neighbourDistances':
                        self.genNeighbourDists(True)

                    if jitParamName in self.GeneratedMeasures.keys():
                        jitVals = self.GeneratedMeasures[jitParamName]

                if jitParamNameZ == '1.0':
                    jitValsZ = np.ones(self.colourFilter['x'].shape)
                elif jitParamNameZ in self.colourFilter.keys():
                    jitValsZ = self.colourFilter[jitParamNameZ]
                else:
                    if jitParamNameZ == 'neighbourDistances':
                            self.genNeighbourDists(True)
                            
                    if jitParamNameZ in self.GeneratedMeasures.keys():
                        jitValsZ = self.GeneratedMeasures[jitParamNameZ]

                jitVals = jitScale*jitVals
                jitValsZ = jitScaleZ*jitValsZ

                im = visHelpers.rendJitTet(self.colourFilter['x'],self.colourFilter['y'], self.colourFilter['z'], dlg.getNumSamples(), jitVals, jitValsZ, dlg.getMCProbability(), imb, pixelSize, dlg.getZBounds(), dlg.getZSliceThickness())

                ims.append(GeneratedImage(im,imb, pixelSize,  dlg.getZSliceThickness()))

            #imfc = imageView.ColourImageViewFrame(self, self.glCanvas)

#            for im in ims:
#                img = GeneratedImage(im,imb, pixelSize )
#                imf = imageView.ImageViewFrame(self,img, self.glCanvas)
#                self.generatedImages.append(imf)
#                imf.Show()
#
#                imfc.ivp.ivps.append(imf.ivp)

            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Generated 3D Histogram - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()

            self.colourFilter.setColour(oldC)

        dlg.Destroy()

    def OnGenQuadTree(self, event):
        bCurr = wx.BusyCursor() 
        dlg = genImageDialog.GenImageDialog(self, mode='quadtree', colours=self.fluorSpecies.keys())

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            pixelSize = dlg.getPixelSize()

            status = statusLog.StatusLogger('Generating QuadTree Image ...')

            x0 = max(self.glCanvas.xmin, self.imageBounds.x0)
            y0 = max(self.glCanvas.ymin, self.imageBounds.y0)
            x1 = min(self.glCanvas.xmax, self.imageBounds.x1)
            y1 = min(self.glCanvas.ymax, self.imageBounds.y1)

            #imb = ImageBounds(self.glCanvas.xmin,self.glCanvas.ymin,self.glCanvas.xmax,self.glCanvas.ymax)
            imb = ImageBounds(x0, y0, x1, y1)
            

            if not pylab.mod(pylab.log2(pixelSize/self.QTGoalPixelSize), 1) == 0:#recalculate QuadTree to get right pixel size
                self.QTGoalPixelSize = pixelSize
                self.Quads = None
            
#            if self.Quads == None:
#                self.GenQuads()
#
#            qtWidth = self.Quads.x1 - self.Quads.x0
#
#            qtWidthPixels = pylab.ceil(qtWidth/pixelSize)

            colours =  dlg.getColour()
            oldC = self.colourFilter.currentColour

            ims = []

            for c in  colours:
                self.colourFilter.setColour(c)

                self.GenQuads()

                qtWidth = self.Quads.x1 - self.Quads.x0

                qtWidthPixels = pylab.ceil(qtWidth/pixelSize)

                im = pylab.zeros((qtWidthPixels, qtWidthPixels))

                QTrend.rendQTa(im, self.Quads)

                im = im[(imb.x0/pixelSize):(imb.x1/pixelSize),(imb.y0/pixelSize):(imb.y1/pixelSize)]

                ims.append(GeneratedImage(im,imb, pixelSize ))

            imfc = imageView.MultiChannelImageViewFrame(self, self.glCanvas, ims, colours, title='Generated QuadTree - %3.1fnm bins' % pixelSize)

            self.generatedImages.append(imfc)
            imfc.Show()
                
            self.colourFilter.setColour(oldC)

        dlg.Destroy()

    def OnGenShiftmap(self, event):
        from PYME.Analysis import twoColour, twoColourPlot
        lx = len(self.filter['x'])
        dx, dy, spx, spy = twoColour.genShiftVectorFieldSpline(self.filter['x']+.1*pylab.randn(lx), self.filter['y']+.1*pylab.randn(lx), self.filter['fitResults_dx'], self.filter['fitResults_dy'], self.filter['fitError_dx'], self.filter['fitError_dy'])
        twoColourPlot.PlotShiftField(dx, dy, spx, spy)

        import cPickle

        fdialog = wx.FileDialog(None, 'Save shift field as ...',
            wildcard='Shift Field file (*.sf)|*.sf', style=wx.SAVE|wx.HIDE_READONLY)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            fpath = fdialog.GetPath()
            #save as a pickle containing the data and voxelsize

            fid = open(fpath, 'wb')
            cPickle.dump((spx, spy), fid, 2)
            fid.close()

    def OnCalcDecays(self, event):
        from PYME.Analysis.BleachProfile import kinModels
        
        kinModels.fitDecay(self.colourFilter, self.mdh)
        kinModels.fitOnTimes(self.colourFilter, self.mdh)
        kinModels.fitFluorBrightness(self.colourFilter, self.mdh)

    def OnPlotTemperature(self, event):
        from PYME.misc import tempDB
        import pylab
        t, tm = tempDB.getEntries(self.mdh.getEntry('StartTime'), self.mdh.getEntry('EndTime'))
        t_, tm_ = tempDB.getEntries(self.mdh.getEntry('StartTime') - 3600, self.mdh.getEntry('EndTime'))

        pylab.figure()
        pylab.plot((t_ - self.mdh.getEntry('StartTime'))/60, tm_)
        pylab.plot((t - self.mdh.getEntry('StartTime'))/60, tm, lw=2)
        pylab.xlabel('Time [mins]')
        pylab.ylabel('Temperature [C]')

    def OnPointwiseColoc(self, event):
        from PYME.Analysis import distColoc
        #A vs B
        distColoc.calcDistCorr(self.colourFilter, *(self.colourFilter.getColourChans()[::1]))
        #B vs A
        distColoc.calcDistCorr(self.colourFilter, *(self.colourFilter.getColourChans()[::-1]))



    def OnTrackMolecules(self, event):
        import PYME.Analysis.DeClump.deClumpGUI as deClumpGUI
        import PYME.Analysis.DeClump.deClump as deClump

        bCurr = wx.BusyCursor()
        dlg = deClumpGUI.deClumpDialog(self)

        ret = dlg.ShowModal()

        if ret == wx.ID_OK:
            nFrames = dlg.GetClumpTimeWindow()
            rad_var = dlg.GetClumpRadiusVariable()
            if rad_var == '1.0':
                delta_x = 0*self.selectedDataSource['x'] + dlg.GetClumpRadiusMultiplier()
            else:
                delta_x = dlg.GetClumpRadiusMultiplier()*self.selectedDataSource[rad_var]

        self.selectedDataSource.clumpIndices = deClump.findClumps(self.selectedDataSource['t'].astype('i'), self.selectedDataSource['x'].astype('f4'), self.selectedDataSource['y'].astype('f4'), delta_x.astype('f4'), nFrames)
        numPerClump, b = np.histogram(self.selectedDataSource.clumpIndices, np.arange(self.selectedDataSource.clumpIndices.max() + 1.5) + .5)
        print b
        self.selectedDataSource.clumpSizes = numPerClump[self.selectedDataSource.clumpIndices - 1]

        self.selectedDataSource.setMapping('clumpIndex', 'clumpIndices')
        self.selectedDataSource.setMapping('clumpSize', 'clumpSizes')

        self.RegenFilter()
        self.CreateFoldPanel()

        dlg.Destroy()

    def OnCalcCorrDrift(self, event):
        from PYME.Analysis import driftAutocorr

        dlg = driftAutocorr.CorrDriftDialog(self)

        if dlg.ShowModal() == wx.ID_OK:
            shifts = driftAutocorr.calcCorrDrift(self.filter, step = dlg.GetStep(), window=dlg.GetWindow(), binsize = dlg.GetBinSize())

            driftAutocorr.plotDrift(shifts, step=dlg.GetStep(), driftExprX=self.driftExprX, driftExprY=self.driftExprY, driftMapping=self.mapping)

        dlg.Destroy()


    def OnPlotExtDrift(self, event):
        from PYME.Analysis import driftAutocorr
        import PYME.misc.driftio as dio
        filename = wx.FileSelector("File with drift trajectory data", nameUtils.genResultDirectoryPath(), default_extension='drift', wildcard='Drift File (*.drift)|*.drift')

        #print filename
        if not filename == '':
            extX, extY, extoffs, extstep = dio.loadDriftFile(filename)
            extdrift = np.vstack((extX,extY)).transpose()
            extdrift = extdrift - extdrift[0, :] # make zero based at beginning
            driftAutocorr.plotDrift(extdrift,step=extstep,offset=extoffs,driftExprX=self.driftExprX, driftExprY=self.driftExprY, driftMapping=self.mapping)

    def OnSaveMeasurements(self, event):
        fdialog = wx.FileDialog(None, 'Save measurements ...',
            wildcard='Numpy array|*.npy|Tab formatted text|*.txt', style=wx.SAVE|wx.HIDE_READONLY)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            outFilename = fdialog.GetPath().encode()

            if outFilename.endswith('.txt'):
                of = open(outFilename, 'w')
                of.write('\t'.join(self.objectMeasures.dtype.names) + '\n')

                for obj in self.objectMeasures:
                    of.write('\t'.join([repr(v) for v in obj]) + '\n')
                of.close()

            else:
                np.save(outFilename, self.objectMeasures)


    def OnOpenFile(self, event):
        filename = wx.FileSelector("Choose a file to open", nameUtils.genResultDirectoryPath(), default_extension='h5r', wildcard='PYME Results Files (*.h5r)|*.h5r|Tab Formatted Text (*.txt)|*.txt|Matlab data (*.mat)|*.mat')

        #print filename
        if not filename == '':
            self.OpenFile(filename)

    def OpenFile(self, filename):
        while len(self.filesToClose) > 0:
            self.filesToClose.pop().close()
        
        self.dataSources = []
        if 'zm' in dir(self):
            del self.zm
        self.filter = None
        self.mapping = None
        self.colourFilter = None
        #print os.path.splitext(filename)[1]
        if os.path.splitext(filename)[1] == '.h5r':
                try:
                    self.selectedDataSource = inpFilt.h5rSource(filename)
                    self.dataSources.append(self.selectedDataSource)

                    self.filesToClose.append(self.selectedDataSource.h5f)

                    if 'DriftResults' in self.selectedDataSource.h5f.root:
                        self.dataSources.append(inpFilt.h5rDSource(self.selectedDataSource.h5f))

                        if len(self.selectedDataSource['x']) == 0:
                            self.selectedDataSource = self.dataSources[-1]

                except:
                    self.selectedDataSource = inpFilt.h5rDSource(filename)
                    self.dataSources.append(self.selectedDataSource)
                    
                    self.filesToClose.append(self.selectedDataSource.h5f)

                #once we get around to storing the some metadata with the results
                if 'MetaData' in self.selectedDataSource.h5f.root:
                    self.mdh = MetaDataHandler.HDFMDHandler(self.selectedDataSource.h5f)

                    if 'Camera.ROIWidth' in self.mdh.getEntryNames():
                        x0 = 0
                        y0 = 0

                        x1 = self.mdh.getEntry('Camera.ROIWidth')*1e3*self.mdh.getEntry('voxelsize.x')
                        y1 = self.mdh.getEntry('Camera.ROIHeight')*1e3*self.mdh.getEntry('voxelsize.y')

                        if 'Splitter' in self.mdh.getEntry('Analysis.FitModule'):
                            y1 = y1/2

                        self.imageBounds = ImageBounds(x0, y0, x1, y1)
                    else:
                        self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)

                else:
                    self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)

                if not self.elv == None: #remove previous event viewer
                    i = 0
                    found = False
                    while not found and i < self.notebook.GetPageCount():
                        if self.notebook.GetPage(i) == self.elv:
                            self.notebook.DeletePage(i)
                            found = True
                        else:
                            i += 1

                

                if 'fitResults_Ag' in self.selectedDataSource.keys():
                    #if we used the splitter set up a mapping so we can filter on total amplitude and ratio
                    #if not 'fitError_Ag' in self.selectedDataSource.keys():

                    if 'fitError_Ag' in self.selectedDataSource.keys():
                        self.selectedDataSource = inpFilt.mappingFilter(self.selectedDataSource, A='fitResults_Ag + fitResults_Ar', gFrac='fitResults_Ag/(fitResults_Ag + fitResults_Ar)', error_gFrac = 'sqrt((fitError_Ag/fitResults_Ag)**2 + (fitError_Ag**2 + fitError_Ar**2)/(fitResults_Ag + fitResults_Ar)**2)*fitResults_Ag/(fitResults_Ag + fitResults_Ar)')
                        sg = self.selectedDataSource['fitError_Ag']
                        sr = self.selectedDataSource['fitError_Ar']
                        g = self.selectedDataSource['fitResults_Ag']
                        r = self.selectedDataSource['fitResults_Ar']
                        I = self.selectedDataSource['A']
                        self.selectedDataSource.colNorm = np.sqrt(2*np.pi)*sg*sr/(2*np.sqrt(sg**2 + sr**2)*I)*(
                            scipy.special.erf((sg**2*r + sr**2*(I-g))/(np.sqrt(2)*sg*sr*np.sqrt(sg**2+sr**2)))
                            - scipy.special.erf((sg**2*(r-I) - sr**2*g)/(np.sqrt(2)*sg*sr*np.sqrt(sg**2+sr**2))))
                        self.selectedDataSource.setMapping('ColourNorm', '1.0*colNorm')
                    else:
                        self.selectedDataSource = inpFilt.mappingFilter(self.selectedDataSource, A='fitResults_Ag + fitResults_Ar', gFrac='fitResults_Ag/(fitResults_Ag + fitResults_Ar)', error_gFrac = '0*x + 0.01')
                        self.selectedDataSource.setMapping('fitError_Ag', '1*sqrt(fitResults_Ag/1)')
                        self.selectedDataSource.setMapping('fitError_Ar', '1*sqrt(fitResults_Ar/1)')
                        sg = self.selectedDataSource['fitError_Ag']
                        sr = self.selectedDataSource['fitError_Ar']
                        g = self.selectedDataSource['fitResults_Ag']
                        r = self.selectedDataSource['fitResults_Ar']
                        I = self.selectedDataSource['A']
                        self.selectedDataSource.colNorm = np.sqrt(2*np.pi)*sg*sr/(2*np.sqrt(sg**2 + sr**2)*I)*(
                            scipy.special.erf((sg**2*r + sr**2*(I-g))/(np.sqrt(2)*sg*sr*np.sqrt(sg**2+sr**2)))
                            - scipy.special.erf((sg**2*(r-I) - sr**2*g)/(np.sqrt(2)*sg*sr*np.sqrt(sg**2+sr**2))))
                        self.selectedDataSource.setMapping('ColourNorm', '1.0*colNorm')

                    self.dataSources.append(self.selectedDataSource)

                    if not self.colp == None: #remove previous colour viewer
                        i = 0
                        found = False
                        while not found and i < self.notebook.GetPageCount():
                            if self.notebook.GetPage(i) == self.colp:
                                self.notebook.DeletePage(i)
                                found = True
                            else:
                                i += 1

                    self.colp = colourPanel.colourPanel(self.notebook, self)
#                    if 'Sample.Labelling' in self.mdh.getEntryNames():
#                        self.colp.SpecFromMetadata(self.mdh)
                    self.notebook.AddPage(self.colp, 'Colour')
                elif 'fitResults_sigxl' in self.selectedDataSource.keys():
                    self.selectedDataSource = inpFilt.mappingFilter(self.selectedDataSource)
                    self.dataSources.append(self.selectedDataSource)

                    self.selectedDataSource.setMapping('sig', 'fitResults_sigxl + fitResults_sigyu')
                    self.selectedDataSource.setMapping('sig_d', 'fitResults_sigxl - fitResults_sigyu')

                    self.selectedDataSource.dsigd_dz = -30.
                    self.selectedDataSource.setMapping('fitResults_z0', 'dsigd_dz*sig_d')
                else:
                    self.selectedDataSource = inpFilt.mappingFilter(self.selectedDataSource)
                    self.dataSources.append(self.selectedDataSource)
    
                    

                if 'Events' in self.selectedDataSource.resultsSource.h5f.root:
                    self.events = self.selectedDataSource.resultsSource.h5f.root.Events[:]

                    self.elv = eventLogViewer.eventLogPanel(self.notebook, self.events, self.mdh, [0, self.selectedDataSource['tIndex'].max()]);
                    self.notebook.AddPage(self.elv, 'Events')

                    evKeyNames = set()
                    for e in self.events:
                        evKeyNames.add(e['EventName'])

                    charts = []

                    if 'ProtocolFocus' in evKeyNames:
                        self.zm = piecewiseMapping.GeneratePMFromEventList(self.events, self.mdh, self.mdh.getEntry('StartTime'), self.mdh.getEntry('Protocol.PiezoStartPos'))
                        self.z_focus = 1.e3*self.zm(self.selectedDataSource['t'])
                        #self.elv.SetCharts([('Focus [um]', self.zm, 'ProtocolFocus'),])
                        charts.append(('Focus [um]', self.zm, 'ProtocolFocus'))

                        self.selectedDataSource.z_focus = self.z_focus
                        self.selectedDataSource.setMapping('focus', 'z_focus')

                    if 'ScannerXPos' in self.elv.evKeyNames:
                        x0 = 0
                        if 'Positioning.Stage_X' in self.mdh.getEntryNames():
                            x0 = self.mdh.getEntry('Positioning.Stage_X')
                        self.xm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), x0, 'ScannerXPos', 0)
                        charts.append(('XPos [um]', self.xm, 'ScannerXPos'))

                        self.selectedDataSource.scan_x = 1.e3*self.xm(self.selectedDataSource['t']-.01)
                        self.selectedDataSource.setMapping('ScannerX', 'scan_x')
                        self.selectedDataSource.setMapping('x', 'x + scan_x')

                    if 'ScannerYPos' in self.elv.evKeyNames:
                        y0 = 0
                        if 'Positioning.Stage_Y' in self.mdh.getEntryNames():
                            y0 = self.mdh.getEntry('Positioning.Stage_Y')
                        self.ym = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), y0, 'ScannerYPos', 0)
                        charts.append(('YPos [um]', self.ym, 'ScannerYPos'))

                        self.selectedDataSource.scan_y = 1.e3*self.ym(self.selectedDataSource['t']-.01)
                        self.selectedDataSource.setMapping('ScannerY', 'scan_y')
                        self.selectedDataSource.setMapping('y', 'y + scan_y')

                    if 'ScannerXPos' in self.elv.evKeyNames or 'ScannerYPos' in self.elv.evKeyNames:
                        self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)

                    self.elv.SetCharts(charts)

                if not 'foreShort' in dir(self.selectedDataSource):
                    self.selectedDataSource.foreShort = 1.

                if not 'focus' in self.selectedDataSource.mappings.keys():
                    self.selectedDataSource.focus= np.zeros(self.selectedDataSource['x'].shape)
                    
                if 'fitResults_z0' in self.selectedDataSource.keys():
                    self.selectedDataSource.setMapping('z', 'fitResults_z0 + foreShort*focus')
                else:
                    self.selectedDataSource.setMapping('z', 'foreShort*focus')

                if not self.mdp == None: #remove previous colour viewer
                    i = 0
                    found = False
                    while not found and i < self.notebook.GetPageCount():
                        if self.notebook.GetPage(i) == self.mdp:
                            self.notebook.DeletePage(i)
                            found = True
                        else:
                            i += 1

                if 'mdh' in dir(self):
                    self.mdp = MetadataTree.MetadataPanel(self.notebook, self.mdh, editable=False)
                    self.notebook.AddPage(self.mdp, 'Metadata')
                        
        elif os.path.splitext(filename)[1] == '.mat': #matlab file
            from scipy.io import loadmat
            mf = loadmat(filename)

            dlg = importTextDialog.ImportMatDialog(self, [k for k in mf.keys() if not k.startswith('__')])

            ret = dlg.ShowModal()

            if not ret == wx.ID_OK:
                return #we cancelled

            #try:
            #print dlg.GetFieldNames()
            ds = inpFilt.matfileSource(filename, dlg.GetFieldNames(), dlg.GetVarName())
            self.selectedDataSource = ds
            self.dataSources.append(ds)

            self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)
        else: #assume it's a text file
            dlg = importTextDialog.ImportTextDialog(self, filename)

            ret = dlg.ShowModal()

            if not ret == wx.ID_OK:
                return #we cancelled

            #try:
            #print dlg.GetFieldNames()
            ds = inpFilt.textfileSource(filename, dlg.GetFieldNames())
            self.selectedDataSource = ds
            self.dataSources.append(ds)

            self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)

        self.SetTitle('PYME Visualise - ' + filename)
        #for k in self.filterKeys.keys():

        #if we've done a 3d fit
        #print self.selectedDataSource.keys()
        for k in self.filterKeys.keys():
            if not k in self.selectedDataSource.keys():
                self.filterKeys.pop(k)

        #print self.filterKeys
        self.RegenFilter()

        self.CreateFoldPanel()
        if not self.colp == None:
            if 'Sample.Labelling' in self.mdh.getEntryNames():
                self.colp.SpecFromMetadata(self.mdh)
            else:
                self.colp.refresh()
        self.SetFit()

    def OnOpenChannel(self, event):
        filename = wx.FileSelector("Choose a file to open", nameUtils.genResultDirectoryPath(), default_extension='h5r', wildcard='PYME Results Files (*.h5r)|*.h5r|Tab Formatted Text (*.txt)|*.txt')

        #print filename
        if not filename == '':
            self.OpenChannel(filename)

    def OpenChannel(self, filename):
        self.filter = None
        self.mapping = None
        self.colourFilter = None
        print os.path.splitext(filename)[1]
        if os.path.splitext(filename)[1] == '.h5r':
                try:
                    self.selectedDataSource = inpFilt.h5rSource(filename)
                    self.dataSources.append(self.selectedDataSource)

                    self.filesToClose.append(self.selectedDataSource.h5f)

                    if 'DriftResults' in self.selectedDataSource.h5f.root:
                        self.dataSources.append(inpFilt.h5rDSource(self.selectedDataSource.h5f))

                        if len(self.selectedDataSource['x']) == 0:
                            self.selectedDataSource = self.dataSources[-1]
                except:
                    self.selectedDataSource = inpFilt.h5rDSource(filename)
                    self.dataSources.append(self.selectedDataSource)

                    self.filesToClose.append(self.selectedDataSource.h5f)

                #once we get around to storing the some metadata with the results
#                if 'MetaData' in self.selectedDataSource.h5f.root:
#                    self.mdh = MetaDataHandler.HDFMDHandler(self.selectedDataSource.h5f)
#
#                    if 'Camera.ROIWidth' in self.mdh.getEntryNames():
#                        x0 = 0
#                        y0 = 0
#
#                        x1 = self.mdh.getEntry('Camera.ROIWidth')*1e3*self.mdh.getEntry('voxelsize.x')
#                        y1 = self.mdh.getEntry('Camera.ROIHeight')*1e3*self.mdh.getEntry('voxelsize.y')
#
#                        self.imageBounds = ImageBounds(x0, y0, x1, y1)
#                    else:
#                        self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)
#
#                else:
#                    self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)
#
#                if not self.elv == None: #remove previous event viewer
#                    i = 0
#                    found = False
#                    while not found and i < self.notebook.GetPageCount():
#                        if self.notebook.GetPage(i) == self.elv:
#                            self.notebook.DeletePage(i)
#                            found = True
#                        else:
#                            i += 1
#
#                if 'Events' in self.selectedDataSource.h5f.root:
#                    self.events = self.selectedDataSource.h5f.root.Events[:]
#
#                    self.elv = eventLogViewer.eventLogPanel(self.notebook, self.events, self.mdh, [0, self.selectedDataSource['tIndex'].max()]);
#                    self.notebook.AddPage(self.elv, 'Events')
#
#                    evKeyNames = set()
#                    for e in self.events:
#                        evKeyNames.add(e['EventName'])
#
#                    if 'ProtocolFocus' in evKeyNames:
#                        self.zm = piecewiseMapping.GeneratePMFromEventList(self.events, self.mdh.getEntry('Camera.CycleTime'), self.mdh.getEntry('StartTime'), self.mdh.getEntry('Protocol.PiezoStartPos'))
#                        self.elv.SetCharts([('Focus [um]', self.zm, 'ProtocolFocus'),])

        else: #assume it's a text file
            dlg = importTextDialog.ImportTextDialog(self)

            ret = dlg.ShowModal()

            if not ret == wx.ID_OK:
                return #we cancelled

            #try:
            #print dlg.GetFieldNames()
            ds = inpFilt.textfileSource(filename, dlg.GetFieldNames())
            self.selectedDataSource = ds
            self.dataSources.append(ds)

            #self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)

        #self.SetTitle('PYME Visualise - ' + filename)
        #for k in self.filterKeys.keys():

        #if we've done a 3d fit
#        print self.selectedDataSource.keys()
#        if 'fitResults_z0' in self.selectedDataSource.keys():
#            self.filterKeys.pop('sig')

        #print self.filterKeys
        self.RegenFilter()
        self.CreateFoldPanel()
        if not self.colp == None:
            self.colp.refresh()
        self.SetFit()

    def OnOpenRaw(self, event):
        filename = wx.FileSelector("Choose a file to open", nameUtils.genResultDirectoryPath(), default_extension='h5', wildcard='PYME Spool Files (*.h5)|*.h5|Khoros Data Format (*.kdf)|*.kdf')
        if not filename == '':
            self.OpenRaw(filename)

    def OpenRaw(self, filename):
        ext = os.path.splitext(filename)[-1]
        if ext == '.kdf': #KDF file
            from PYME.FileUtils import read_kdf
            im = read_kdf.ReadKdfData(filename).squeeze()

            dlg = wx.TextEntryDialog(self, 'Pixel Size [nm]:', 'Please enter the x-y pixel size', '70')
            dlg.ShowModal()

            pixelSize = float(dlg.GetValue())

            imb = ImageBounds(0,0,pixelSize*im.shape[0],pixelSize*im.shape[1])
            
            img = GeneratedImage(im,imb, pixelSize )
            imf = imageView.ImageViewFrame(self,img, self.glCanvas, title=filename,zdim=2)
            self.generatedImages.append(imf)
            imf.Show()
        elif ext == '.h5': #h5 spool
            h5f = tables.openFile(filename)

            md = MetaData.genMetaDataFromHDF(h5f)

            
            im = h5f.root.ImageData
            
            self.filesToClose.append(h5f)
            
            pixelSize = md.voxelsize.x*1e3

            imb = ImageBounds(0,0,pixelSize*im.shape[1],pixelSize*im.shape[2])

            img = GeneratedImage(im,imb, pixelSize )
            imf = imageView.ImageViewFrame(self,img, self.glCanvas, title=filename,zp=min(md.EstimatedLaserOnFrameNo+10,(h5f.root.ImageData.shape[0]-1)))
            self.generatedImages.append(imf)
            imf.Show()
        else:
            raise 'Unrecognised Data Format'




    def RegenFilter(self):
        if not self.selectedDataSource == None:
            self.filter = inpFilt.resultsFilter(self.selectedDataSource, **self.filterKeys)
            if self.mapping:
                self.mapping.resultsSource = self.filter
            else:
                self.mapping = inpFilt.mappingFilter(self.filter)

#                if 'zm' in dir(self):
#                    self.mapping.zm = self.zm
#                    self.mapping.setMapping('focus', '1e3*zm(t)')

#                if not 'dz_dt' in dir(self.mapping):
#                    self.mapping.dz_dt = 0.
#
#                if 'fitResults_z0' in self.filter.keys():
#                    if 'zm' in dir(self):
#                        if not 'foreShort' in dir(self.mapping):
#                            self.mapping.foreShort = 1.
#                        self.mapping.setMapping('z', 'fitResults_z0 + foreShort*focus + dz_dt*t')
#                    else:
#                        self.mapping.setMapping('z', 'fitResults_z0+ dz_dt*t')
#                elif 'zm' in dir(self):
#                    self.mapping.setMapping('z', 'focus + dz_dt*t')
#                else:
#                    self.mapping.setMapping('z', 'dz_dt*t')

            if not self.colourFilter:
                self.colourFilter = inpFilt.colourFilter(self.mapping, self)

        self.stFilterNumPoints.SetLabel('%d of %d events' % (len(self.filter['x']), len(self.selectedDataSource['x'])))

        self.Triangles = None
        self.edb = None
        self.objects = None

        self.GeneratedMeasures = {}
#        if 'zm' in dir(self):
#            self.GeneratedMeasures['focusPos'] = self.zm(self.colourFilter['tIndex'].astype('f'))
        self.Quads = None

        self.RefreshView()


    def RefreshView(self):
        if self.colourFilter == None:
            return #get out of here

        if len(self.colourFilter['x']) == 0:
            wx.MessageBox('No data points - try adjusting the filter', "len(filter['x']) ==0")
            return

        if self.glCanvas.init == 0: #glcanvas is not initialised
            return

        bCurr = wx.BusyCursor()


        if self.objects == None:
#            if 'bObjMeasure' in dir(self):
#                self.bObjMeasure.Enable(False)
            self.objectMeasures = None

            if not self.rav == None: #remove previous event viewer
                i = 0
                found = False
                while not found and i < self.notebook.GetPageCount():
                    if self.notebook.GetPage(i) == self.rav:
                        self.notebook.DeletePage(i)
                        found = True
                    else:
                        i += 1
                        
                self.rav = None

        if self.viewMode == 'points':
            self.glCanvas.setPoints(self.colourFilter['x'], self.colourFilter['y'], self.pointColour())
        elif self.viewMode == 'triangles':
            if self.Triangles == None:
                status = statusLog.StatusLogger("Generating Triangulation ...")
                self.Triangles = delaunay.Triangulation(self.colourFilter['x'] + 0.1*np.random.normal(size=self.colourFilter['x'].shape), self.colourFilter['y'] + 0.1*np.random.normal(size=self.colourFilter['x'].shape))
                
            self.glCanvas.setTriang(self.Triangles)

        elif self.viewMode == 'voronoi':
            if self.Triangles == None:
                status = statusLog.StatusLogger("Generating Triangulation ...")
                self.Triangles = delaunay.Triangulation(self.colourFilter['x']+ 0.1*np.random.normal(size=self.colourFilter['x'].shape), self.colourFilter['y']+ 0.1*np.random.normal(size=self.colourFilter['x'].shape))
                

            status = statusLog.StatusLogger("Generating Voronoi Diagram ... ")
            self.glCanvas.setVoronoi(self.Triangles)
            

        elif self.viewMode == 'quads':
            if self.Quads == None:
                status = statusLog.StatusLogger("Generating QuadTree ...")
                self.GenQuads()
                

            self.glCanvas.setQuads(self.Quads)

        elif self.viewMode == 'interp_triangles':
            if self.Triangles == None:
                status = statusLog.StatusLogger("Generating Triangulation ...")
                self.Triangles = delaunay.Triangulation(self.colourFilter['x']+ 0.1*np.random.normal(size=self.colourFilter['x'].shape), self.colourFilter['y']+ 0.1*np.random.normal(size=self.colourFilter['x'].shape))

            self.glCanvas.setIntTriang(self.Triangles, self.pointColour())

        elif self.viewMode == 'blobs':
            if self.objects == None:
                #check to see that we don't have too many points
                if len(self.colourFilter['x']) > 1e5:
                    goAhead = wx.MessageBox('You have %d events in the selected ROI;\nThis could take a LONG time ...' % len(self.colourFilter['x']), 'Continue with blob detection', wx.YES_NO|wx.ICON_EXCLAMATION)

                    if not goAhead == wx.YES:
                        return

                if self.Triangles == None:
                    status = statusLog.StatusLogger("Generating Triangulation ...")
                    self.Triangles = delaunay.Triangulation(self.colourFilter['x']+ 0.1*np.random.normal(size=self.colourFilter['x'].shape), self.colourFilter['y']+ 0.1*np.random.normal(size=self.colourFilter['x'].shape))

                if self.edb == None:
                    self.edb = edges.EdgeDB(self.Triangles)

                if self.blobJitter == 0:
                    #T = delny.Triangulation(pylab.array([self.colourFilter['x'] + 0.1*pylab.randn(len(self.colourFilter['x'])), self.colourFilter['y']+ 0.1*pylab.randn(len(self.colourFilter['x']))]).T)

                    #self.objects = gen3DTriangs.segment(T, self.objThreshold, self.objMinSize)

                    #edb = edges.EdgeDB(self.Triangles)
                    self.objIndices = edges.objectIndices(self.edb.segment(self.objThreshold), self.objMinSize)
                    self.objects = [pylab.vstack((self.Triangles.x[oi], self.Triangles.y[oi])).T for oi in self.objIndices]
                else:
                    if not 'neighbourDistances' in self.GeneratedMeasures.keys():
                        self.genNeighbourDists()
                    x_ = pylab.hstack([self.colourFilter['x'] + 0.5*self.GeneratedMeasures['neighbourDistances']*pylab.randn(len(self.colourFilter['x'])) for i in range(self.blobJitter)])
                    y_ = pylab.hstack([self.colourFilter['y'] + 0.5*self.GeneratedMeasures['neighbourDistances']*pylab.randn(len(self.colourFilter['x'])) for i in range(self.blobJitter)])

                    #T = delny.Triangulation(pylab.array([x_, y_]).T)
                    T = delaunay.Triangulation(x_, y_)
                    #self.objects = gen3DTriangs.segment(T, self.objThreshold, self.objMinSize)
                    edb = edges.EdgeDB(T)
                    objIndices = edges.objectIndices(edb.segment(self.objThreshold), self.objMinSize)
                    self.objects = [pylab.vstack((T.x[oi], T.y[oi])).T for oi in objIndices]

#                if 'bObjMeasure' in dir(self):
#                    self.bObjMeasure.Enable(True)

            self.glCanvas.setBlobs(self.objects, self.objThreshold)
            self.objCInd = self.glCanvas.c

        self.hlCLim.SetData(self.glCanvas.c, self.glCanvas.clim[0], self.glCanvas.clim[1])

        if not self.colp == None and self.colp.IsShown():
            self.colp.refresh()

        #self.sh.shell.user_ns.update(self.__dict__)
        wx.EndBusyCursor()
        self.workspaceView.RefreshItems()



    def GenQuads(self):
        di = max(self.imageBounds.x1 - self.imageBounds.x0, self.imageBounds.y1 - self.imageBounds.y0)

        np = di/self.QTGoalPixelSize

        di = self.QTGoalPixelSize*2**pylab.ceil(pylab.log2(np))

        
        self.Quads = pointQT.qtRoot(self.imageBounds.x0, self.imageBounds.x0+di, self.imageBounds.y0, self.imageBounds.y0 + di)

        for xi, yi in zip(self.colourFilter['x'],self.colourFilter['y']):
            self.Quads.insert(pointQT.qtRec(xi,yi, None))

    def SetFit(self,event = None):
        xsc = self.imageBounds.width()*1./self.glCanvas.Size[0]
        ysc = self.imageBounds.height()*1./self.glCanvas.Size[1]

        #print xsc
        #print ysc

        if xsc > ysc:
            self.glCanvas.setView(self.imageBounds.x0, self.imageBounds.x1, self.imageBounds.y0, self.imageBounds.y0 + xsc*self.glCanvas.Size[1])
        else:
            self.glCanvas.setView(self.imageBounds.x0, self.imageBounds.x0 + ysc*self.glCanvas.Size[0], self.imageBounds.y0, self.imageBounds.y1)

    def OnFitROI(self,event = None):
        if 'x' in self.filterKeys.keys():
            xbounds = self.filterKeys['x']
        else:
            xbounds = (self.imageBounds.x0, self.imageBounds.x1)

        if 'y' in self.filterKeys.keys():
            ybounds = self.filterKeys['y']
        else:
            ybounds = (self.imageBounds.y0, self.imageBounds.y1)
        
        xsc = (xbounds[1] - xbounds[0])*1./self.glCanvas.Size[0]
        ysc = (ybounds[1] - ybounds[0])*1./self.glCanvas.Size[1]

        #print xsc
        #print ysc

        if xsc > ysc:
            self.glCanvas.setView(xbounds[0], xbounds[1], ybounds[0], ybounds[0] + xsc*self.glCanvas.Size[1])
        else:
            self.glCanvas.setView(xbounds[0], xbounds[0] + ysc*self.glCanvas.Size[0], ybounds[0], ybounds[1])

    def OnGLViewChanged(self):
        for genI in self.generatedImages:
            genI.Refresh()

    def SetStatus(self, statusText):
        self.statusbar.SetStatusText(statusText, 0)


class VisGuiApp(wx.App):
    def __init__(self, filename, *args):
        self.filename = filename
        wx.App.__init__(self, *args)
        
        
    def OnInit(self):
        wx.InitAllImageHandlers()
        self.main = VisGUIFrame(None, self.filename)
        self.main.Show()
        self.SetTopWindow(self.main)
        return True


def main(filename):
    application = VisGuiApp(filename, 0)
    application.MainLoop()


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    
    filename = None

    if len(sys.argv) > 1:
        filename = sys.argv[1]

    if wx.GetApp() == None: #check to see if there's already a wxApp instance (running from ipython -pylab or -wthread)
        main(filename)
    else:
        #time.sleep(1)
        visFr = VisGUIFrame(None, filename)
        visFr.Show()
        visFr.RefreshView()


