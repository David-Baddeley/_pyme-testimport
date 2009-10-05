#!/usr/bin/python

##################
# eventLogViewer.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import wx
import numpy as np
import time
import pylab

class eventLogPanel(wx.Panel):
    def __init__(self, parent, eventSource, metaData, frameRange, charts = [], size=(-1, -1)):
        self.eventSource = eventSource
        self.metaData = metaData
        self.maxRange = frameRange
        self.frameRange = frameRange
        self.charts = charts

        self.autoRange = True

        self.initialised = False

        self.SetEventSource(eventSource)

#        self.evKeyNames = set()
#        for e in self.eventSource:
#            self.evKeyNames.add(e['EventName'])
#
#        colours = pylab.cm.gist_rainbow(np.arange(len(self.evKeyNames))/float(len(self.evKeyNames)))[:,:3]
#
#        self.lineColours = {}
#        for k, c in zip(self.evKeyNames, colours):
#            self.lineColours[k] = c

        wx.Panel.__init__(self, parent, size=size)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_MOUSEWHEEL(self, self.OnWheel)

        self.initialised = True

    def DoPaint(self, dc):
        dc.Clear()

        hpadding = 10
        barWidth = 20
        tickSize = 5

        lastEvY = 0

        eventTextWidth = 100
        
        dc.SetFont(wx.NORMAL_FONT)
        textHeight = dc.GetTextExtent('test')[1]

        self.textHeight = textHeight

        frameLabelSize = max(dc.GetTextExtent('%3.4g' % self.frameRange[1])[0], dc.GetTextExtent('N')[0])

        tPerFrame = self.metaData.getEntry('Camera.CycleTime')

        maxT = tPerFrame*self.frameRange[1]
        minT = tPerFrame*self.frameRange[0]

        timeLabelSize = max(dc.GetTextExtent('%3.4g' % maxT)[0], dc.GetTextExtent('[s]' % maxT)[0])

        #labels
        dc.DrawText('N', hpadding + frameLabelSize/2 - dc.GetTextExtent('N')[0]/2, 0)
        dc.DrawText('[s]', frameLabelSize + 3*hpadding + barWidth + timeLabelSize/2 - dc.GetTextExtent('[s]')[0]/2 , 0)

        #dc.SetFont(wx.NORMAL_FONT)
        #bar
        #dc.SetPen(wx.GREEN_PEN)
        dc.SetBrush(wx.MEDIUM_GREY_BRUSH)

        x0 = frameLabelSize + 2*hpadding
        y0 = 2*textHeight
        dc.DrawRectangle(x0, y0, barWidth, self.Size[1] - 3*textHeight)

        if self.frameRange[0] > self.maxRange[0]:
            pl = [(x0 + 2,y0 - 3), (x0 + barWidth/2, y0 - barWidth/2 - 1), (x0 + barWidth - 2, y0 - 3)]
            dc.DrawPolygon(pl)

        if self.frameRange[1] < self.maxRange[1]:
            y0 = y0 + self.Size[1] - 3*textHeight
            pl = [(x0 + 2,y0 + 2), (x0 + barWidth/2, y0 + barWidth/2), (x0 + barWidth - 2, y0 + 2)]
            dc.DrawPolygon(pl)

        #ticks
        dc.SetPen(wx.BLACK_PEN)

        ##frame # ticks
        nFrames = self.frameRange[1] - self.frameRange[0]
        pixPerFrame = float(self.Size[1] - 3*textHeight)/nFrames

        self.pixPerFrame = pixPerFrame

        nTicksTarget = self.Size[1]/(7.5*textHeight)
        tickSpacing = nFrames/nTicksTarget
        #round to 1sf
        tickSpacing = round(tickSpacing/(10**np.floor(np.log10(tickSpacing))))*(10**np.floor(np.log10(tickSpacing)))
        tickStart = np.ceil(self.frameRange[0]/tickSpacing)*tickSpacing
        ticks = np.arange(tickStart, self.frameRange[1]+.01, tickSpacing)

        for t in ticks:
            y = (t -self.frameRange[0])*pixPerFrame + 2*textHeight
            dc.DrawText('%3.4g' % t, hpadding, y - 0.5*textHeight)
            dc.DrawLine(frameLabelSize + 2*hpadding - tickSize, y, frameLabelSize + 2*hpadding, y)


