# -*- coding: utf-8 -*-
"""
Created on Sat May 14 14:54:52 2016

@author: david
"""
import wx
import wx.py.shell

import PYME.ui.autoFoldPanel as afp
import wx.lib.agw.aui as aui

#hacked so py2exe works
#from PYME.DSView.dsviewer import View3D

from PYME.LMVis import gl_render3D as gl_render
#from PYME.LMVis import workspaceTree
#import sys

import pylab

from PYME.LMVis.gl_render3D_shaders import LMGLShaderCanvas
from PYME.misc import extraCMaps
from PYME.IO.FileUtils import nameUtils

import os

#from PYME.LMVis import colourPanel
from PYME.LMVis import renderers

import logging
logger = logging.getLogger(__name__)

import PYME.config

#try importing our drift correction stuff
HAVE_DRIFT_CORRECTION = False
try:
    from PYMEnf.DriftCorrection.driftGUI import CreateDriftPane
    HAVE_DRIFT_CORRECTION = True
    #from PYMEnf.DriftCorrection import driftGUI
    #renderers.renderMetadataProviders.append(driftGUI.dp.SaveMetadata)
except:
    pass

from PYME.LMVis.colourFilterGUI import CreateColourFilterPane
from PYME.LMVis import displayPane
from PYME.LMVis.filterPane import CreateFilterPane

from PYME.LMVis import pointSettingsPanel
from PYME.LMVis import quadTreeSettings
from PYME.LMVis import triBlobs

#from PYME.Analysis import MetadataTree

import numpy as np
#import scipy.special

#from PYME.DSView import eventLogViewer



from PYME.LMVis import statusLog
#from PYME.recipes import recipeGui

