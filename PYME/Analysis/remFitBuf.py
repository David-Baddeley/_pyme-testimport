#!/usr/bin/python

##################
# remFitBuf.py
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

from PYME.ParallelTasks import taskDef
from PYME.Analysis import ofind
#import ofind_nofilt #use for drift estimation - faster
#import ofind_xcorr
#try:
    #try to use the FFTW version if we have fftw installed
#    import ofind_xcorr_fw as ofind_xcorr
#except:
    #fall back on fftpack in scipy
    #this was only marginally slower at last benchmark implying much of the 
    #cost is not in the ffts
from PYME.Analysis import ofind_xcorr
from PYME.Analysis import ofind_pri
    
import numpy
import numpy as np

dBuffer = None
bBuffer = None
dataSourceID = None

bufferMisses = 0
nTasksProcessed = 0

splitterFitModules = ['SplitterFitFR', 'SplitterFitFNR','SplitterFitQR', 'SplitterFitCOIR', 'SplitterFitFNSR',
                      'BiplaneFitR', 'SplitterShiftEstFR', 
                      'SplitterObjFindR', 'SplitterFitInterpR', 'SplitterFitInterpQR', 'SplitterFitInterpNR', 'SplitterFitInterpBNR', 'SplitterROIExtractNR']

#from pylab import *

import copy

def tqPopFcn(workerN, NWorkers, NTasks):
    #let each task work on its own chunk of data ->
    return workerN * NTasks/NWorkers 
    
class fitResult(taskDef.TaskResult):
    def __init__(self, task, results, driftResults=[]):
        taskDef.TaskResult.__init__(self, task)
        self.index = task.index
        self.results = results
        self.driftResults = driftResults

class dataBuffer: #buffer our io to avoid decompressing multiple times
    def __init__(self,dataSource, bLen = 12):
        self.bLen = bLen
        self.buffer = None #delay creation until we know the dtype
        #self.buffer = numpy.zeros((bLen,) + dataSource.getSliceShape(), 'uint16')
        self.insertAt = 0
        self.bufferedSlices = -1*numpy.ones((bLen,), 'i')
        self.dataSource = dataSource
        
    def getSlice(self,ind):
        global bufferMisses
        #print self.bufferedSlices, self.insertAt, ind
        #return self.dataSource.getSlice(ind)
        if ind in self.bufferedSlices: #return from buffer
            #print int(numpy.where(self.bufferedSlices == ind)[0])
            return self.buffer[int(numpy.where(self.bufferedSlices == ind)[0]),:,:]
        else: #get from our data source and store in buffer
            sl = self.dataSource.getSlice(ind)
            self.bufferedSlices[self.insertAt] = ind

            if self.buffer == None: #buffer doesn't exist yet
                self.buffer = numpy.zeros((self.bLen,) + self.dataSource.getSliceShape(), sl.dtype)
                
            self.buffer[self.insertAt, :,:] = sl
            self.insertAt += 1
            self.insertAt %=self.bLen

            bufferMisses += 1
            
            #if bufferMisses % 10 == 0:
            #    print nTasksProcessed, bufferMisses

            return sl
        
class backgroundBuffer:
    def __init__(self, dataBuffer):
        self.dataBuffer = dataBuffer
        self.curFrames = set()
        self.curBG = numpy.zeros(dataBuffer.dataSource.getSliceShape(), 'f4')

    def getBackground(self, bgindices):
        bgi = set(bgindices)

        #subtract frames we're currently holding but don't need
        for fi in self.curFrames.difference(bgi):
            self.curBG[:] = (self.curBG - self.dataBuffer.getSlice(fi))[:]

        #add frames we don't already have
        nSlices = self.dataBuffer.dataSource.getNumSlices()
        for fi in bgi.difference(self.curFrames):
            if fi >= nSlices:
                #drop frames which run over the end of our data
                bgi.remove(fi)
            else:
                self.curBG[:] = (self.curBG + self.dataBuffer.getSlice(fi))[:]

        self.curFrames = bgi

        return self.curBG/len(bgi)
        