#        #### Time # ticks
        tickSpacingTime = tPerFrame * tickSpacing
        pixPerS = pixPerFrame/tPerFrame
        #round to 1sf
        tickSpacingTime = round(tickSpacingTime/(10**np.floor(np.log10(tickSpacingTime))))*(10**np.floor(np.log10(tickSpacingTime)))
        tickStartTime = np.ceil(minT/tickSpacingTime)*tickSpacingTime
        ticks = np.arange(tickStartTime, maxT+.0001, tickSpacingTime)
#
#        #print minT, maxT, tickSpacingTime
#
        for t in ticks:
            y = (t -minT)*pixPerS + 2*textHeight
            dc.DrawText('%2.4g' % t, frameLabelSize + 3*hpadding + barWidth, y - 0.5*textHeight)
            dc.DrawLine(frameLabelSize + 2*hpadding + barWidth, y, frameLabelSize + 2*hpadding + barWidth + tickSize, y)

        tTickPositions = (ticks -minT)*pixPerS + 2*textHeight


        startT = self.metaData.getEntry('StartTime')

        x0 = frameLabelSize + 2*hpadding
        x1 = x0 + 3*hpadding + barWidth + timeLabelSize
        x2 = x1 + hpadding
        x3 = x2 + hpadding

        numSkipped = 0

        for e in self.eventSource:
            t = e['Time'] - startT
            if t > minT and t < maxT:
                y = (t -minT)*pixPerS + 2*textHeight
                dc.SetPen(wx.Pen(self.lineColours[e['EventName']]))
                dc.SetTextForeground(self.lineColours[e['EventName']])
                if y < (lastEvY + 2) or (numSkipped > 0 and y < (lastEvY + 1.2*textHeight)): #no room - skip
                    if ((tTickPositions - y)**2).min() < (0.3*textHeight)**2:
                        dc.DrawLine(x0, y, x0 + barWidth, y)
                        dc.DrawLine(x1 - 2*hpadding, y, x1 - 2*(1 + 1*numSkipped), y)
                    else:
                        dc.DrawLine(x0, y, x1 - 2*(1 + 1*numSkipped), y)
                    dc.DrawLine(x1- 2*(1 + 1*numSkipped), y, x1- 2*(1 + 1*numSkipped), lastEvY + 0.5*textHeight + 1 + 2*numSkipped)
                    dc.DrawLine(x1- 2*(1 + 1*numSkipped),lastEvY + 0.5*textHeight + 1 + 2*numSkipped, x3 + 200, lastEvY+ 0.5*textHeight + 1 + 2*numSkipped)
                    numSkipped +=1
                else:
                    if ((tTickPositions - y)**2).min() < (0.3*textHeight)**2:
                        dc.DrawLine(x0, y, x0 + barWidth, y)
                        dc.DrawLine(x1 - 2*hpadding, y, x1, y)
                    else:
                        dc.DrawLine(x0, y, x1, y)
                    if y < (lastEvY + 1.2*textHeight):
                        dc.DrawLine(x1, y, x1, lastEvY + 1.2*textHeight)
                        y = lastEvY + 1.2*textHeight

                    dc.DrawLine(x1, y, x2, y)
                    eventText = '%6.2fs\t' % t + '%(EventName)s\t%(EventDescr)s' % e

                    etw = dc.GetTextExtent(eventText)[0]

                    etwMax = self.Size[0] - (x3 + 2*hpadding + 80*len(self.charts))

                    if etw >  etwMax:
                        newLen = int((float(etwMax)/etw)*len(eventText))
                        eventText = eventText[:(newLen - 4)] + ' ...'

                    eventTextWidth = max(eventTextWidth, dc.GetTextExtent(eventText)[0])
                    dc.DrawText(eventText, x3, y - 0.5*textHeight)
                    lastEvY = y
                    numSkipped = 0

        dc.SetTextForeground(wx.BLACK)
        dc.SetPen(wx.BLACK_PEN)

        
        x4 = x3 + eventTextWidth + 2*hpadding
        chartWidth = (self.Size[0] - x4)/max(len(self.charts), 1) - 2*hpadding

        for c in self.charts:
            cname = c[0]
            cmapping = c[1]
            sourceEv = c[2]

            dc.SetTextForeground(self.lineColours[sourceEv])

            dc.DrawText(cname, x4 + chartWidth/2 - dc.GetTextExtent(cname)[0]/2, 0)

            xv = np.array([self.frameRange[0],] + [x for x in cmapping.xvals if x > self.frameRange[0] and x < self.frameRange[1]] + [self.frameRange[1],])
            vv = cmapping(xv)

            vmin = vv.min()
            vmax = vv.max()
            if vmax == vmin:
                vsc = 0
            else:
                vsc = chartWidth/float(vmax - vmin)

            dc.DrawText('%3.2f'% vmin, x4 - dc.GetTextExtent('%3.2f'% vmin)[0]/2, 1*textHeight)
            dc.DrawText('%3.2f'% vmax, x4 + chartWidth - dc.GetTextExtent('%3.2f'% vmax)[0]/2, 1*textHeight)

            dc.SetPen(wx.BLACK_PEN)
            dc.DrawLine(x4, 2*textHeight, x4, 2*textHeight + tickSize)
            dc.DrawLine(x4 + chartWidth, 2*textHeight, x4 + chartWidth, 2*textHeight + tickSize)
            
            #dc.SetPen(wx.Pen(wx.BLUE, 2))
            dc.SetPen(wx.Pen(self.lineColours[sourceEv],2))

            x_0 = xv[0]
            v_0 = vv[0]

            yp_ = (x_0 -self.frameRange[0])*pixPerFrame + 2*textHeight
            xp_ = x4 + (v_0 - vmin)*vsc

            for x,v in zip(xv[1:-1], vv[1:-1]):
                yp = (x -self.frameRange[0])*pixPerFrame + 2*textHeight
                xp = x4 + (v - vmin)*vsc
                dc.DrawLine(xp_, yp_, xp_, yp)
                dc.DrawLine(xp_, yp, xp, yp)
                xp_ = xp
                yp_ = yp

            yp = (xv[-1] -self.frameRange[0])*pixPerFrame + 2*textHeight
            xp = x4 + (vv[-1] - vmin)*vsc
            dc.DrawLine(xp_, yp_, xp_, yp)

            x4 = x4 + chartWidth + hpadding

                
        #pm = piecewiseMapping.GeneratePMFromEventList(elv.eventSource, md.Camera.CycleTime*1e-3, md.StartTime, md.Protocol.PiezoStartPos)
