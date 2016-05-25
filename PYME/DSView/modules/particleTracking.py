# -*- coding: utf-8 -*-
"""
Created on Wed Mar 11 21:15:36 2015

@author: david
"""

import wx
import wx.html2
import wx.lib.mixins.listctrl as listmix

import PYME.ui.autoFoldPanel as afp
import numpy as np
#import pandas as pd
import pylab

from PYME.recipes.tracking import TrackFeatures

import cherrypy

from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('PYME.DSView.modules', 'templates'))

def movieplot(clump, image):
    import matplotlib.pyplot as plt
    import mpld3
    
    plt.ioff()
    nRows = int(np.ceil(clump.nEvents/10.))
    f = plt.figure(figsize=(12,1.2*nRows))
    
    #msdi = self.msdinfo
    #t = msdi['t']
    #plt.plot(t[1:], msdi['msd'][1:])
    #plt.plot(t, powerMod2D([msdi['D'], msdi['alpha']], t))
    
    xp, yp = clump['centroid'][0]
    
    xp = int(np.round(xp))
    yp = int(np.round(yp))
    
    contours = clump['contour']
    
    for i in range(clump.nEvents):
        plt.subplot(nRows, min(clump.nEvents, 10), i+1)
        if image.data.shape[3] == 1:
            #single color
            img = image.data[(xp - 20):(xp + 20), (yp - 20):(yp + 20), clump['t'][i]].squeeze()
            plt.imshow(img.T, interpolation ='nearest', cmap=plt.cm.gray, clim=[0, clump.featuremean['mean_intensity']*1.5])

        else:
            img = np.zeros([40,40,3], 'uint8')
            
            for j in range(min(image.data.shape[3], 3)):
                im_j = image.data[(xp - 20):(xp + 20), (yp - 20):(yp + 20), clump['t'][i], j].squeeze().T.astype('f')
                img[:,:,j] = np.clip(255.*im_j/(clump.featuremean['mean_intensity']*1.5), 0, 255).astype('uint8')
                
            plt.imshow(img, interpolation ='nearest')
            
        
        xc, yc = contours[i].T
        plt.plot(xc - xp + 20, yc - yp + 20, c='b')#plt.cm.hsv(clump.clumpID/16.))

        xsb = 5
        ysb = 5
        plt.plot([xsb, xsb+ 200./image.pixelSize], [ysb,ysb], 'y', lw=4)        
        
        plt.xticks([])
        plt.yticks([])
        plt.axis('image')
        plt.axis('off')
   
    
    plt.tight_layout(pad=1)
    
    plt.ion()
    
    return mpld3.fig_to_html(f)
    
env.filters['movieplot'] = movieplot


#from PYME.Analysis.Tracking import tracking
#from PYME.Analysis.Tracking import trackUtils

from traits.api import HasTraits, Float, File, BaseEnum, Enum, List, Instance, CStr, Bool, Int, ListInstance, on_trait_change
from traitsui.api import View, Item, Group

class TrackList(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES|wx.LC_SINGLE_SEL, size=(250, 400))
        #listmix.CheckListCtrlMixin.__init__(self)
        self.InsertColumn(0, 'Track ID')
        self.InsertColumn(1, 'Length')
        self.InsertColumn(2, 'Enabled')
        
        self.clumps = []
        
        #self.SetItemCount(100)
        
    def OnCheckItem(self, index, flag):
        print(index, flag)
        
    def OnGetItemText(self, item, col):
        if col == 0:
            return self.clumps[item].clumpID
        if col == 1:
            return self.clumps[item].nEvents
        elif col == 2:
            return str(self.clumps[item].enabled)
        else:
            return ''
        
    def SetClumps(self, clumps):
        self.clumps = clumps
        self.SetItemCount(len(self.clumps))

#    def OnGetItemImage(self, item):
#        if item % 3 == 0:
#            return self.idx1
#        else:
#            return self.idx2

#    def OnGetItemAttr(self, item):
#        if item % 3 == 1:
#            return self.attr1
#        elif item % 3 == 2:
#            return self.attr2
#        else:
#            return None


        

