#!/usr/bin/python

##################
# myviewpanel_numarray.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################


import wx
import sys
sys.path.append(".")
import viewpanelN
#import PYME.cSMI as example
import numpy
import scipy
import tables
import time
from matplotlib import cm

class ListWrap:
    def __init__(self, dataList):
        self.dataList = dataList
        self.wrapList = [DataWrap(d) for d in dataList]

        self.listDim = self.wrapList[0].nTrueDims

        self.shape = self.wrapList[0].shape[:self.listDim] + (len(self.wrapList), 1, 1, 1)

    def __getattr__(self, name):
        return getattr(self.wrapList[0], name)

    def __getitem__(self, keys):
        keys = list(keys)
        #print keys

        kL = keys[self.listDim]

        return self.wrapList[kL].__getitem__(keys[:self.listDim])


class DataWrap: #permit indexing with more dimensions larger than len(shape)
    def __init__(self, data):
        self.data = data
        self.type = 'Array'

        self.dim_1_is_z = False

        if not data.__class__ == numpy.ndarray and not data.__class__ == tables.EArray: # is a data source
            self.type = 'DataSource'
            self.shape = data.getSliceShape() + (data.getNumSlices(),)
            #print self.shape
            self.data.shape = self.shape
            self.dim_1_is_z = True
        
        self.nTrueDims = len(data.shape)
        self.shape = data.shape + (1, 1, 1, 1, 1)
        self.oldData = None
        self.oldSlice = None #buffer last lookup


        if data.__class__ == tables.EArray:
             self.dim_1_is_z = True
             self.shape = self.shape[1:3] + (self.shape[0],) + self.shape[3:]

    def __getattr__(self, name):
        return getattr(self.data, name)
    
    def __getitem__(self, keys):
        keys = list(keys)
        #print keys
        for i in range(len(keys)):
            if not keys[i].__class__ == slice:
                keys[i] = slice(keys[i],keys[i] + 1)
        if keys == self.oldSlice:
            return self.oldData
        self.oldSlice = keys
        if len(keys) > len(self.data.shape):
            #return self.data.__getitem__(keys)
            #print keys[:len(self.data.shape)]
            keys = keys[:len(self.data.shape)]
        if self.dim_1_is_z:
            keys = [keys[2]] + keys[:2] + keys[3:]
        #print keys
        if self.type == 'Array':
            r = self.data.__getitem__(keys)
        else:
            #print keys[0]
            #print numpy.mgrid[keys[0]]
            r = numpy.concatenate([self.data.getSlice(i)[keys[1], keys[2]][:,:,None] for i in numpy.mgrid[keys[0]] if i < self.data.getNumSlices()], 2)
#        if self.dim_1_is_z and len(numpy.mgrid[keys[0]]) == 1: #and keys[0].__class__ == slice
#            r = r.T
        self.oldData = r
        #print r.max()
        return r
        
class DisplayOpts:
    UPRIGHT, ROT90 = range(2)
    SLICE_XY, SLICE_XZ, SLICE_YZ = range(3)
    
    def __init__(self, nchans=1):
        if nchans ==1:
            self.Chans = [0]
            self.Gains = [1]
            self.Offs = [0]
            self.cmaps = [viewpanelN.fast_grey]
        else:
            self.Chans = []
            self.Gains = []
            self.Offs = []
            self.cmaps = []

            cms = [cm.r, cm.g, cm.b]

            for i in range(nchans):
                self.Chans.append(i)
                self.Gains.append(1.)
                self.Offs.append(0.)
                self.cmaps.append(cms[i%len(cms)])


        self.orientation = self.UPRIGHT
        self.slice = self.SLICE_XY
        self.aspects = [1.,1.,1.]
    
    def Optimise(self,data, zp = 0):
        if len(data.shape) == 2:
            self.Offs[0] = 1.*data.min()
            self.Gains[0] =1./(data.max()- data.min())
        elif len(data.shape) ==3:
            self.Offs[0] = 1.*data[:,:,zp].min()
            self.Gains[0] =1./(data[:,:,zp].max()- data[:,:,zp].min())
        else:
            for i in range(len(self.Chans)):
                self.Offs[i] = data[:,:,zp,self.Chans[i]].min()
                self.Gains[i] = 1.0/(data[:,:,zp,self.Chans[i]].max() - self.Offs[i])
            
class MyViewPanel(viewpanelN.ViewPanel):
    def __init__(self, parent, dstack = None, aspect=None):
        
        if (dstack is None):
            scipy.zeros(10,10)
        else:
            self.ds = dstack

        self.xp = 0
        self.yp=0
        self.zp=0

        self.aspect = 1.0
        
        #print self.ds.__class__
        if self.ds.__class__ ==list:
            self.ds = ListWrap(self.ds)
        else:
            self.ds = DataWrap(self.ds)

        self.do = DisplayOpts(self.ds.shape[3])

        if not aspect is None:
            if scipy.isscalar(aspect):
                self.do.aspects[2] = aspect
            elif len(aspect) == 3:
                self.do.aspects = aspect

        if (len(self.ds.shape) >3) and (self.ds.shape[3] >= 2):
            self.do.Chans[1] = 1
            if (self.ds.shape[3] >=3):
                self.do.Chans[2] = 2
        self.do.Optimise(self.ds, self.zp)

        viewpanelN.ViewPanel.__init__(self, parent, -1)

        self.imagepanel.SetVirtualSize(wx.Size(self.ds.shape[0],self.ds.shape[1]))
        #self.imagepanel.SetSize(wx.Size(self.ds.shape[0],self.ds.shape[1]))
        
        
        if (len(self.ds.shape) >3) and (self.ds.shape[3] >= 2):
            self.do.Chans[1] = 1
            if (self.ds.shape[3] >=3):
                self.do.Chans[2] = 2
        self.do.Optimise(self.ds, self.zp)

        self.points =[]
        self.pointsR = []
        self.pointMode = 'confoc'
        self.pointTolNFoc = {'confoc' : (5,5,5), 'lm' : (2, 5, 5), 'splitter' : (2,5,5)}

        self.psfROIs = []
        self.psfROISize=[30,30,30]

        self.lastUpdateTime = 0
        self.lastFrameTime = 2e-3

        self.scale = 2
        self.crosshairs = True
        self.selection = True
        
        self.ResetSelection()
        #self.SetOpts()
        self.optionspanel.RefreshHists()
        self.updating = 0
        self.showOptsPanel = 1

        self.refrTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnRefrTimer)

        #wx.EVT_PAINT(self.imagepanel.impanel, self.OnPaint)
        wx.EVT_MOUSEWHEEL(self, self.OnWheel)
        wx.EVT_KEY_DOWN(self.imagepanel.impanel, self.OnKeyPress)
        wx.EVT_LEFT_UP(self.imagepanel.impanel, self.OnLeftClick)
        
        wx.EVT_RIGHT_DOWN(self.imagepanel.impanel, self.OnRightDown)
        wx.EVT_RIGHT_UP(self.imagepanel.impanel, self.OnRightUp)
