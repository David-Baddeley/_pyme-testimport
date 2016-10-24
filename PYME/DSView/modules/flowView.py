# -*- coding: utf-8 -*-
"""
Created on Wed Mar 11 21:15:36 2015

@author: david
"""

import wx
#import wx.html2
#import wx.lib.mixins.listctrl as listmix

import PYME.ui.autoFoldPanel as afp
import numpy as np
#import pandas as pd
import pylab

from traits.api import HasTraits, Float, File, BaseEnum, Enum, List, Instance, CStr, Bool, Int, ListInstance, on_trait_change
from traitsui.api import View, Item, Group     

class FlowView(HasTraits):    
    showFlow = Bool(True)
    flowVectWidth = Int(3)
    flowVectSpacing = Int(3)
    flowVectScale = Float(10)
    flowVectArrowSize = Float(1)
    flowImageName = CStr('outFlow')
    flowMaskName = CStr('outFlowMask')
    flowVectThresh = Float(0)
    
    traits_view = View(Item('showFlow'),
                             Item('flowImageName'),
                             Item('flowVectWidth'),
                             Item('flowVectSpacing'),
                             Item('flowVectScale'),
                             Item('flowVectArrowSize'),
                             Item('flowVectThresh'),
                    )
    
    def __init__(self, dsviewer):
        HasTraits.__init__(self)
        
        self._dsviewer = dsviewer
        self._view = dsviewer.view
        self._do = dsviewer.do
        #self.image = dsviewer.image
        
        self._penCols = [wx.Colour(*pylab.cm.hsv(v, bytes=True)) for v in np.linspace(0, 1, 16)]
        self._penColsA = [wx.Colour(*pylab.cm.hsv(v, alpha=0.5, bytes=True)) for v in np.linspace(0, 1, 16)]
        self.CreatePens()

        
        dsviewer.do.overlays.append(self.DrawOverlays)

        dsviewer.paneHooks.append(self.GenFlowPanel)
        
    def Unplug(self):
        self._dsviewer.do.overlays.remove(self.DrawOverlays)
        self._dsviewer.paneHooks.remove(self.GenFlowPanel)
    
    @on_trait_change('flowVectWidth')    
    def CreatePens(self):
        #self.candPens = [wx.Pen(c, self.candLineWidth, wx.DOT) for c in self.penCols]
        #self.chosenPens = [wx.Pen(c, self.chosenLineWidth) for c in self.penCols]
        self._vecPens = [wx.Pen(c, self.flowVectWidth) for c in self._penColsA]
        #self.selectedPens = [wx.Pen(c, self.selectedLineWidth) for c in self.penCols]

    def GenFlowPanel(self, _pnl):
        item = afp.foldingPane(_pnl, -1, caption="Flow Visualization", pinned = True)
        
        pan = self.edit_traits(parent=item, kind='panel')
        item.AddNewElement(pan.control)
        
        
        _pnl.AddPane(item)
        

    @property
    def flowImage(self):
        try:
            return self._dsviewer.recipes.activeRecipe.namespace[self.flowImageName]
        except KeyError:
            return None
            
        
    def DrawOverlays_(self, view, dc): 
        flow = self.flowImage
        
        if (not self.showFlow) or flow is None:
            return
        
        xb, yb, zb = view._calcVisibleBounds()
        x0, x1 = xb
        y0, y1 = yb 
                
        z = self._do.zp
        
        flow_x = flow.data[:, :, z, 0].squeeze()
        flow_y = flow.data[:, :, z, 1].squeeze()

        dc.SetBrush(wx.TRANSPARENT_BRUSH) 
        dc.SetPen(self._vecPens[0])
        
        step = int(self.flowVectSpacing)
        scale = float(self.flowVectScale)
        arrowSize = float(self.flowVectArrowSize)
        
        for x in np.arange(x0,min(x1, flow_x.shape[0]), step, dtype='i'):
            for y in np.arange(y0, min(y1, flow_y.shape[1]), step, dtype='i'):
                fx = flow_x[x, y]
                fy = flow_y[x, y]
                

                
                x_1, y_1 = x + scale*fx, y + scale*fy
                
                xs, ys = view._PixelToScreenCoordinates(x, y)
                xs1, ys1 = view._PixelToScreenCoordinates(x_1, y_1)
                
                dc.DrawLine(xs, ys, xs1, ys1)
                
                #now for the arrowhead - normal vectors in each direction                
                l = np.sqrt(fx*fx + fy*fy)
                
                h = np.array([x_1, y_1])
                
                fh = np.array([fx/l, fy/l])
                fhh = np.array([-fy/l, fx/l])
                
                t1 = h + arrowSize*(.5*fhh - fh)
                t2 = h + arrowSize*(-.5*fhh - fh)
                
                xt1, yt1 = view._PixelToScreenCoordinates(*t1)
                xt2, yt2 = view._PixelToScreenCoordinates(*t2)
                
                dc.DrawLine(xs1, ys1, xt1, yt1)
                dc.DrawLine(xs1, ys1, xt2, yt2)
                
                
                
    def DrawOverlays(self, view, dc): 
        flow = self.flowImage
        
        if (not self.showFlow) or flow is None:
            return
        
        xb, yb, zb = view._calcVisibleBounds()
        x0, x1 = xb
        y0, y1 = yb 
                
        z = self._do.zp
        
        flow_x = flow.data[:, :, z, 0].squeeze()
        flow_y = flow.data[:, :, z, 1].squeeze()

        dc.SetBrush(wx.TRANSPARENT_BRUSH) 
        dc.SetPen(self._vecPens[0])
        
        step = int(self.flowVectSpacing)
        scale = float(self.flowVectScale)
        arrowSize = float(self.flowVectArrowSize)
        
        #for x in np.arange(x0,min(x1, flow_x.shape[0]), step, dtype='i'):
        #    for y in np.arange(y0, min(y1, flow_y.shape[1]), step, dtype='i'):
        
        fx = flow_x[x0:x1:step, y0:y1:step].ravel()
        fy = flow_y[x0:x1:step, y0:y1:step].ravel()
        
        #flow magnitude        
        l = np.sqrt(fx*fx + fy*fy)
                
        x, y = np.mgrid[x0:min(x1, flow_x.shape[0]):step, y0:min(y1, flow_y.shape[1]):step]
        x = x.ravel()
        y = y.ravel()
        
        #don't draw any vectors which are below the cutoff length
        f_t_mask = l > self.flowVectThresh
        
        fx = fx[f_t_mask]
        fy = fy[f_t_mask]
        
        x = x[f_t_mask]
        y = y[f_t_mask]
        l = l[f_t_mask]
                
        x_1, y_1 = x + scale*fx, y + scale*fy
                
        xs, ys = view._PixelToScreenCoordinates(x, y)
        xs1, ys1 = view._PixelToScreenCoordinates(x_1, y_1)
                
        dc.DrawLineList(np.array([xs, ys, xs1, ys1]).T)
                
        #now for the arrowhead - normal vectors in each direction                
        
        
        h = np.array([x_1, y_1])
        
        fh = np.array([fx/l, fy/l])
        fhh = np.array([-fy/l, fx/l])
        
        t1 = h + arrowSize*(.5*fhh - fh)
        t2 = h + arrowSize*(-.5*fhh - fh)
        
        xt1, yt1 = view._PixelToScreenCoordinates(*t1)
        xt2, yt2 = view._PixelToScreenCoordinates(*t2)
        
        dc.DrawLineList(np.array([xs1, ys1, xt1, yt1]).T)
        dc.DrawLineList(np.array([xs1, ys1, xt2, yt2]).T)
#                
                
                
                        

        
  

def Plug(dsviewer):
    #from PYME.DSView import htmlServe #ensure that our local cherrypy server is running
    dsviewer.flowView = FlowView(dsviewer)
    #cherrypy.tree.mount(dsviewer.tracker, '/tracks')
    #dsviewer.tracker.trackview.LoadURL(htmlServe.getURL() + 'tracks/')
    
def Unplug(dsviewer):
    dsviewer.flowView.Unplug()
    