class VisGUICore(object):
    def __init__(self, use_shaders=False):
        self.viewMode = 'points' #one of points, triangles, quads, or voronoi
        #self.colData = 't'
        self.pointDisplaySettings = pointSettingsPanel.PointDisplaySettings()
        self.pointDisplaySettings.on_trait_change(self.RefreshView)
        
        self.quadTreeSettings = quadTreeSettings.QuadTreeSettings()
        self.quadTreeSettings.on_trait_change(self.RefreshView)
        
        self.pipeline.blobSettings.on_trait_change(self.RefreshView)
        self.pipeline.onRebuild.connect(self.RefreshView)
        
        #initialize the gl canvas
        if isinstance(self, wx.Window):
            win = self
        else:
            win = self.dsviewer

        if not use_shaders:
            self.glCanvas = gl_render.LMGLCanvas(win)
        else:
            from PYME.LMVis.gl_render3D_shaders import LMGLShaderCanvas
            self.glCanvas = LMGLShaderCanvas(win)
        win.AddPage(page=self.glCanvas, caption='View')#, select=True)

        self.glCanvas.setCMap(pylab.cm.gist_rainbow) #pylab.cm.hot

        #self.rec_gui = recipeGui.
        #win.AddPage(page=self.glCanvas, caption='View')#, select=True)
        
        self.refv = False
        
        self._legacy_layer = None
        self._new_layers = PYME.config.get('VisGUI-new_layers', False)
        
        renderers.renderMetadataProviders.append(self.SaveMetadata)
        self.use_shaders = use_shaders
        
        wx.CallLater(100, self.OnIdle)
        
    
    def OnIdle(self, event=None):
        print('Ev Idle')
        if self.glCanvas._is_initialized and not self.refv:
            self.refv = True
            print((self.viewMode, self.pointDisplaySettings.colourDataKey))
            self.SetFit()
            
            if self._new_layers:
                self.add_layer(method='points')
            else:
                self.RefreshView()
                self.displayPane.OnPercentileCLim(None)
                
            self.Refresh()
            self.Update()
            print('refreshed')
            
    def GenPanels(self, sidePanel):    
        self.GenDataSourcePanel(sidePanel)

        self.filterPane = CreateFilterPane(sidePanel, self.pipeline.filterKeys, self.pipeline, self)

        if HAVE_DRIFT_CORRECTION:
            self.driftPane = CreateDriftPane(sidePanel, self.pipeline.mapping, self.pipeline)
            
        self.colourFilterPane = CreateColourFilterPane(sidePanel, self.pipeline.colourFilter, self.pipeline)
        self.displayPane = displayPane.CreateDisplayPane(sidePanel, self.glCanvas, self)
        self.displayPane.Bind(displayPane.EVT_DISPLAY_CHANGE, self.RefreshView)
        
        if PYME.config.get('VisGUI-new_layers', False):
            from .layer_panel import CreateLayerPane
            CreateLayerPane(sidePanel, self)
        else:
            if self.viewMode == 'quads':
                quadTreeSettings.GenQuadTreePanel(self, sidePanel)
    
            if self.viewMode in ['points', 'tracks', 'pointsprites', 'shadedpoints']:
                pointSettingsPanel.GenPointsPanel(self, sidePanel)
            if self.viewMode == 'blobs':
                triBlobs.GenBlobPanel(self, sidePanel)
    
            if self.viewMode == 'interp_triangles':
                pointSettingsPanel.GenPointsPanel(self, sidePanel,'Vertex Colours')

        
        self.glCanvas.Refresh()
        
    def GenDataSourcePanel(self, pnl):
        from PYME.recipes.vertical_recipe_display import RecipeDisplayPanel
        item = afp.foldingPane(pnl, -1, caption="Data Source")#, pinned = True)
        
        self.chSource = wx.Choice(item, -1, choices=[])
        self.set_datasource_choices()
        self.chSource.Bind(wx.EVT_CHOICE, self.OnSourceChange)
        self.pipeline.onRebuild.connect(self.set_datasource_choices)
            
        item.AddNewElement(self.chSource, foldable=False)
        
        self.recipeView = RecipeDisplayPanel(item)
        self.recipeView.SetRecipe(self.pipeline.recipe)
        item.AddNewElement(self.recipeView)

        pnl.AddPane(item)
        
    def set_datasource_choices(self, event=None, **kwargs):
        dss = self.pipeline.dataSources.keys()
        self.chSource.SetItems(dss)
        if not self.pipeline.selectedDataSourceKey is None:
            self.chSource.SetStringSelection(self.pipeline.selectedDataSourceKey)
        

    def OnSourceChange(self, event):
        self.pipeline.selectDataSource(self.chSource.GetStringSelection())
        
        
    def pointColour(self):
        pointColour = None
        
        colData = self.pointDisplaySettings.colourDataKey
        
        if colData == '<None>':
            pointColour = None
        elif not self.pipeline.colourFilter is None:
            if colData in self.pipeline.keys():
                pointColour = self.pipeline[colData]
            elif colData in self.pipeline.GeneratedMeasures.keys():
                pointColour = self.pipeline.GeneratedMeasures[colData]
            else:
                pointColour = None

        return pointColour
        
    def CreateMenuBar(self, subMenu = False, use_shaders = False):
        logger.debug('Creating VisGUI menu bar')
        if 'dsviewer' in dir(self):
            parent = self.dsviewer
        else:
            parent = self

        self.AddMenuItem('File', '&Open', self.OnOpenFile)
        if not subMenu:
            self.AddMenuItem('File', "Open &Raw/Prebleach Data", self.OnOpenRaw)
            self.AddMenuItem('File', "Open Extra &Channel", self.OnOpenChannel)
            
        self.AddMenuItem('File', 'Save filtered localizations', self.OnSave)
        
        if not subMenu:
            self.AddMenuItem('File', itemType='separator')
            self.AddMenuItem('File', "&Save Measurements", self.OnSaveMeasurements)

            self.AddMenuItem('File', itemType='separator')

            self.AddMenuItem('File', "&Exit", self.OnQuit,id = wx.ID_EXIT)


        self.AddMenuItem('View', '&Points', self.OnViewPoints, itemType='normal') #TODO - add radio type
        if use_shaders:
            self.AddMenuItem('View', '&Pointsprites', self.OnViewPointsprites)
            self.AddMenuItem('View', '&Shaded Points', self.OnViewShadedPoints)
        self.AddMenuItem('View',  '&Triangles', self.OnViewTriangles)
        self.AddMenuItem('View', '3D Triangles', self.OnViewTriangles3D)
        self.AddMenuItem('View', '&Quad Tree', self.OnViewQuads)
        if not use_shaders:
            self.AddMenuItem('View', '&Voronoi', self.OnViewVoronoi)
            self.AddMenuItem('View', '&Interpolated Triangles', self.OnViewInterpTriangles)
            self.AddMenuItem('View', '&Blobs', self.OnViewBlobs)
            self.AddMenuItem('View', '&Tracks', self.OnViewTracks)


        #self.view_menu.Check(ID_VIEW_POINTS, True)
        #self.view_menu.Enable(ID_VIEW_QUADS, False)

        self.AddMenuItem('View', itemType='separator')
        self.AddMenuItem('View', '&Fit', self.SetFit)
        self.AddMenuItem('View', 'Fit &ROI', self.OnFitROI)

        #this needs an ID as we bind to it elsewhere (in the filter panel)
        self.ID_VIEW_CLIP_ROI = wx.NewId()
        self.AddMenuItem('View', 'Clip to ROI\tF8', id=self.ID_VIEW_CLIP_ROI)
        
        renderers.init_renderers(self)

        from PYME.LMVis import Extras
        Extras.InitPlugins(self)
        
        try:
            #see if we can find any 'non free' plugins
            from PYMEnf.Analysis.LMVis import Extras
            Extras.InitPlugins(self)
        except ImportError:
            pass

        if not subMenu:
            self.AddMenuItem('Help', "&About",)

        
    def OnViewPoints(self,event):
        self.viewMode = 'points'
        #self.glCanvas.cmap = pylab.cm.hsv
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewPointsprites(self, event):
        self.viewMode = 'pointsprites'
        # self.glCanvas.cmap = pylab.cm.hsv
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewShadedPoints(self,event):
        self.viewMode = 'shadedpoints'
        #self.glCanvas.cmap = pylab.cm.hsv
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewTracks(self,event):
        self.viewMode = 'tracks'
        #self.glCanvas.cmap = pylab.cm.hsv
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewBlobs(self,event):
        self.viewMode = 'blobs'
        self.RefreshView()
        self.CreateFoldPanel()
        #self.OnPercentileCLim(None)

    def OnViewTriangles(self,event):
        self.viewMode = 'triangles'
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewTriangles3D(self,event):
        self.viewMode = 'triangles3D'
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewQuads(self,event):
        self.viewMode = 'quads'
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewVoronoi(self,event):
        self.viewMode = 'voronoi'
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)

    def OnViewInterpTriangles(self,event):
        self.viewMode = 'interp_triangles'
        self.RefreshView()
        self.CreateFoldPanel()
        self.displayPane.OnPercentileCLim(None)
        
    def OnOpenFile(self, event):
        filename = wx.FileSelector("Choose a file to open", 
                                   nameUtils.genResultDirectoryPath(), 
                                   default_extension='h5r', 
                                   wildcard='PYME Results Files (*.h5r)|*.h5r|Tab Formatted Text (*.txt)|*.txt|Matlab data (*.mat)|*.mat|Comma separated values (*.csv)|*.csv')

        #print filename
        if not filename == '':
            self.OpenFile(filename)
            
    def OnSave(self, event):
        filename = wx.SaveFileSelector("Save pipeline output as ...", '.hdf')
        if not filename == '':
            self.pipeline.save_hdf(filename)
            
    def RegenFilter(self):
        logger.warn('RegenFilter is deprecated, please use pipeline.Rebuild() instead.')
        self.pipeline.Rebuild()
        
    def add_layer(self, method='points', ds_name=''):
        from .layer_wrapper import LayerWrapper
        l = LayerWrapper(self.pipeline, method=method, ds_name=ds_name)
        self.glCanvas.layers.append(l)
        l.on_update.connect(self.glCanvas.refresh)
        return l
    
    @property
    def layers(self):
        return self.glCanvas.layers
        
    def RefreshView(self, event=None, **kwargs):
        if self._new_layers:
            #refresh view no longer updates the display
            
            #FIXME - this doesn't belong here (used to be done in SetPoints)
            self.glCanvas.zc = self.pipeline['z'].mean()
            return
        
        if not self.pipeline.ready:
            return #get out of here

        self.filterPane.stFilterNumPoints.SetLabel('%d of %d events' % (len(self.pipeline.filter['x']), len(self.pipeline.selectedDataSource['x'])))

        if len(self.pipeline['x']) == 0:
            self.glCanvas.setOverlayMessage('No data points - try adjusting the filter')
            return
        else:
            self.glCanvas.setOverlayMessage('')

        if not self.glCanvas._is_initialized: #glcanvas is not initialised
            return

        #bCurr = wx.BusyCursor()

        #delete previous layers (new view)
        # self.glCanvas.layers = []
        
        # only delete the layer we created on the last call - leave other layers alone.
        if self._legacy_layer:
            try:
                self.glCanvas.layers.remove(self._legacy_layer)
            except ValueError:
                pass
            self._legacy_layer = None
        
        self.glCanvas.pointSize = self.pointDisplaySettings.pointSize

        if self.pipeline.objects is None:
#            if 'bObjMeasure' in dir(self):
#                self.bObjMeasure.Enable(False)
            self.objectMeasures = None

            if 'rav' in dir(self) and not self.rav is None: #remove previous event viewer
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
            if 'setPoints3D' in dir(self.glCanvas) and 'z' in self.pipeline.keys():
                #new mode
                self.glCanvas.setPoints3D(self.pipeline['x'], 
                                      self.pipeline['y'], 
                                      self.pipeline['z'], 
                                      self.pointColour(), alpha=self.pointDisplaySettings.alpha)
            else:
                self.glCanvas.setPoints(self.pipeline['x'], 
                                    self.pipeline['y'], self.pointColour())
        elif self.viewMode == 'pointsprites':
            self.glCanvas.setPoints3D(self.pipeline['x'],
                                      self.pipeline['y'],
                                      self.pipeline['z'],
                                      self.pointColour(), alpha=self.pointDisplaySettings.alpha, mode='pointsprites')
        elif self.viewMode == 'shadedpoints':
            self.glCanvas.setPoints3D(self.pipeline['x'],
                                      self.pipeline['y'],
                                      self.pipeline['z'],
                                      self.pointColour(),
                                      alpha=self.pointDisplaySettings.alpha,
                                      normal_x=self.pipeline['xn'],
                                      normal_y=self.pipeline['yn'],
                                      normal_z=self.pipeline['zn'],
                                      mode='shadedpoints')
        elif self.viewMode == 'tracks':
            if 'setTracks3D' in dir(self.glCanvas) and 'z' in self.pipeline.keys():
                self.glCanvas.setTracks3D(self.pipeline['x'], 
                                    self.pipeline['y'], 
                                    self.pipeline['z'],
                                    self.pipeline['clumpIndex'], 
                                    self.pointColour())
            else:
                self.glCanvas.setTracks(self.pipeline['x'], 
                                    self.pipeline['y'], 
                                    self.pipeline['clumpIndex'], 
                                    self.pointColour())
                                    
        elif self.viewMode == 'triangles':
            self.glCanvas.setTriang(self.pipeline.getTriangles())

        elif self.viewMode == 'triangles3D':
            self.glCanvas.setTriang3D(self.pipeline['x'], 
                                      self.pipeline['y'], 
                                      self.pipeline['z'], 'z', 
                                      sizeCutoff=self.glCanvas.edgeThreshold)

        elif self.viewMode == 'voronoi':
            status = statusLog.StatusLogger("Generating Voronoi Diagram ... ")
            self.glCanvas.setVoronoi(self.pipeline.getTriangles())
            

        elif self.viewMode == 'quads':
            if self.pipeline.Quads is None:
                status = statusLog.StatusLogger("Generating QuadTree ...")
                self.pipeline.GenQuads()
                

            self.glCanvas.setQuads(self.pipeline.Quads)

        elif self.viewMode == 'interp_triangles':
            self.glCanvas.setIntTriang(self.pipeline.getTriangles(), self.pointColour())

        elif self.viewMode == 'blobs':
            if self.pipeline.objects is None:
                #check to see that we don't have too many points
                if len(self.pipeline['x']) > 1e5:
                    goAhead = wx.MessageBox('You have %d events in the selected ROI;\nThis could take a LONG time ...' % len(self.pipeline['x']), 'Continue with blob detection', wx.YES_NO|wx.ICON_EXCLAMATION)
    
                    if not goAhead == wx.YES:
                        return

            self.glCanvas.setBlobs(*self.pipeline.getBlobs())
            self.objCInd = self.glCanvas.c
            
        #save the new layer we created so we can remove it
        self._legacy_layer = self.glCanvas.layers[-1]

        self.displayPane.hlCLim.SetData(self.glCanvas.c, self.glCanvas.clim[0], 
                                        self.glCanvas.clim[1])

        if 'colp' in dir(self) and not self.colp is None and self.colp.IsShown():
            self.colp.refresh()

        #self.sh.shell.user_ns.update(self.__dict__)
        #wx.EndBusyCursor()
        #self.workspaceView.RefreshItems()
        
        
    def SetFit(self,event = None):
        xsc = self.pipeline.imageBounds.width()*1./self.glCanvas.Size[0]
        ysc = self.pipeline.imageBounds.height()*1./self.glCanvas.Size[1]

        if xsc != 0 and ysc != 0:
            if xsc > ysc:
                self.glCanvas.setView(self.pipeline.imageBounds.x0, self.pipeline.imageBounds.x1,
                                      self.pipeline.imageBounds.y0, self.pipeline.imageBounds.y0 + xsc*self.glCanvas.Size[1])
            else:
                self.glCanvas.setView(self.pipeline.imageBounds.x0, self.pipeline.imageBounds.x0 + ysc*self.glCanvas.Size[0],
                                      self.pipeline.imageBounds.y0, self.pipeline.imageBounds.y1)

    def OnFitROI(self,event = None):
        if 'x' in self.pipeline.filterKeys.keys():
            xbounds = self.pipeline.filterKeys['x']
        else:
            xbounds = (self.pipeline.imageBounds.x0, self.pipeline.imageBounds.x1)

        if 'y' in self.pipeline.filterKeys.keys():
            ybounds = self.pipeline.filterKeys['y']
        else:
            ybounds = (self.pipeline.imageBounds.y0, self.pipeline.imageBounds.y1)
        
        xsc = (xbounds[1] - xbounds[0])*1./self.glCanvas.Size[0]
        ysc = (ybounds[1] - ybounds[0])*1./self.glCanvas.Size[1]

        if xsc > ysc:
            self.glCanvas.setView(xbounds[0], xbounds[1], ybounds[0], 
                                  ybounds[0] + xsc*self.glCanvas.Size[1])
        else:
            self.glCanvas.setView(xbounds[0], xbounds[0] + ysc*self.glCanvas.Size[0], 
                                  ybounds[0], ybounds[1])


    def SetStatus(self, statusText):
        self.statusbar.SetStatusText(statusText, 0)
        
    def SaveMetadata(self, mdh):
        mdh['Filter.Keys'] = self.pipeline.filterKeys      
        
        if HAVE_DRIFT_CORRECTION and 'x' in self.pipeline.mapping.mappings.keys(): #drift correction has been applied
            self.driftPane.dp.SaveMetadata(mdh)

    def AddMenuItem(self, menuName, *args, **kwargs):
        """ Add a menu item. Calls AUIFrame.AddMenuItem. Should be over-ridden when called from VisGUI, and only
        exposed / used when called from within a dsviewer module."""
        logger.debug('Calling AddMenuItem from visCore')
        self.dsviewer.AddMenuItem('Points>' + menuName, *args, **kwargs)

    def OpenFile(self, filename):
        args = {}
        
        if os.path.splitext(filename)[1] =='.h5r':
            pass
        elif os.path.splitext(filename)[1] == '.hdf':
            pass
        elif os.path.splitext(filename)[1] == '.mat':
            from PYME.LMVis import importTextDialog
            from scipy.io import loadmat
            
            mf = loadmat(filename)

            dlg = importTextDialog.ImportMatDialog(self, [k for k in mf.keys() if not k.startswith('__')])
            ret = dlg.ShowModal()

            if not ret == wx.ID_OK:
                dlg.Destroy()
                return #we cancelled
                
            args['FieldNames'] = dlg.GetFieldNames()
            args['VarName'] = dlg.GetVarName()
            # args['PixelSize'] = dlg.GetPixelSize()
            
            
            dlg.Destroy()

        else: #assume it's a text file
            from PYME.LMVis import importTextDialog
            
            dlg = importTextDialog.ImportTextDialog(self, filename)
            ret = dlg.ShowModal()

            if not ret == wx.ID_OK:
                dlg.Destroy()
                return #we cancelled


            args['FieldNames'] = dlg.GetFieldNames()
            # remove trailing whitespace/line brake on last field name
            args['FieldNames'][-1] = args['FieldNames'][-1].rstrip()
            args['SkipRows'] = dlg.GetNumberComments()
            args['PixelSize'] = dlg.GetPixelSize()
            
            #print 'Skipping %d rows' %args['SkipRows']
            dlg.Destroy()

        print('Creating Pipeline')
        self.pipeline.OpenFile(filename, **args)
        print('Pipeline Created')
        
        
        #############################
        #now do all the gui stuff
        if isinstance(self, wx.Frame):
            #run this if only we are the main frame
            self.SetTitle('PYME Visualise - ' + filename)
            self._removeOldTabs()
            self._createNewTabs()
            
            self.CreateFoldPanel()
            print('Gui stuff done')
        
        self.SetFit()
        
        #wx.CallAfter(self.RefreshView)
        