#        wx.EVT_COMBOBOX(self,self.cbRedChan.GetId(), self.GetOpts)
#        wx.EVT_COMBOBOX(self,self.cbGreenChan.GetId(), self.GetOpts)
#        wx.EVT_COMBOBOX(self,self.cbBlueChan.GetId(), self.GetOpts)
#        wx.EVT_COMBOBOX(self,self.cbSlice.GetId(), self.GetOpts)
#        wx.EVT_COMBOBOX(self,self.cbScale.GetId(), self.GetOpts)
#        wx.EVT_TEXT(self,self.tRedGain.GetId(), self.GetOpts)
#        wx.EVT_TEXT(self,self.tRedOff.GetId(), self.GetOpts)
#        wx.EVT_TEXT(self,self.tGreenGain.GetId(), self.GetOpts)
#        wx.EVT_TEXT(self,self.tGreenOff.GetId(), self.GetOpts)
#        wx.EVT_TEXT(self,self.tBlueGain.GetId(), self.GetOpts)
#        wx.EVT_TEXT(self,self.tBlueOff.GetId(), self.GetOpts)
#        wx.EVT_BUTTON(self, self.bOptimise.GetId(), self.Optim)
        wx.EVT_BUTTON(self, self.bShowOpts.GetId(), self.ShowOpts)
        wx.EVT_ERASE_BACKGROUND(self.imagepanel.impanel, self.DoNix)
        wx.EVT_ERASE_BACKGROUND(self, self.DoNix)

    def OnRefrTimer(self, event):
        self.Refresh()
        
    def SetDataStack(self, ds):
        self.ds = DataWrap(ds)
        self.imagepanel.SetVirtualSize(wx.Size(self.ds.shape[0],self.ds.shape[1]))
        
        #if len(self.ds.shape) == 2:
        #    self.ds = self.ds.reshape(self.ds.shape + (1,))
        
        #if len(self.ds.shape) == 3:
        #    self.ds = self.ds.reshape(self.ds.shape + (1,))
        self.do =DisplayOpts()
        if (len(self.ds.shape) >3) and (self.ds.shape[3] >= 2):
            self.do.Chans[1] = 1
            if (self.ds.shape[3] >=3):
                self.do.Chans[2] = 2
        self.xp = 0
        self.yp=0
        self.zp=0
        self.do.Optimise(self.ds, self.zp)
        
            
        self.ResetSelection()
        #self.SetOpts()

        self.Layout()
        self.Refresh()

    def ResetDataStack(self, ds):
        #print ds.__class__
        if ds.__class__ ==list:
            self.ds = ListWrap(ds)
        else:
            self.ds = DataWrap(ds)
        #self.ds = DataWrap(ds)
        self.Refresh()
        
    def DoPaint(self, dc):
        #dc = wx.PaintDC(self.imagepanel)
        #self.imagepanel.PrepareDC(dc)
        #dc.BeginDrawing()
        #mdc = wx.MemoryDC(dc)
        
        #s = self.CalcImSize()
        #im = wx.EmptyImage(s[0],s[1])
        #bmp = im.GetDataBuffer()
        #self.rend.pyRender(bmp,self.ds)

        #print self.imagepanel.CalcUnscrolledPosition(0,0)

        dc.Clear()
                                     
        im = self.Render()

        #print im.max()
        
        sc = pow(2.0,(self.scale-2))
        im.Rescale(im.GetWidth()*sc,im.GetHeight()*sc*self.aspect)
        #dc.DrawBitmap(wx.BitmapFromImage(im),wx.Point(0,0))

        x0,y0 = self.imagepanel.CalcUnscrolledPosition(0,0)
        dc.DrawBitmap(wx.BitmapFromImage(im),-sc/2,-sc/2)
        #mdc.SelectObject(wx.BitmapFromImage(self.im))
        #mdc.DrawBitmap(wx.BitmapFromImage(self.im),wx.Point(0,0))
        #dc.Blit(0,0,im.GetWidth(), im.GetHeight(),mdc,0,0)
        #dc.EndDrawing()

        #sX, sY = self.imagepanel.GetVirtualSize()
        sX, sY = im.GetWidth(), im.GetHeight()

        if self.crosshairs:
            dc.SetPen(wx.Pen(wx.CYAN,0))
            if(self.do.slice == self.do.SLICE_XY):
                lx = self.xp
                ly = self.yp
            elif(self.do.slice == self.do.SLICE_XZ):
                lx = self.xp
                ly = self.zp
            elif(self.do.slice == self.do.SLICE_YZ):
                lx = self.yp
                ly = self.zp
        
            #dc.DrawLine((0, ly*sc), (im.GetWidth(), ly*sc))
            #dc.DrawLine((lx*sc, 0), (lx*sc, im.GetHeight()))
            if (self.do.orientation == self.do.UPRIGHT):
                dc.DrawLine(0, ly*sc*self.aspect - y0, sX, ly*sc*self.aspect - y0)
                dc.DrawLine(lx*sc - x0, 0, lx*sc - x0, sY)
            else:
                dc.DrawLine(0, lx*sc - y0, sX, lx*sc - y0)
                dc.DrawLine(ly*sc - x0, 0, ly*sc - x0, sY)
            dc.SetPen(wx.NullPen)
            
        if self.selection:
            dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('YELLOW'),0))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            if(self.do.slice == self.do.SLICE_XY):
                lx = self.selection_begin_x
                ly = self.selection_begin_y
                hx = self.selection_end_x
                hy = self.selection_end_y
            elif(self.do.slice == self.do.SLICE_XZ):
                lx = self.selection_begin_x
                ly = self.selection_begin_z
                hx = self.selection_end_x
                hy = self.selection_end_z
            elif(self.do.slice == self.do.SLICE_YZ):
                lx = self.selection_begin_y
                ly = self.selection_begin_z
                hx = self.selection_end_y
                hy = self.selection_end_z
        
            #dc.DrawLine((0, ly*sc), (im.GetWidth(), ly*sc))
            #dc.DrawLine((lx*sc, 0), (lx*sc, im.GetHeight()))
            #dc.DrawLine(lx, ly*sc, im.GetWidth(), ly*sc)
            #dc.DrawLine(lx*sc, 0, lx*sc, im.GetHeight())
            
            #(lx*sc,ly*sc, (hx-lx)*sc,(hy-ly)*sc)
            if (self.do.orientation == self.do.UPRIGHT):
                dc.DrawRectangle(lx*sc - x0,ly*sc*self.aspect - y0, (hx-lx)*sc,(hy-ly)*sc*self.aspect)
            else:
                dc.DrawRectangle(ly*sc - x0,lx*sc - y0, (hy-ly)*sc,(hx-lx)*sc)
            dc.SetPen(wx.NullPen)
            dc.SetBrush(wx.NullBrush)

        if (len(self.psfROIs) > 0):
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('GREEN'),0))
            if(self.do.slice == self.do.SLICE_XY):
                for p in self.psfROIs:
                    dc.DrawRectangle(sc*p[0]-self.psfROISize[0]*sc - x0,sc*p[1] - self.psfROISize[1]*sc - y0, 2*self.psfROISize[0]*sc,2*self.psfROISize[1]*sc)
            elif(self.do.slice == self.do.SLICE_XZ):
                for p in self.psfROIs:
                    dc.DrawRectangle(sc*p[0]-self.psfROISize[0]*sc - x0,sc*p[2]*self.aspect - self.psfROISize[2]*sc*self.aspect - y0, 2*self.psfROISize[0]*sc,2*self.psfROISize[2]*sc*self.aspect)
            elif(self.do.slice == self.do.SLICE_YZ):
                for p in self.psfROIs:
                    dc.DrawRectangle(sc*p[1]-self.psfROISize[1]*sc - x0,sc*p[2]*self.aspect - self.psfROISize[2]*sc*self.aspect - y0, 2*self.psfROISize[1]*sc,2*self.psfROISize[2]*sc*self.aspect)


        if len(self.points) > 0:
            #if self.pointsMode == 'confoc':
            pointTol = self.pointTolNFoc[self.pointMode]
            if(self.do.slice == self.do.SLICE_XY):
                pFoc = self.points[abs(self.points[:,2] - self.zp) < 1][:,:2]
                if self.pointMode == 'splitter':
                    pCol = self.pointColours[abs(self.points[:,2] - self.zp) < 1]
                pNFoc = self.points[abs(self.points[:,2] - self.zp) < pointTol[0]][:,:2]

            elif(self.do.slice == self.do.SLICE_XZ):
                pFoc = self.points[abs(self.points[:,1] - self.yp) < 1][:, ::2]
                pNFoc = self.points[abs(self.points[:,1] - self.yp) < pointTol[1]][:,::2]

            else:#(self.do.slice == self.do.SLICE_YZ):
                pFoc = self.points[abs(self.points[:,0] - self.xp) < 1][:, 1:]
                pNFoc = self.points[abs(self.points[:,0] - self.xp) < pointTol[2]][:,1:]

            #pFoc = numpy.atleast_1d(pFoc)
            #pNFoc = numpy.atleast_1d(pNFoc)


            dc.SetBrush(wx.TRANSPARENT_BRUSH)

            dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('BLUE'),0))
            for p in pNFoc:
                dc.DrawRectangle(sc*p[0]-2*sc - x0,sc*p[1]*self.aspect - 2*sc*self.aspect - y0, 4*sc,4*sc*self.aspect)

                if self.pointMode == 'splitter' and self.do.slice == self.do.SLICE_XY:
                    dc.DrawRectangle(sc*p[0]-2*sc - x0,sc*(self.ds.shape[1] - p[1])*self.aspect - 2*sc*self.aspect - y0, 4*sc,4*sc*self.aspect)


            pGreen = wx.Pen(wx.TheColourDatabase.FindColour('GREEN'),0)
            pRed = wx.Pen(wx.TheColourDatabase.FindColour('RED'),0)
            dc.SetPen(pGreen)
            if self.pointMode == 'splitter' and self.do.slice == self.do.SLICE_XY:
                for p, c in zip(pFoc, pCol):
                    if c:
                        dc.SetPen(pGreen)
                    else:
                        dc.SetPen(pRed)
                    dc.DrawRectangle(sc*p[0]-2*sc - x0,sc*p[1]*self.aspect - 2*sc*self.aspect - y0, 4*sc,4*sc*self.aspect)
                    dc.DrawRectangle(sc*p[0]-2*sc - x0,sc*(self.ds.shape[1] - p[1])*self.aspect - 2*sc*self.aspect - y0, 4*sc,4*sc*self.aspect)
            else:
                for p in pFoc:
                    dc.DrawRectangle(sc*p[0]-2*sc - x0,sc*p[1]*self.aspect - 2*sc*self.aspect - y0, 4*sc,4*sc*self.aspect)