class ParticleTrackingView(HasTraits):
    #features = CStr('x, y')    
    #pNew = Float(0.2)
    #r0 = Float(500)
    #pLinkCutoff = Float(0.2)
    
    #minTrackLength = Int(5)
    #maxParticleSize = Float(20)
    tracker = Instance(TrackFeatures, ())
    
    showTracks = Bool(True)
    showSelectedTrack = Bool(True)
    showCandidates = Bool(False)
    showTrackIDs = Bool(False)
    
    candLineWidth = Int(4)
    chosenLineWidth = Int(5)
    trackLineWidth = Int(2)
    selectedLineWidth = Int(5)
    
    traits_view = View(Group(Item('object.tracker.features'),
                             Item('object.tracker.pNew'),
                             Item('object.tracker.r0'),
                             Item('object.tracker.pLinkCutoff'),
                             Item('object.tracker.minTrackLength'),
                             Item('object.tracker.maxParticleSize'), label='Linkage'),
                       Group(Item(name = 'showTracks'),
                             Item(name = 'showTrackIDs'),
                             Item(name = 'showSelectedTrack'),
                             Item(name = 'showCandidates'),
                             label= 'Display'))
    
    def __init__(self, dsviewer, tracker = None, clumps=[]):
        HasTraits.__init__(self)
        if tracker == None:
            self.tracker = TrackFeatures()
        else:
            self.tracker = tracker
        
        self.clumps = []
        
        self.dsviewer = dsviewer
        self.view = dsviewer.view
        self.do = dsviewer.do
        self.image = dsviewer.image
        
        #self.tracker = None
        self.selectedTrack = None
        
        #self.clumps = []
        
        if 'tracks' in dir(self.image):
            self.SetTracks(self.image.tracks)
        
        self.penCols = [wx.Colour(*pylab.cm.hsv(v, bytes=True)) for v in np.linspace(0, 1, 16)]
        self.penColsA = [wx.Colour(*pylab.cm.hsv(v, alpha=0.5, bytes=True)) for v in np.linspace(0, 1, 16)]
        self.CreatePens()

        self.trackview = wx.html2.WebView.New(dsviewer)
        dsviewer.AddPage(self.trackview, True, 'Track Info')  
        
        dsviewer.do.overlays.append(self.DrawOverlays)

        dsviewer.paneHooks.append(self.GenTrackingPanel)
    
    @on_trait_change('candLineWidth, chosenLineWidth, trackLineWidth')    
    def CreatePens(self):
        self.candPens = [wx.Pen(c, self.candLineWidth, wx.DOT) for c in self.penCols]
        self.chosenPens = [wx.Pen(c, self.chosenLineWidth) for c in self.penCols]
        self.trackPens = [wx.Pen(c, self.trackLineWidth) for c in self.penColsA]
        self.selectedPens = [wx.Pen(c, self.selectedLineWidth) for c in self.penCols]

    def GenTrackingPanel(self, _pnl):
        item = afp.foldingPane(_pnl, -1, caption="Particle Tracking", pinned = True)
        
        pan = self.edit_traits(parent=item, kind='panel')
        item.AddNewElement(pan.control)
        

        bTrack = wx.Button(item, -1, 'Track')
        bTrack.Bind(wx.EVT_BUTTON, self.OnTrack)
        item.AddNewElement(bTrack)
        
        pan = wx.Panel(item, -1)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.list = TrackList(pan)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelectTrack)
        vsizer.Add(self.list, 1, wx.EXPAND)        
        
        pan.SetSizer(vsizer)
        vsizer.Fit(pan)


        item.AddNewElement(pan)
        
        bSave = wx.Button(item, -1, 'Save')
        bSave.Bind(wx.EVT_BUTTON, self.SaveTracks)
        item.AddNewElement(bSave)
        
        _pnl.AddPane(item)
        
        if not self.OnViewSelect in self.view.selectHandlers:
            self.view.selectHandlers.append(self.OnViewSelect)


    def OnTrack(self, event):     
        clumps = self.tracker.TrackWithPipeline(self.dsviewer.pipeline)
        self.SetTracks(clumps)
        
    def SetTracks(self, clumps):
        self.clumps = clumps        
        self.list.SetClumps(self.clumps)
        
    def OnSelectTrack(self, event):
        self.selectedTrack = self.clumps[event.m_itemIndex]
        template = env.get_template('trackView.html')
        self.trackview.SetPage(template.render(clump=self.selectedTrack, img=self.dsviewer.image), '')
        
    def OnViewSelect(self, view):
        #select a track by clicking on it
        
        pos = (view.do.xp, view.do.yp, view.do.zp)
        
        candidates = [i for i, c in enumerate(self.clumps) if self._hittest(c, pos)]
        
        if len(candidates) > 0:
            item = candidates[0] #take the first hit
            self.list.SetItemState(item, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

        
    def DrawOverlays(self, view, dc):    
        if self.showTracks and (len(self.clumps) > 0):
            bounds = view._calcVisibleBounds()
            vx, vy, vz = self.image.voxelsize
            visibleClumps = [c for c in self.clumps if self._visibletest(c, bounds)]
            
            dc.SetBrush(wx.TRANSPARENT_BRUSH)

            for c in visibleClumps:
                x = c['x']/vx
                y = c['y']/vy
                t = c['t']
                pFoc = np.vstack(view._PixelToScreenCoordinates3D(x, y, t)).T
                
                #print pFoc.shape
                if c == self.selectedTrack:
                    dc.SetPen(self.selectedPens[c.clumpID%16])
                else:
                    dc.SetPen(self.trackPens[c.clumpID%16])
                dc.DrawLines(pFoc)
                
                if self.showTrackIDs:
                    x0, y0 = pFoc[0]
                    dc.SetTextForeground(self.penCols[c.clumpID%16])
                    dc.DrawText('%d' % c.clumpID, x0, y0 + 1)
                    
                
        if self.showSelectedTrack and not self.showTracks and (len(self.clumps) > 0):
            vx, vy, vz = self.image.voxelsize
            c = self.selectedTrack
            x = c['x']/vx
            y = c['y']/vy
            t = c['t']
            
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            
            pFoc = np.vstack(view._PixelToScreenCoordinates3D(x, y, t)).T
            
            dc.SetPen(self.selectedPens[c.clumpID%16])
            
            dc.DrawLines(pFoc)
                
        if self.showCandidates and not (self.tracker == None):
            if view.do.zp >=1:
                iCurr = view.do.zp
                iPrev = view.do.zp-1
                links = self.tracker.tracker.calcLinkages(iCurr, iPrev)
                
                #pRed = wx.Pen(wx.TheColourDatabase.FindColour('RED'),2)
                pRedDash = wx.Pen(wx.TheColourDatabase.FindColour('RED'),2, wx.SHORT_DASH)
                dc.SetPen(pRedDash)
                
                dc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))                
                dc.SetTextForeground(wx.TheColourDatabase.FindColour('YELLOW'))
                
                for curFrameIndex, linkInfo in links.items():
                    inds = self.tracker.tracker.indicesByT[iCurr]
                    i = inds[curFrameIndex]
                    
                    x1 = self.dsviewer.pipeline['x'][i]/self.image.voxelsize[0] 
                    y1 = self.dsviewer.pipeline['y'][i]/self.image.voxelsize[1]
                    
                    x1s, y1s = view._PixelToScreenCoordinates(x1, y1)
                    
                    linkSrcs, linkPs = linkInfo
                    n = 0
                    for ls, lp in zip(linkSrcs, linkPs):
                        if n == 0:
                            dc.SetPen(self.chosenPens[self.tracker.clumpIndex[ls]%16])
                        else:
                            dc.SetPen(self.candPens[self.tracker.clumpIndex[ls]%16])
                            
                        if ls == -1:
                            #new object
                            x0 = x1
                            y0 = y1 - 10
                            
                        else:
                            x0 = self.dsviewer.pipeline['x'][ls]/self.image.voxelsize[0]
                            y0 = self.dsviewer.pipeline['y'][ls]/self.image.voxelsize[1]
                        
                        x0s, y0s = view._PixelToScreenCoordinates(x0, y0)
                        dc.DrawLine(x0s, y0s, x1s, y1s)
                        
                        if ls == -1:
                            dc.DrawText('N', x0s, y0s + 1)
                        dc.DrawText('%1.1f'%lp, (x0s+x1s)/2 + 2, (y0s+y1s)/2 + 2)
                        n += 1
                        
    def _visibletest(self, clump, bounds):
        if (not clump.enabled) or (clump.nEvents < 2):
            return False
            
        xb, yb, zb = bounds
        vx, vy, vz = self.image.voxelsize
        
        x = clump['x']/vx
        y = clump['y']/vy
        t = clump['t']
        
        return np.any((x >= xb[0])*(y >= yb[0])*(t >= (zb[0]-1))*(x < xb[1])*(y < yb[1])*(t < (zb[1]+1)))
        
    def _hittest(self, clump, pos):
        xp, yp, zp = pos
        
        bounds = [(xp-2, xp+2), (yp -2, yp + 2), (zp-15, zp+15)]
        
        return self._visibletest(clump, bounds)
        
        
        
    @cherrypy.expose
    def index(self):
        template = env.get_template('tracksOverview.html')
        
        return template.render(clumps = self.clumps)
        
        
    def SaveTracks(self, event=None):
        import os        
        filename = wx.FileSelector('Save tracks as ...', 
                                   wildcard="HDF5 (*.hdf)|*.hdf", 
                                   flags = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
                                   
        if not filename == '':
            #load the template for creating the html track report
            template = env.get_template('trackView.html')

            #convert pipeline to a pandas dataframe, and save            
            df = self.dsviewer.pipeline.toDataFrame()
            if filename.endswith('.csv'):
                df.to_csv(filename)
            elif filename.endswith('.hdf'):
                df.to_hdf(filename, 'Results')
                
            fstub, ext = os.path.splitext(filename) 
            dirname = fstub + '_tracks'
            
            os.makedirs(dirname)
            
            for c in self.clumps:
                if c.enabled:
                    html_file = os.path.join(dirname, 'track_%d.html' % c.clumpID)
                    raw_file = os.path.join(dirname, 'track_%d.csv' % (c.clumpID, ))
                    
                    with open(html_file, 'w') as f:
                        f.write(template.render(clump=c))
                        
                    c.save(raw_file, ['t', 'x', 'y', 'area', 'eccentricity', 
                    'equivalent_diameter', 'extent', 'major_axis_length', 'max_intensity', 
                    'mean_intensity', 'min_intensity', 'minor_axis_length',  'orientation', 
                    'perimeter', 'solidity', 'clumpIndex'])
            
                    
                    
                    
                    
                    

        
  

def Plug(dsviewer):
    from PYME.DSView import htmlServe #ensure that our local cherrypy server is running
    htmlServe.StartServing()
    
    dsviewer.tracker = ParticleTrackingView(dsviewer)
    cherrypy.tree.mount(dsviewer.tracker, '/tracks')
    dsviewer.tracker.trackview.LoadURL(htmlServe.getURL() + 'tracks/')