class bgFrameBuffer:
    MAXSHORT = 65535
    MAXIDX = 10000
    def __init__(self, initialSize = 30, percentile=.25):
        self.frameBuffer = None
        self.indices = None
        self.initSize = initialSize
        self.frameNos = {}
        self.availableSlots = []
        self.validData = None
        
        self.pctile = percentile
        
        self.curBG = None
        
    def addFrame(self, frameNo, data):
        if len(self.availableSlots) == 0:
            self._growBuffer(data)
            
        slot = self.availableSlots.pop()
        self.frameNos[frameNo] = slot
        self.frameBuffer[slot, :,:] = data
        self.validData[slot] = 1
        
        dg = self.frameBuffer <= data
        
        self.indices[slot, :, :] = dg.sum(0)
        self.indices += (dg < 1)
        
    def removeFrame(self, frameNo):
        slot = self.frameNos.pop(frameNo)
        
        
        self.frameBuffer[slot, :,:] = self.MAXSHORT
        self.indices -= (self.indices > self.indices[slot, :,:])
        self.indices[slot, :,:] = self.MAXIDX
        
        self.validData[slot] = 0        
        self.availableSlots.append(slot)
        
    def _createBuffers(self, size, shape, dtype):
        bufShape = (size,) + shape #[:2]
        self.frameBuffer = self.MAXSHORT*np.ones(bufShape, dtype)
        self.indices = self.MAXIDX*np.ones(bufShape, np.uint16)
        self.validData = np.zeros(size, np.bool)
        
    def _growBuffer(self, data=None):
        if self.frameBuffer == None:
            #starting from scratch
            self._createBuffers(self.initSize, data.shape, data.dtype)
            
            self.availableSlots += list(range(self.initSize))
            
        else:
            #keep a copy of the existing data
            ofb = self.frameBuffer
            oi = self.indices
            ov = self.validData
            
            #make new buffers half as large again
            oldsize = ofb.shape[0]
            newsize = int(oldsize*1.5)
            self._createBuffers(newsize, ofb.shape[1:], ofb.dtype)
            
            self.frameBuffer[:oldsize, :,:] = ofb
            self.indices[:oldsize, :,:] = oi
            self.validData[:oldsize] = ov
            
            #add new frames to list of availiable frames
            self.availableSlots += list(range(oldsize, newsize))
            
    def getPercentile(self, pctile):
        pcIDX = int(self.validData.sum()*pctile)
        print(pcIDX)
        
        return (self.frameBuffer*(self.indices==pcIDX)).max(0).squeeze()
            
        
        
class backgroundBufferM:
    def __init__(self, dataBuffer, percentile=.5):
        self.dataBuffer = dataBuffer
        self.curFrames = set()
        self.curBG = np.zeros(dataBuffer.dataSource.getSliceShape(), 'f4')
        
        self.bfb = bgFrameBuffer(percentile=percentile)
        
        self.bgSegs = None
        self.pctile = percentile

    def getBackground(self, bgindices):
        bgi = set(bgindices)
        
        if bgi == self.curFrames:
            return self.curBG

        #subtract frames we're currently holding but don't need
        for fi in self.curFrames.difference(bgi):
            self.bfb.removeFrame(fi)

        #add frames we don't already have
        nSlices = self.dataBuffer.dataSource.getNumSlices()
        for fi in bgi.difference(self.curFrames):
            if fi >= nSlices:
                #drop frames which run over the end of our data
                bgi.remove(fi)
            else:
                self.bfb.addFrame(fi, self.dataBuffer.getSlice(fi).squeeze())

        self.curFrames = bgi
        self.curBG = self.bfb.getPercentile(self.pctile).astype('f')

        return self.curBG

        