#            elif(self.do.slice == self.do.SLICE_XZ):
#                pFoc = self.points[abs(self.points[:,1] - self.yp) < 1]
#                pNFoc = self.points[abs(self.points[:,1] - self.yp) < pointTol[1]]
#
#
#                dc.SetBrush(wx.TRANSPARENT_BRUSH)
#
#                dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('BLUE'),0))
#                for p in pNFoc:
#                    dc.DrawRectangle(sc*p[0]-2*sc,sc*p[2] - 2*sc, 4*sc,4*sc)
#
#                dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('GREEN'),0))
#                for p in pFoc:
#                    dc.DrawRectangle(sc*p[0]-2*sc,sc*p[2] - 2*sc, 4*sc,4*sc)
#
#            else:#(self.do.slice == self.do.SLICE_YZ):
#                pFoc = self.points[abs(self.points[:,0] - self.xp) < 1]
#                pNFoc = self.points[abs(self.points[:,0] - self.xp) < pointTol[2] ]
#
#
#                dc.SetBrush(wx.TRANSPARENT_BRUSH)
#
#                dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('BLUE'),0))
#                for p in pNFoc:
#                    dc.DrawRectangle(sc*p[1]-2*sc,sc*p[2] - 2*sc, 4*sc,4*sc)
#
#                dc.SetPen(wx.Pen(wx.TheColourDatabase.FindColour('GREEN'),0))
#                for p in pFoc:
#                    dc.DrawRectangle(sc*p[1]-2*sc,sc*p[2] - 2*sc, 4*sc,4*sc)
            
            dc.SetPen(wx.NullPen)
            dc.SetBrush(wx.NullBrush)
            
    def OnPaint(self,event):
        self.painting = True
        DC = wx.PaintDC(self.imagepanel)
        if not time.time() > (self.lastUpdateTime + 2*self.lastFrameTime): #avoid paint floods
            if not self.refrTimer.IsRunning():
                self.refrTimer.Start(.2, True) #make sure we do get a refresh after disposing of flood
            return

        frameStartTime = time.time()
        self.imagepanel.impanel.PrepareDC(DC)

        x0,y0 = self.imagepanel.CalcUnscrolledPosition(0,0)
        
        #s = self.imagepanel.GetVirtualSize()
        s = self.imagepanel.impanel.GetClientSize()
        MemBitmap = wx.EmptyBitmap(s.GetWidth(), s.GetHeight())
        #del DC
        MemDC = wx.MemoryDC()
        OldBitmap = MemDC.SelectObject(MemBitmap)
        try:
            DC.BeginDrawing()
            #DC.Clear()
            #Perform(WM_ERASEBKGND, MemDC, MemDC);
            #Message.DC := MemDC;
            self.DoPaint(MemDC);
            #Message.DC := 0;
            #DC.BlitXY(0, 0, s.GetWidth(), s.GetHeight(), MemDC, 0, 0)
            DC.Blit(x0, y0, s.GetWidth(), s.GetHeight(), MemDC, 0, 0)
            DC.EndDrawing()
        finally:
            #MemDC.SelectObject(OldBitmap)
            del MemDC
            del MemBitmap

        self.lastUpdateTime = time.time()
        self.lastFrameTime = self.lastUpdateTime - frameStartTime

        self.painting = False
        #print self.lastFrameTime
            
    def OnWheel(self, event):
        rot = event.GetWheelRotation()
        if rot < 0:
            self.zp = (self.zp - 1)
        if rot > 0:
            self.zp = (self.zp + 1)
        if ('update' in dir(self.GetParent())):
             self.GetParent().update()
        else:
            self.imagepanel.impanel.Refresh()
    
    def OnKeyPress(self, event):
        if event.GetKeyCode() == wx.WXK_PRIOR:
            self.zp = max(0, self.zp - 1)
            self.optionspanel.RefreshHists()
            if ('update' in dir(self.GetParent())):
                self.GetParent().update()
            else:
                #if not self.painting:
                self.imagepanel.impanel.Refresh()
                #else:
                #    if not self.refrTimer.IsRunning():
                #        self.refrTimer.Start(.2, True)

        elif event.GetKeyCode() == wx.WXK_NEXT:
            self.zp = min(self.zp + 1, self.ds.shape[2] - 1)
            self.optionspanel.RefreshHists()
            if ('update' in dir(self.GetParent())):
                self.GetParent().update()
                #print 'upd'
            else:
                #if not self.painting:
                self.imagepanel.impanel.Refresh()
                #else:
                #    if not self.refrTimer.IsRunning():
                        #print 'upt'
                #        self.refrTimer.Start(.2, True)
                
        elif event.GetKeyCode() == 74:
            self.xp = (self.xp - 1)
            if ('update' in dir(self.GetParent())):
                self.GetParent().update()
            else:
                self.imagepanel.impanel.Refresh()
        elif event.GetKeyCode() == 76:
            self.xp +=1
            if ('update' in dir(self.GetParent())):
                self.GetParent().update()
            else:
                self.imagepanel.impanel.Refresh()
        elif event.GetKeyCode() == 73:
            self.yp += 1
            if ('update' in dir(self.GetParent())):
                self.GetParent().update()
            else:
                self.imagepanel.impanel.Refresh()
        elif event.GetKeyCode() == 75:
            self.yp -= 1
            if ('update' in dir(self.GetParent())):
                self.GetParent().update()
            else:
                self.imagepanel.impanel.Refresh()
        else:
            event.Skip()
        
