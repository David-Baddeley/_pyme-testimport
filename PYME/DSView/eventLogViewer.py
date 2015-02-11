#!/usr/bin/python

##################
# eventLogViewer.py
#
# Copyright David Baddeley, 2009
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
import numpy as np
import time
import pylab
from PYME.Analysis.piecewiseMapping import timeToFrames, framesToTime

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

        self.startTime = self.metaData.getEntry('StartTime')

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

        #maxT = tPerFrame*self.frameRange[1]
        maxT = framesToTime(self.frameRange[1], self.eventSource, self.metaData) - self.startTime
        #minT = tPerFrame*self.frameRange[0]
        minT = framesToTime(self.frameRange[0], self.eventSource, self.metaData) - self.startTime

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
        pixPerS = pixPerFrame/tPerFrame

        self.pixPerFrame = pixPerFrame

        nTicksTarget = self.Size[1]/(7.5*textHeight)
        tickSpacing = nFrames/nTicksTarget
        #round to 1sf
        tickSpacing = round(tickSpacing/(10**np.floor(np.log10(tickSpacing))))*(10**np.floor(np.log10(tickSpacing)))
        tickStart = np.ceil(self.frameRange[0]/tickSpacing)*tickSpacing
        ticks = np.arange(tickStart, self.frameRange[1]+.01, tickSpacing)
        tickTimes = framesToTime(ticks, self.eventSource, self.metaData) - self.startTime

        for t, tt in zip(ticks, tickTimes):
            #y = (t -self.frameRange[0])*pixPerFrame + 2*textHeight
            y = (tt -minT)*pixPerS + 2*textHeight
            dc.DrawText('%3.4g' % t, hpadding, y - 0.5*textHeight)
            dc.DrawLine(frameLabelSize + 2*hpadding - tickSize, y, frameLabelSize + 2*hpadding, y)


#        #### Time # ticks
        tickSpacingTime = tPerFrame * tickSpacing
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
        #self.PrepareDC(DC)

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
        self.Update()

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
        self.Update()

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
            self.Update()

    def SetRange(self, range):
        self.maxRange = range
        if self.autoRange:
            self.frameRange = range
        self.Refresh()
        self.Update()

    def SetCharts(self, charts):
        self.charts = charts
        self.Refresh()
        self.Update()

class eventLogTPanel(wx.Panel):
    def __init__(self, parent, eventSource, metaData, timeRange, charts = [], size=(-1, -1)):
        self.eventSource = eventSource
        self.metaData = metaData
        self.maxRange = list(timeRange)
        self.timeRange = timeRange
        self.charts = charts

        self.autoRange = True

        self.initialised = False

        self.SetEventSource(eventSource)

        self.startTime = self.metaData.getEntry('StartTime')

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

        timeLabelSize = max(dc.GetTextExtent('%3.4g' % self.timeRange[1])[0], dc.GetTextExtent('N')[0])

        #tPerFrame = self.metaData.getEntry('Camera.CycleTime')
        minT, maxT = self.timeRange

        pixPerS = float(self.Size[1] - 3*textHeight)/(maxT - minT)
        self.pixPerS = pixPerS

        maxF = timeToFrames(maxT+ self.startTime, self.eventSource, self.metaData) #- self.startTime
        minF = timeToFrames(minT+ self.startTime, self.eventSource, self.metaData) #- self.startTime

        #print minF, maxF

        if (maxF < minF) < 30: #show when camera was actually recording
            fTimes = framesToTime(np.arange(minF, maxF + .1), self.eventSource, self.metaData) - self.startTime
            tPerFrame = self.metaData.getEntry('Camera.CycleTime')

            old_pen = dc.GetPen()
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.Colour(220, 255, 200)))

            for ft in fTimes:
                y0 = (ft -minT)*pixPerS + 2*textHeight
                bh = tPerFrame*pixPerS

                dc.DrawRectangle(0, y0, self.Size[0], bh)

            dc.SetPen(old_pen)



        frameLabelSize = max(dc.GetTextExtent('%3.4g' % maxF)[0], dc.GetTextExtent('[s]' % maxF)[0])

        #labels
        dc.DrawText('N', hpadding + frameLabelSize/2 - dc.GetTextExtent('N')[0]/2, 0)
        dc.DrawText('[s]', frameLabelSize + 3*hpadding + barWidth + timeLabelSize/2 - dc.GetTextExtent('[s]')[0]/2 , 0)

        dc.SetBrush(wx.MEDIUM_GREY_BRUSH)

        x0 = frameLabelSize + 2*hpadding
        y0 = 2*textHeight
        dc.DrawRectangle(x0, y0, barWidth, self.Size[1] - 3*textHeight)

        if self.timeRange[0] > self.maxRange[0]:
            pl = [(x0 + 2,y0 - 3), (x0 + barWidth/2, y0 - barWidth/2 - 1), (x0 + barWidth - 2, y0 - 3)]
            dc.DrawPolygon(pl)

        if self.timeRange[1] < self.maxRange[1]:
            y0 = y0 + self.Size[1] - 3*textHeight
            pl = [(x0 + 2,y0 + 2), (x0 + barWidth/2, y0 + barWidth/2), (x0 + barWidth - 2, y0 + 2)]
            dc.DrawPolygon(pl)

        #ticks
        dc.SetPen(wx.BLACK_PEN)

        ##frame # ticks
        nFrames = maxF - minF
        
        #pixPerS = pixPerFrame/tPerFrame

        #self.pixPerFrame = pixPerFrame

        nTicksTarget = self.Size[1]/(5.5*textHeight)
        tickSpacing = np.floor(nFrames/nTicksTarget)
        #round to 1sf
        #tickSpacing = round(tickSpacing/(10**np.floor(np.log10(tickSpacing))))*(10**np.floor(np.log10(tickSpacing)))
        tickStart = np.ceil(minF/tickSpacing)*tickSpacing
        ticks = np.arange(tickStart, maxF+.01, tickSpacing)
        tickTimes = framesToTime(ticks, self.eventSource, self.metaData) - self.startTime

        #print minT, maxT,nFrames, nTicksTarget, tickStart, tickSpacing

        for t, tt in zip(ticks, tickTimes):
            #y = (t -self.frameRange[0])*pixPerFrame + 2*textHeight
            y = (tt -minT)*pixPerS + 2*textHeight
            #print t, hpadding, y - 0.5*textHeight
            dc.DrawText('%3.4g' % t, hpadding, y - 0.5*textHeight)
            dc.DrawLine(frameLabelSize + 2*hpadding - tickSize, y, frameLabelSize + 2*hpadding, y)