class fitTask(taskDef.Task):
    def __init__(self, dataSourceID, index, threshold, metadata, fitModule, dataSourceModule='HDFDataSource', bgindices = [], SNThreshold = False, driftEstInd=[], calObjThresh=200):
        '''Create a new fitting task, which opens data from a supplied filename.
        -------------
        Parameters:
        filename - name of file containing the frame to be fitted
        seriesName - name of the series to which the file belongs (to be used in future for sorting processed data)
        threshold - threshold to be used to detect points n.b. this applies to the filtered, potentially bg subtracted data
        taskDef.Task.__init__(self)
        metadata - image metadata (see MetaData.py)
        fitModule - name of module defining fit factory to use
        bgffiles - (optional) list of files to be averaged and subtracted from image prior to point detection - n.B. fitting is still performed on raw data'''
        taskDef.Task.__init__(self)

        self.threshold = threshold
        self.dataSourceID = dataSourceID
        self.index = index

        self.bgindices = bgindices

        self.md = metadata
        
        self.fitModule = fitModule
        self.dataSourceModule = dataSourceModule
        self.SNThreshold = SNThreshold
        self.driftEstInd = driftEstInd
        self.driftEst = not len(self.driftEstInd) == 0
        self.calObjThresh = calObjThresh
                 
        self.bufferLen = 50 #12
        if self.driftEst: 
            #increase the buffer length as we're going to look forward as well
            self.bufferLen = 50 #17
            
    def __mapSplitterCoords(self, x,y):
        vx = self.md['voxelsize.x']*1e3
        vy = self.md['voxelsize.y']*1e3
        
        x0 = (self.md['Camera.ROIPosX'] - 1)
        y0 = (self.md['Camera.ROIPosY'] - 1)
        
        if 'Splitter.Channel0ROI' in self.md.getEntryNames():
            xg, yg, w, h = self.md['Splitter.Channel0ROI']
            #x0 -= (self.md['Camera.ROIPosX'] - 1)
            #y0 -= (self.md['Camera.ROIPosY'] - 1)
            
            xr, yr, w, h = self.md['Splitter.Channel1ROI']
            #x1 -= (self.md['Camera.ROIPosX'] - 1)
            #y1 -= (self.md['Camera.ROIPosY'] - 1)
        else:
            xg,yg, w, h = 0,0,self.data.shape[0], self.data.shape[1]
            xr, yr = w,h
            
        ch1 = (x>=(xr - x0))&(y >= (yr - y0))
            
        xn = x - (x >= (xg-x0+w))*(xr)
        yn = y - (y >= (yg-y0+h))*(yr)
        
        if not (('Splitter.Flip' in self.md.getEntryNames() and not self.md.getEntry('Splitter.Flip'))):          
            yn += ch1*(h - 2*yn) 
            
        #print xn, yn
            
        #chromatic shift
        if 'chroma.dx' in self.md.getEntryNames():
            dx = self.md['chroma.dx'].ev((xn+x0)*vx, (yn+y0)*vy)/vx
            dy = self.md['chroma.dy'].ev((xn+x0)*vy, (yn+y0)*vy)/vy
        
            xn += dx*ch1
            yn += dy*ch1
        
        #print xn, yn
       
        return np.clip(xn, 0, w-1), np.clip(yn, 0, h-1)
        
    def __remapSplitterCoords(self, x,y):
        vx = self.md['voxelsize.x']*1e3
        vy = self.md['voxelsize.y']*1e3
        
        x0 = (self.md['Camera.ROIPosX'] - 1)
        y0 = (self.md['Camera.ROIPosY'] - 1)
        
        if 'Splitter.Channel0ROI' in self.md.getEntryNames():
            xg, yg, w, h = self.md['Splitter.Channel0ROI']
            #x0 -= (self.md['Camera.ROIPosX'] - 1)
            #y0 -= (self.md['Camera.ROIPosY'] - 1)
            
            xr, yr, w, h = self.md['Splitter.Channel1ROI']
            #x1 -= (self.md['Camera.ROIPosX'] - 1)
            #y1 -= (self.md['Camera.ROIPosY'] - 1)
        else:
            xg,yg, w, h = 0,0,self.data.shape[0], self.data.shape[1]
            xr, yr = w,h
            
        #ch1 = (x>=x1)&(y >= y1)
            
        xn = x + (xr - xg)
        yn = y + (yr -yg)
        
        #print y1
        
        if not (('Splitter.Flip' in self.md.getEntryNames() and not self.md.getEntry('Splitter.Flip'))):          
            yn = (h - y) + yr - yg 
            
            
        #chromatic shift
        if 'chroma.dx' in self.md.getEntryNames():
            dx = self.md['chroma.dx'].ev((x+x0)*vx, (y+y0)*vy)/vx
            dy = self.md['chroma.dy'].ev((x+x0)*vx, (y+y0)*vy)/vy
            
            #print dx, dy
        
            xn -= dx
            yn -= dy
        
        #print xn, yn
       
        return xn, yn
        
    def _getSplitterROIs(self):
        x0 = (self.md['Camera.ROIPosX'] - 1)
        y0 = (self.md['Camera.ROIPosY'] - 1)  
        
        #print x0, y0
        
        if 'Splitter.Channel0ROI' in self.md.getEntryNames():
            xg, yg, wg, hg = self.md['Splitter.Channel0ROI']                       
            xr, yr, wr, hr = self.md['Splitter.Channel1ROI']
            #print 'Have splitter ROIs'
        else:
            xg = 0
            yg = 0
            wg = self.data.shape[0]
            hg = self.data.shape[1]/2
            
            xr = 0
            yr = hg
            wr = self.data.shape[0]
            hr = self.data.shape[1]/2
            
        def _bdsClip(x, w, x0, iw):
            x -= x0
            if (x < 0):
                w += x
                x = 0
            if ((x + w) > iw):
                w -= (x + w) - iw
                
            return x, w
            
        xg, wg = _bdsClip(xg, wg, x0, self.data.shape[0])
        xr, wr = _bdsClip(xr, wr, 0, self.data.shape[0])
        yg, hg = _bdsClip(yg, hg, y0, self.data.shape[1])
        yr, hr = _bdsClip(yr, hr, 0, self.data.shape[1])
        
        #print xr, wr
            
        w = min(wg, wr)
        h = min(hg, hr)
                
        if ('Splitter.Flip' in self.md.getEntryNames() and not self.md.getEntry('Splitter.Flip')):
            step = 1
        else:
            step = -1
            
        return slice(xg, xg+w, 1), slice(xr, xr+w, 1),slice(yg, yg+h, 1),slice(yr, yr+h, step)


    def __call__(self, gui=False, taskQueue=None):
        global dBuffer, bBuffer, dataSourceID, nTasksProcessed
                        
        fitMod = __import__('PYME.Analysis.FitFactories.' + self.fitModule, fromlist=['PYME', 'Analysis','FitFactories']) #import our fitting module

        DataSource = __import__('PYME.Analysis.DataSources.' + self.dataSourceModule, fromlist=['DataSource']).DataSource #import our data source
        
        #create a local copy of the metadata        
        md = copy.copy(self.md)
        md.tIndex = self.index
        md.taskQueue = taskQueue
        md.dataSourceID = self.dataSourceID

        #read the data
        if not dataSourceID == self.dataSourceID: #avoid unnecessary opening and closing of 
            dBuffer = dataBuffer(DataSource(self.dataSourceID, taskQueue), self.bufferLen)
            
            if 'Analysis.PCTBackground' in self.md.getEntryNames() and self.md['Analysis.PCTBackground'] > 0:
                bBuffer = backgroundBufferM(dBuffer, self.md['Analysis.PCTBackground'])
            else:
                bBuffer = backgroundBuffer(dBuffer)
            dataSourceID = self.dataSourceID
        
        self.data = dBuffer.getSlice(self.index)
        nTasksProcessed += 1
        #print self.index

        #when camera buffer overflows, empty pictures are produced - deal with these here
        if self.data.max() == 0:
            return fitResult(self, [])
        
        #squash 4th dimension
        self.data = self.data.reshape((self.data.shape[0], self.data.shape[1],1))


        #calculate background
        self.bg = self.md['Camera.ADOffset']
        if not len(self.bgindices) == 0:
            self.bg = bBuffer.getBackground(self.bgindices).reshape(self.data.shape)

        
        #############################################
        # Special cases - defer object finding to fit module
        
        if self.fitModule == 'ConfocCOIR': #special case - no object finding
            self.res = fitMod.ConfocCOI(self.data, md, background = self.bg)
            return fitResult(self, self.res, [])
            
        if 'MULTIFIT' in dir(fitMod):
            #fit module does it's own object finding
            ff = fitMod.FitFactory(self.data, md, background = self.bg)
            self.res = ff.FindAndFit(self.threshold, gui=gui)
            return fitResult(self, self.res, [])
            

        ##############################################        
        # Find candidate molecule positions

        bgd = (self.data.astype('f') - self.bg)

        
        if 'Splitter.TransmittedChannel' in self.md.getEntryNames():
            #don't find points in transmitted light channel
            transChan = md.getEntry('Splitter.TransmitedChannel')
            if transChan == 'Top':
                bgd[:, :(self.data.shape[1]/2)] = 0 #set upper half of image to zero
    
        #defne splitter mapping function (if appropriate) for use in object finding
        sfunc = None        
        if self.fitModule in splitterFitModules:            
            sfunc = self.__mapSplitterCoords


        if 'PRI.Axis' in self.md.getEntryNames() and not self.md['PRI.Axis'] == 'none':
            self.ofd = ofind_pri.ObjectIdentifier(bgd * (bgd > 0), md, axis = self.md['PRI.Axis'])
        else:# not 'PSFFile' in self.md.getEntryNames():
            self.ofd = ofind.ObjectIdentifier(bgd * (bgd > 0))
        #else: #if we've got a PSF then use cross-correlation object identificatio      
        #    self.ofd = ofind_xcorr.ObjectIdentifier(bgd * (bgd > 0), md, 7, 5e-2)
            

        if 'Analysis.DebounceRadius' in self.md.getEntryNames():
            debounce = self.md.getEntry('Analysis.DebounceRadius')
        else:
            debounce = 5
            
        self.ofd.FindObjects(self.calcThreshold(),0, splitter=sfunc, debounceRadius=debounce)
        
        
        ####################################################
        # Find Fiducials
        if self.driftEst: #do the same for objects which are on the whole time
            self.mIm = numpy.ones(self.data.shape, 'f')
            for dri in self.driftEstInd:
                bs = dBuffer.getSlice(dri)
                bs = bs.reshape(self.data.shape)
                #multiply images together, thus favouring images which are on over multiple frames
                self.mIm = self.mIm*numpy.maximum(bs.astype('f') - numpy.median(bs.ravel()), 1)
            
            #self.mIm = numpy.absolute(self.mIm)
            if not 'PSFFile' in self.md.getEntryNames():
                self.ofdDr = ofind.ObjectIdentifier(self.mIm)
            else:
                self.ofdDr = ofind_xcorr.ObjectIdentifier(self.mIm, self.md.getEntry('PSFFile'), 7, 3e-2)
                
            thres = self.calObjThresh**10
            self.ofdDr.FindObjects(thres,0, splitter=sfunc, debounceRadius=debounce)
            
            while len(self.ofdDr) >= 10: #just go for the brightest ones
                thres = thres * max(2, len(self.ofdDr)/5)
                self.ofdDr.FindObjects(thres,0, splitter=sfunc, debounceRadius=debounce)
                
                
        
        #####################################################################
        #If we are using a splitter, chop the largest common ROI out of the two channels
        
        if self.fitModule in splitterFitModules:
            xgs, xrs, ygs, yrs = self._getSplitterROIs()
            g = self.data[xgs, ygs]
            r = self.data[xrs, yrs]
            
            self.data = numpy.concatenate((g.reshape(g.shape[0], -1, 1), r.reshape(g.shape[0], -1, 1)),2)
            
            if not len(self.bgindices) == 0:
                g_ = self.bg[xgs,ygs]
                r_ = self.bg[xrs,yrs]
                self.bg = numpy.concatenate((g_.reshape(g.shape[0], -1, 1), r_.reshape(g.shape[0], -1, 1)),2)

                 
        
        #If we're running under a gui - display found objects
        if gui:
            import pylab
            cm = pylab.cm
            pylab.clf()
            pylab.imshow(self.ofd.filteredData.T, cmap=pylab.cm.hot, hold=False)
            xc = np.array([p.x for p in self.ofd])
            yc = np.array([p.y for p in self.ofd])
            pylab.plot(xc, yc, 'o', mew=2, mec='g', mfc='none', ms=9)

            if self.fitModule in splitterFitModules:
                xn, yn = self.__remapSplitterCoords(xc, yc)
                pylab.plot(xn, yn, 'o', mew=2, mec='r', mfc='none', ms=9)


            if self.driftEst:
                pylab.plot([p.x for p in self.ofdDr], [p.y for p in self.ofdDr], 'o', mew=2, mec='b', mfc='none', ms=9)
            #axis('image')
            #gca().set_ylim([255,0])
            pylab.colorbar()
            pylab.show()

        #########################################################
        #Create a fit 'factory'
        #if self.fitModule == 'LatGaussFitFRTC'  or self.fitModule == 'BiplaneFitR':
        #    fitFac = fitMod.FitFactory(numpy.concatenate((g.reshape(g.shape[0], -1, 1), r.reshape(g.shape[0], -1, 1)),2), md)
        #else:
        fitFac = fitMod.FitFactory(self.data, md, background = self.bg)

        #print 'Have Fit Factory'
        
        #perform fit for each point that we detected
        if 'FitResultsDType' in dir(fitMod):
            self.res = numpy.empty(len(self.ofd), fitMod.FitResultsDType)
            if 'Analysis.ROISize' in md.getEntryNames():
                rs = md.getEntry('Analysis.ROISize')
                for i in range(len(self.ofd)):
                    p = self.ofd[i]
                    self.res[i] = fitFac.FromPoint(p.x, p.y, roiHalfSize=rs)
            else:
                for i in range(len(self.ofd)):
                    p = self.ofd[i]
                    self.res[i] = fitFac.FromPoint(p.x, p.y)
        else:
            self.res  = [fitFac.FromPoint(p.x, p.y) for p in self.ofd]

        self.drRes = []
        if self.driftEst:
            nToFit = min(10,len(self.ofdDr)) #don't bother fitting lots of calibration objects 
            if 'FitResultsDType' in dir(fitMod):
                self.drRes = numpy.empty(nToFit, fitMod.FitResultsDType)
                for i in range(nToFit):
                    p = self.ofdDr[i]
                    self.drRes[i] = fitFac.FromPoint(p.x, p.y)
            else:
                self.drRes  = [fitFac.FromPoint(p.x, p.y) for p in self.ofd[:nToFit]]    

        #print fitResult(self, self.res, self.drRes)
        return fitResult(self, self.res, self.drRes)

    def calcThreshold(self):
        from scipy import ndimage
        if self.SNThreshold:
            fudgeFactor = 1 #to account for the fact that the blurring etc... in ofind doesn't preserve intensities - at the moment completely arbitrary so a threshold setting of 1 results in reasonable detection.
            return (numpy.sqrt(self.md.Camera.ReadNoise**2 + numpy.maximum(self.md.Camera.ElectronsPerCount*(self.md.Camera.NoiseFactor**2)*(ndimage.gaussian_filter((self.data.astype('f') - self.md.Camera.ADOffset).sum(2), 2))*self.md.Camera.TrueEMGain, 1))/self.md.Camera.ElectronsPerCount)*fudgeFactor*self.threshold
        else:
            return self.threshold