#    def SetOpts(self,event=None):
#        self.cbRedChan.SetSelection(self.do.Chans[2] + 1)
#        self.cbGreenChan.SetSelection(self.do.Chans[1] + 1)
#        self.cbBlueChan.SetSelection(self.do.Chans[0] + 1)
#        self.tRedGain.SetValue(self.do.Gains[2].__str__())
#        self.tGreenGain.SetValue(self.do.Gains[1].__str__())
#        self.tBlueGain.SetValue(self.do.Gains[0].__str__())
#        self.tRedOff.SetValue(self.do.Offs[2].__str__())
#        self.tGreenOff.SetValue(self.do.Offs[1].__str__())
#        self.tBlueOff.SetValue(self.do.Offs[0].__str__())
#        if (self.do.slice == self.do.SLICE_XY):
#            if (self.do.orientation == self.do.UPRIGHT):
#                self.cbSlice.SetSelection(0)
#            else:
#                self.cbSlice.SetSelection(1)
#        elif (self.do.slice == self.do.SLICE_XZ):
#            self.cbSlice.SetSelection(2)
#        else:
#            self.cbSlice.SetSelection(3)
#        self.cbScale.SetSelection(self.scale)
        
    def GetOpts(self,event=None):
        if (self.updating == 0):
#            self.do.Chans[2]=(self.cbRedChan.GetSelection() - 1)
#            self.do.Chans[1]=(self.cbGreenChan.GetSelection() - 1)
#            self.do.Chans[0]=(self.cbBlueChan.GetSelection() - 1)
#            self.do.Gains[2]=(float(self.tRedGain.GetValue()))
#            self.do.Gains[1]=(float(self.tGreenGain.GetValue()))
#            self.do.Gains[0]=(float(self.tBlueGain.GetValue()))
#            self.do.Offs[2]=(float(self.tRedOff.GetValue()))
#            self.do.Offs[1]=(float(self.tGreenOff.GetValue()))
#            self.do.Offs[0]=(float(self.tBlueOff.GetValue()))
#            if (self.cbSlice.GetSelection() == 0):
#                self.do.slice =(self.do.SLICE_XY)
#                self.do.orientation = (self.do.UPRIGHT)
#            elif (self.cbSlice.GetSelection() == 1):
#                self.do.slice = (self.do.SLICE_XY)
#                self.do.orientation = (self.do.ROT90)
#            elif (self.cbSlice.GetSelection() == 2):
#                self.do.slice =(self.do.SLICE_XZ)
#                self.do.orientation=(self.do.UPRIGHT)
#            elif (self.cbSlice.GetSelection() == 3):
#                self.do.slice =(self.do.SLICE_YZ)
#                self.do.orientation  =self.do.UPRIGHT
            #self.scale = self.cbScale.GetSelection()
            sc = pow(2.0,(self.scale-2))
            s = self.CalcImSize()
            self.imagepanel.SetVirtualSize(wx.Size(s[0]*sc,s[1]*sc))

            #if not event == None and event.GetId() in [self.cbSlice.GetId(), self.cbScale.GetId()]:
            #recenter the view
            if(self.do.slice == self.do.SLICE_XY):
                lx = self.xp
                ly = self.yp
                self.aspect = self.do.aspects[1]/self.do.aspects[0]
            elif(self.do.slice == self.do.SLICE_XZ):
                lx = self.xp
                ly = self.zp
                self.aspect = self.do.aspects[2]/self.do.aspects[0]
            elif(self.do.slice == self.do.SLICE_YZ):
                lx = self.yp
                ly = self.zp
                self.aspect = self.do.aspects[2]/self.do.aspects[1]

            sx,sy =self.imagepanel.impanel.GetClientSize()

            #self.imagepanel.SetScrollbars(20,20,s[0]*sc/20,s[1]*sc/20,min(0, lx*sc - sx/2)/20, min(0,ly*sc - sy/2)/20)
            ppux, ppuy = self.imagepanel.GetScrollPixelsPerUnit()
            #self.imagepanel.SetScrollPos(wx.HORIZONTAL, max(0, lx*sc - sx/2)/ppux)
            #self.imagepanel.SetScrollPos(wx.VERTICAL, max(0, ly*sc - sy/2)/ppuy)
            self.imagepanel.Scroll(max(0, lx*sc - sx/2)/ppux, max(0, ly*sc*self.aspect - sy/2)/ppuy)

            self.imagepanel.impanel.Refresh()
            #self.Refresh()
            
    def Optim(self, event = None):
        self.do.Optimise(self.ds, int(self.zp))
        self.updating=1
        #self.SetOpts()
        self.optionspanel.RefreshHists()
        self.Refresh()
        self.updating=0
        
    def CalcImSize(self):
        if (self.do.slice == self.do.SLICE_XY):
            if (self.do.orientation == self.do.UPRIGHT):
                return (self.ds.shape[0],self.ds.shape[1])
            else:
                return (self.ds.shape[1],self.ds.shape[0])
        elif (self.do.slice == self.do.SLICE_XZ):
            return (self.ds.shape[0],self.ds.shape[2])
        else:
            return(self.ds.shape[1],self.ds.shape[2] )
        
    def DoNix(self, event):
        pass
    
    def ShowOpts(self, event):
        if (self.showOptsPanel == 1):
            self.showOptsPanel = 0
            self.GetSizer().Show(self.optionspanel, 0)
            self.Layout()
        else:
            self.showOptsPanel = 1
            self.GetSizer().Show(self.optionspanel, 1)
            self.Layout()
            
    def OnLeftClick(self,event):
        dc = wx.ClientDC(self.imagepanel.impanel)
        self.imagepanel.impanel.PrepareDC(dc)
        pos = event.GetLogicalPosition(dc)
        #print pos
        sc = pow(2.0,(self.scale-2))
        if (self.do.slice == self.do.SLICE_XY):
            self.xp =int(pos[0]/sc)
            self.yp = int(pos[1]/(sc*self.aspect))
        elif (self.do.slice == self.do.SLICE_XZ):
            self.xp =int(pos[0]/sc)
            self.zp =int(pos[1]/(sc*self.aspect))
        elif (self.do.slice == self.do.SLICE_YZ):
            self.yp =int(pos[0]/sc)
            self.zp =int(pos[1]/(sc*self.aspect))
        if ('update' in dir(self.GetParent())):
             self.GetParent().update()
        else:
            self.imagepanel.impanel.Refresh()

    def PointsHitTest(self):
        if len(self.points) > 0:
            iCand = numpy.where((abs(self.points[:,2] - self.zp) < 1)*(abs(self.points[:,0] - self.xp) < 3)*(abs(self.points[:,1] - self.yp) < 3))[0]

            if len(iCand) == 0:
                return None
            elif len(iCand) == 1:
                return iCand[0]
            else:
                pCand = self.points[iCand, :]

                iNearest = numpy.argmin((pCand[:,0] - self.xp)**2 + (pCand[:,1] - self.yp)**2)

                return iCand[iNearest]
        else:
            return None



            
    def OnRightDown(self,event):
        dc = wx.ClientDC(self.imagepanel.impanel)
        self.imagepanel.impanel.PrepareDC(dc)
        pos = event.GetLogicalPosition(dc)
        print(pos)
        sc = pow(2.0,(self.scale-2))
        if (self.do.slice == self.do.SLICE_XY):
            self.selection_begin_x = int(pos[0]/sc)
            self.selection_begin_y = int(pos[1]/(sc*self.aspect))
        elif (self.do.slice == self.do.SLICE_XZ):
            self.selection_begin_x = int(pos[0]/sc)
            self.selection_begin_z = int(pos[1]/(sc*self.aspect))
        elif (self.do.slice == self.do.SLICE_YZ):
            self.selection_begin_y = int(pos[0]/sc)
            self.selection_begin_z = int(pos[1]/(sc*self.aspect))
            
    def OnRightUp(self,event):
        dc = wx.ClientDC(self.imagepanel.impanel)
        self.imagepanel.impanel.PrepareDC(dc)
        pos = event.GetLogicalPosition(dc)
        print(pos)
        sc = pow(2.0,(self.scale-2))
        if (self.do.slice == self.do.SLICE_XY):
            self.selection_end_x = int(pos[0]/sc)
            self.selection_end_y = int(pos[1]/(sc*self.aspect))
        elif (self.do.slice == self.do.SLICE_XZ):
            self.selection_end_x = int(pos[0]/sc)
            self.selection_end_z = int(pos[1]/(sc*self.aspect))
        elif (self.do.slice == self.do.SLICE_YZ):
            self.selection_end_y = int(pos[0]/sc)
            self.selection_end_z = int(pos[1]/(sc*self.aspect))
        if ('update' in dir(self.GetParent())):
             self.GetParent().update()
        else:
            self.imagepanel.impanel.Refresh()
            
    def ResetSelection(self):
        self.selection_begin_x = 0
        self.selection_begin_y = 0
        self.selection_begin_z = 0
        
        self.selection_end_x = self.ds.shape[0] - 1
        self.selection_end_y = self.ds.shape[1] - 1
        self.selection_end_z = self.ds.shape[2] - 1
        
    def SetSelection(self, (b_x,b_y,b_z),(e_x,e_y,e_z)):
        self.selection_begin_x = b_x
        self.selection_begin_y = b_y
        self.selection_begin_z = b_z
        
        self.selection_end_x = e_x
        self.selection_end_y = e_y
        self.selection_end_z = e_z
        