#        if self.dragging == 'upper':
#            dc.SetPen(wx.Pen(wx.GREEN, 2))
#        else:
#            dc.SetPen(wx.Pen(wx.RED, 2))

        dc.SetTextForeground(wx.BLACK)

        dc.SetPen(wx.NullPen)
        dc.SetBrush(wx.NullBrush)
        dc.SetFont(wx.NullFont)

    def OnPaint(self,event):
        DC = wx.PaintDC(self)
        self.PrepareDC(DC)

        s = self.GetVirtualSize()
        MemBitmap = wx.EmptyBitmap(s.GetWidth(), s.GetHeight())
        #del DC
        MemDC = wx.MemoryDC()
        OldBitmap = MemDC.SelectObject(MemBitmap)
        try:
            DC.BeginDrawing()

            self.DoPaint(MemDC);

            DC.Blit(0, 0, s.GetWidth(), s.GetHeight(), MemDC, 0, 0)
            DC.EndDrawing()
        finally:

            del MemDC
            del MemBitmap

    def OnSize(self,event):
        self.Refresh()

    def OnWheel(self, event):
        rot = event.GetWheelRotation()

        #get translated coordinates
        #xp = event.GetX()*view_size_x/self.Size[0] + self.xmin
        yp = self.frameRange[0] + (float(event.GetY() - 2*self.textHeight)/self.pixPerFrame)
        #print yp

        nFrames = self.frameRange[1] - self.frameRange[0]

        if rot < 0: #zoom out
            nMin = max(yp - nFrames, self.maxRange[0])
            nMax = min(yp + nFrames, self.maxRange[1])
            
        elif rot > 0: #zoom in
            nMin = max(yp - nFrames/4, self.maxRange[0])
            nMax = min(yp + nFrames/4, self.maxRange[1])
            if not nMax > (nMin + 2):
                nMax += 1

        if nMin == self.maxRange[0] and nMax == self.maxRange[1]:
            self.autoRange = True
        else:
            self.autoRange = False

        self.frameRange = (nMin, nMax)
        self.Refresh()

    def SetEventSource(self, eventSource):
        self.eventSource = eventSource
        self.evKeyNames = set()
        for e in self.eventSource:
            self.evKeyNames.add(e['EventName'])

        colours = 0.9*pylab.cm.gist_rainbow(np.arange(len(self.evKeyNames))/float(len(self.evKeyNames)))[:,:3]

        self.lineColours = {}
        for k, c in zip(self.evKeyNames, colours):
            self.lineColours[k] = wx.Colour(*(255*c))

        if self.initialised:
            self.Refresh()

    def SetRange(self, range):
        self.maxRange = range
        if self.autoRange:
            self.frameRange = range
        self.Refresh()

    def SetCharts(self, charts):
        self.charts = charts
        self.Refresh()