#        #### Time # ticks
        tickSpacingTime = (maxT - minT)/nTicksTarget
        #round to 1sf
        tickSpacingTime = round(tickSpacingTime/(10**np.floor(np.log10(tickSpacingTime))))*(10**np.floor(np.log10(tickSpacingTime)))
        tickStartTime = np.ceil(minT/tickSpacingTime)*tickSpacingTime
        ticks = np.arange(tickStartTime, maxT+.0001, tickSpacingTime)
#
        #print minT, maxT, tickSpacingTime
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

        evts = self.eventSource[(self.eventSource['Time'] > (minT + self.startTime))*(self.eventSource['Time'] < (maxT + self.startTime))]
        ets = evts['Time'] - self.startTime
        eys = (ets -minT)*pixPerS + 2*textHeight
        dys = np.hstack([np.diff(eys), [100]])

        #special hack for co-incident events
        for i in range(len(dys)):
            if dys[i] == 0:
                j = i+1
                while dys[j] == 0: #find the next non-zero step
                    j += 1

                if dys[j] > 1.2*textHeight: #we have room to expand
                    dys[i] += 1.2*textHeight
                    dys[j] -= 1.2*textHeight

        lastLineY = 0

        for i, e in enumerate(evts):
            y = eys[i]
            t = ets[i]
            #print y
            dc.SetPen(wx.Pen(self.lineColours[e['EventName']]))
            dc.SetTextForeground(self.lineColours[e['EventName']])
            if (y < (lastLineY + 2)  or (numSkipped > 0 and y < (lastLineY + 1.2*textHeight))) and dys[i] < (1.2*textHeight + 2*numSkipped): #no room - skip
                if ((tTickPositions - y)**2).min() < (0.3*textHeight)**2:
                    dc.DrawLine(x0, y, x0 + barWidth, y)
                    dc.DrawLine(x1 - 2*hpadding, y, x1 - 2*(1 + 1*numSkipped), y)
                else:
                    dc.DrawLine(x0, y, x1 - 2*(1 + 1*numSkipped), y)
                dc.DrawLine(x1- 2*(1 + 1*numSkipped), y, x1- 2*(1 + 1*numSkipped), lastEvY + 0.5*textHeight + 1 + 2*numSkipped)
                dc.DrawLine(x1- 2*(1 + 1*numSkipped),lastEvY + 0.5*textHeight + 1 + 2*numSkipped, x3 + 200, lastEvY+ 0.5*textHeight + 1 + 2*numSkipped)
                numSkipped +=1
                lastLineY += 2
            else:
                if ((tTickPositions - y)**2).min() < (0.3*textHeight)**2:
                    dc.DrawLine(x0, y, x0 + barWidth, y)
                    dc.DrawLine(x1 - 2*hpadding, y, x1- 2*(1 + 1*numSkipped), y)
                else:
                    dc.DrawLine(x0, y, x1- 2*(1 + 1*numSkipped), y)
                if y < (lastLineY + 1.2*textHeight):
                    dc.DrawLine(x1- 2*(1 + 1*numSkipped), y, x1- 2*(1 + 1*numSkipped), lastLineY + 1.2*textHeight)
                    y = lastLineY + 1.2*textHeight

                dc.DrawLine(x1- 2*(1 + 1*numSkipped), y, x2, y)
                eventText = '%6.2fs\t' % t + '%(EventName)s\t%(EventDescr)s' % e

                etw = dc.GetTextExtent(eventText)[0]

                etwMax = self.Size[0] - (x3 + 2*hpadding + 80*len(self.charts))

                if etw >  etwMax:
                    newLen = int((float(etwMax)/etw)*len(eventText))
                    eventText = eventText[:(newLen - 4)] + ' ...'

                eventTextWidth = max(eventTextWidth, dc.GetTextExtent(eventText)[0])
                dc.DrawText(eventText, x3, y - 0.5*textHeight)
                lastEvY = y
                lastLineY = y
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

            xv = np.array([max(minF, 0),] + [x for x in cmapping.xvals if x > minF and x < maxF] + [maxF,])
            vv = cmapping(xv)

            vmin = vv.min()
            vmax = vv.max()

            ml = dc.GetTextExtent('%3.2f'% vmin)[0]/2
            mr = dc.GetTextExtent('%3.2f'% vmax)[0]/2

            chartWidthInternal = chartWidth - ml - mr

            if vmax == vmin:
                vsc = 0
            else:
                vsc = chartWidthInternal/float(vmax - vmin)

            

            dc.DrawText('%3.2f'% vmin, x4 , 1*textHeight)
            dc.DrawText('%3.2f'% vmax, x4 + chartWidth - 2*mr, 1*textHeight)

            dc.SetPen(wx.BLACK_PEN)
            dc.DrawLine(x4 + ml, 2*textHeight, x4 + ml, 2*textHeight + tickSize)
            dc.DrawLine(x4 + chartWidth - mr, 2*textHeight, x4 + chartWidth - mr, 2*textHeight + tickSize)

            #dc.SetPen(wx.Pen(wx.BLUE, 2))
            dc.SetPen(wx.Pen(self.lineColours[sourceEv],2))

            xvt = framesToTime(xv, self.eventSource, self.metaData) - self.startTime

            x_0 = xvt[0]
            v_0 = vv[0]

            yp_ = (x_0 -minT)*pixPerS + 2*textHeight
            xp_ = x4  + ml + (v_0 - vmin)*vsc

            for x,v in zip(xvt[1:-1], vv[1:-1]):
                yp = (x -minT)*pixPerS + 2*textHeight
                xp = x4 + ml + (v - vmin)*vsc
                dc.DrawLine(xp_, yp_, xp_, yp)
                dc.DrawLine(xp_, yp, xp, yp)
                xp_ = xp
                yp_ = yp

            yp = (xvt[-1] -minT)*pixPerS + 2*textHeight
            xp = x4 + ml + (vv[-1] - vmin)*vsc
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
        self.Update()

    def OnWheel(self, event):
        rot = event.GetWheelRotation()

        #get translated coordinates
        #xp = event.GetX()*view_size_x/self.Size[0] + self.xmin
        yp = self.timeRange[0] + (float(event.GetY() - 2*self.textHeight)/self.pixPerS)
        #print 'yp = ', yp

        dT = self.timeRange[1] - self.timeRange[0]

        if rot < 0: #zoom out
            nMin = max(yp - dT, self.maxRange[0])
            nMax = min(yp + dT, self.maxRange[1])

        elif rot > 0: #zoom in
            nMin = max(yp - dT/4, self.maxRange[0])
            nMax = min(yp + dT/4, self.maxRange[1])
            if not nMax > (nMin + .1):
                nMax = nMin + .1

        if nMin == self.maxRange[0] and nMax == self.maxRange[1]:
            self.autoRange = True
        else:
            self.autoRange = False

        self.timeRange = (nMin, nMax)
        self.Refresh()
        self.Update()

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
            self.Update()

    def SetRange(self, range):
        self.maxRange = range
        if self.autoRange:
            self.frameRange = range
        self.Refresh()
        self.Update()

    def SetCharts(self, charts):
        self.charts = charts
        self.Refresh()