#    def Render(self):
#        x0,y0 = self.imagepanel.CalcUnscrolledPosition(0,0)
#        sX, sY = self.imagepanel.Size
#
#        sc = pow(2.0,(self.scale-2))
#        sX_ = int(sX/sc)
#        sY_ = int(sY/sc)
#        x0_ = int(x0/sc)
#        y0_ = int(y0/sc)
#
#        #XY
#        if self.do.slice == DisplayOpts.SLICE_XY:
#            if self.do.Chans[0] < self.ds.shape[3]:
#                r = (self.do.Gains[0]*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), self.do.Chans[0]] - self.do.Offs[0])).astype('uint8').squeeze().T
#            else:
#                r = numpy.zeros(ds.shape[:2], 'uint8').T
#            if self.do.Chans[1] < self.ds.shape[3]:
#                g = (self.do.Gains[1]*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), self.do.Chans[1]] - self.do.Offs[1])).astype('uint8').squeeze().T
#            else:
#                g = numpy.zeros(ds.shape[:2], 'uint8').T
#            if self.do.Chans[2] < self.ds.shape[3]:
#                b = (self.do.Gains[2]*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), self.do.Chans[2]] - self.do.Offs[2])).astype('uint8').squeeze().T
#            else:
#                b = numpy.zeros(ds.shape[:2], 'uint8').T
#        #XZ
#        elif self.do.slice == DisplayOpts.SLICE_XZ:
#            if self.do.Chans[0] < self.ds.shape[3]:
#                r = (self.do.Gains[0]*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), self.do.Chans[0]] - self.do.Offs[0])).astype('uint8').squeeze().T
#            else:
#                r = numpy.zeros((ds.shape[0], ds.shape[2]), 'uint8').T
#            if self.do.Chans[1] < self.ds.shape[3]:
#                g = (self.do.Gains[1]*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), self.do.Chans[1]] - self.do.Offs[1])).astype('uint8').squeeze().T
#            else:
#                g = numpy.zeros((ds.shape[0], ds.shape[2]), 'uint8').T
#            if self.do.Chans[2] < self.ds.shape[3]:
#                b = (self.do.Gains[2]*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), self.do.Chans[2]] - self.do.Offs[2])).astype('uint8').squeeze().T
#            else:
#                b = numpy.zeros((ds.shape[0], ds.shape[2]), 'uint8'.T)
#
#        #YZ
#        elif self.do.slice == DisplayOpts.SLICE_YZ:
#            if self.do.Chans[0] < self.ds.shape[3]:
#                r = (self.do.Gains[0]*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), self.do.Chans[0]] - self.do.Offs[0])).astype('uint8').squeeze().T
#            else:
#                r = numpy.zeros((ds.shape[1], ds.shape[2]), 'uint8').T
#            if self.do.Chans[1] < self.ds.shape[3]:
#                g = (self.do.Gains[1]*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), self.do.Chans[1]] - self.do.Offs[1])).astype('uint8').squeeze().T
#            else:
#                g = numpy.zeros((ds.shape[1], ds.shape[2]), 'uint8').T
#            if self.do.Chans[2] < self.ds.shape[3]:
#                b = (self.do.Gains[2]*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), self.do.Chans[2]] - self.do.Offs[2])).astype('uint8').squeeze().T
#            else:
#                b = numpy.zeros((ds.shape[1], ds.shape[2]), 'uint8'.T)
#        r = r.T
#        g = g.T
#        b = b.T
#        r = r.reshape(r.shape + (1,))
#        g = g.reshape(g.shape + (1,))
#        b = b.reshape(b.shape + (1,))
#        ima = numpy.concatenate((r,g,b), 2)
#        return wx.ImageFromData(ima.shape[1], ima.shape[0], ima.ravel())

    def Render(self):
        x0,y0 = self.imagepanel.CalcUnscrolledPosition(0,0)
        sX, sY = self.imagepanel.impanel.Size

        sc = pow(2.0,(self.scale-2))
        sX_ = int(sX/sc)
        sY_ = int(sY/(sc*self.aspect))
        x0_ = int(x0/sc)
        y0_ = int(y0/(sc*self.aspect))

        #XY
        #ima = numpy.zeros((sX_, sY_, 3), 'uint8')

        if self.do.slice == DisplayOpts.SLICE_XY:
            ima = numpy.zeros((min(sY_, self.ds.shape[1]), min(sX_, self.ds.shape[0]), 3), 'uint8')
            #ima = numpy.zeros((self.ds.shape[1], self.ds.shape[0], 3), 'uint8')
#            if self.do.Chans[0] < self.ds.shape[3]:
#                r = (self.do.Gains[0]*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), self.do.Chans[0]] - self.do.Offs[0])).astype('uint8').squeeze().T
#            else:
#                r = numpy.zeros(ds.shape[:2], 'uint8').T
#            if self.do.Chans[1] < self.ds.shape[3]:
#                g = (self.do.Gains[1]*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), self.do.Chans[1]] - self.do.Offs[1])).astype('uint8').squeeze().T
#            else:
#                g = numpy.zeros(ds.shape[:2], 'uint8').T
#            if self.do.Chans[2] < self.ds.shape[3]:
#                b = (self.do.Gains[2]*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), self.do.Chans[2]] - self.do.Offs[2])).astype('uint8').squeeze().T
#            else:
#                b = numpy.zeros(ds.shape[:2], 'uint8').T
            for chan, offset, gain, cmap in zip(self.do.Chans, self.do.Offs, self.do.Gains, self.do.cmaps):
                #print ima.shape, cmap(gain*self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), chan].squeeze() - offset)[:,:,:3].shape
                #print (gain*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), chan] - offset).max()
                ima[:] = ima[:] + (255*cmap(gain*(self.ds[x0_:(x0_+sX_),y0_:(y0_+sY_),int(self.zp), chan].squeeze().T - offset))[:,:,:3]).astype('b')[:]
        #XZ
        elif self.do.slice == DisplayOpts.SLICE_XZ:
            ima = numpy.zeros((min(sY_, self.ds.shape[2]), min(sX_, self.ds.shape[0]), 3), 'uint8')
            #ima = numpy.zeros((self.ds.shape[0], self.ds.shape[2], 3), 'uint8')
#            if self.do.Chans[0] < self.ds.shape[3]:
#                r = (self.do.Gains[0]*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), self.do.Chans[0]] - self.do.Offs[0])).astype('uint8').squeeze().T
#            else:
#                r = numpy.zeros((ds.shape[0], ds.shape[2]), 'uint8').T
#            if self.do.Chans[1] < self.ds.shape[3]:
#                g = (self.do.Gains[1]*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), self.do.Chans[1]] - self.do.Offs[1])).astype('uint8').squeeze().T
#            else:
#                g = numpy.zeros((ds.shape[0], ds.shape[2]), 'uint8').T
#            if self.do.Chans[2] < self.ds.shape[3]:
#                b = (self.do.Gains[2]*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), self.do.Chans[2]] - self.do.Offs[2])).astype('uint8').squeeze().T
#            else:
#                b = numpy.zeros((ds.shape[0], ds.shape[2]), 'uint8'.T)

            for chan, offset, gain, cmap in zip(self.do.Chans, self.do.Offs, self.do.Gains, self.do.cmaps):
                ima[:] = ima[:] + 255*cmap(gain*(self.ds[x0_:(x0_+sX_),int(self.yp),y0_:(y0_+sY_), chan].squeeze().T - offset))[:,:,:3][:]

        #YZ
        elif self.do.slice == DisplayOpts.SLICE_YZ:
            ima = numpy.zeros((min(sY_, self.ds.shape[2]), min(sX_, self.ds.shape[1]), 3), 'uint8')
            #ima = numpy.zeros((self.ds.shape[1], self.ds.shape[2], 3), 'uint8')
#            if self.do.Chans[0] < self.ds.shape[3]:
#                r = (self.do.Gains[0]*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), self.do.Chans[0]] - self.do.Offs[0])).astype('uint8').squeeze().T
#            else:
#                r = numpy.zeros((ds.shape[1], ds.shape[2]), 'uint8').T
#            if self.do.Chans[1] < self.ds.shape[3]:
#                g = (self.do.Gains[1]*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), self.do.Chans[1]] - self.do.Offs[1])).astype('uint8').squeeze().T
#            else:
#                g = numpy.zeros((ds.shape[1], ds.shape[2]), 'uint8').T
#            if self.do.Chans[2] < self.ds.shape[3]:
#                b = (self.do.Gains[2]*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), self.do.Chans[2]] - self.do.Offs[2])).astype('uint8').squeeze().T
#            else:
#                b = numpy.zeros((ds.shape[1], ds.shape[2]), 'uint8'.T)

            for chan, offset, gain, cmap in zip(self.do.Chans, self.do.Offs, self.do.Gains, self.do.cmaps):
                ima[:] = ima[:] + 255*cmap(gain*(self.ds[int(self.xp),x0_:(x0_+sX_),y0_:(y0_+sY_), chan].squeeze().T - offset))[:,:,:3][:]
#        r = r.T
#        g = g.T
#        b = b.T
#        r = r.reshape(r.shape + (1,))
#        g = g.reshape(g.shape + (1,))
#        b = b.reshape(b.shape + (1,))
#        ima = numpy.concatenate((r,g,b), 2)
        #print ima.max()
        return wx.ImageFromData(ima.shape[1], ima.shape[0], ima.ravel())

    def GetProfile(self,halfLength=10,axis = 2, pos=None, roi=[2,2], background=None):
        if not pos is None:
            px, py, pz = pos
        else:
            px, py, pz = self.xp, self.yp, self.zp

        points = self.points
        d = None
        pts = None

        if axis == 2: #z
            p = self.ds[(px - roi[0]):(px + roi[0]),(py - roi[1]):(py + roi[1]),(pz - halfLength):(pz + halfLength)].mean(2).mean(1)
            x = numpy.mgrid[(pz - halfLength):(pz + halfLength)]
            if len(points) > 0:
                d = numpy.array([((abs(points[:,0] - px) < 2*roi[0])*(abs(points[:,1] - py) < 2*roi[1])*(points[:,2] == z)).sum() for z in x])

                pts = numpy.where((abs(points[:,0] - px) < 2*roi[0])*(abs(points[:,1] - py) < 2*roi[1])*(abs(points[:,2] - pz) < halfLength))
            #print p.shape
            #p = p.mean(1).mean(0)
            if not background is None:
                p -= self.ds[(px - background[0]):(px + background[0]),(py - background[1]):(py + background[1]),(pz - halfLength):(pz + halfLength)].mean(2).mean(1)
        elif axis == 1: #y
            p = self.ds[(px - roi[0]):(px + roi[0]),(py - halfLength):(py + halfLength),(pz - roi[1]):(pz + roi[1])].mean(1).mean(0)
            x = numpy.mgrid[(py - halfLength):(py + halfLength)]
            if len(points) > 0:
                d = numpy.array([((abs(points[:,1] - py) < 2*roi[0])*(abs(points[:,2] - pz) < 2*roi[1])*(points[:,0] == z)).sum() for z in x])

                pts = numpy.where((abs(points[:,0] - px) < 2*roi[0])*(abs(points[:,1] - py) < halfLength)*(abs(points[:,2] - pz) < 2*roi[1]))
            if not background is None:
                p -= self.ds[(px - background[0]):(px + background[0]),(py - halfLength):(py + halfLength),(pz - background[1]):(pz + background[1]),(pz - halfLength):(pz + halfLength)].mean(1).mean(0)
        elif axis == 0: #x
            p = self.ds[(px - halfLength):(px + halfLength), (py - roi[0]):(py + roi[0]),(pz - roi[1]):(pz + roi[1])].mean(2).mean(0)
            x = numpy.mgrid[(px - halfLength):(px + halfLength)]
            if len(points) > 0:
                d = numpy.array([((abs(points[:,0] - px) < 2*roi[0])*(abs(points[:,2] - pz) < 2*roi[1])*(points[:,1] == z)).sum() for z in x])

                pts = numpy.where((abs(points[:,0] - px) < halfLength)*(abs(points[:,1] - py) < 2*roi[0])*(abs(points[:,2] - pz) < 2*roi[1]))
            if not background is None:
                p -= self.ds[(px - halfLength):(px + halfLength),(py - background[0]):(py + background[0]),(pz - background[1]):(pz + background[1])].mean(2).mean(0)

        return x,p,d, pts
# end of class ViewPanel
