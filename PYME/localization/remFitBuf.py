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
from PYME.localization import ofind
#import ofind_nofilt #use for drift estimation - faster
#import ofind_xcorr
#try:
    #try to use the FFTW version if we have fftw installed
#    import ofind_xcorr_fw as ofind_xcorr
#except:
    #fall back on fftpack in scipy
    #this was only marginally slower at last benchmark implying much of the 
    #cost is not in the ffts
from PYME.localization import ofind_xcorr
from PYME.localization import ofind_pri

from PYME.IO import buffers
from PYME.IO.image import ImageStack

import logging
logger = logging.getLogger(__name__)
    
import numpy
import numpy as np

from PYME.IO.FileUtils.nameUtils import getFullExistingFilename

bufferMisses = 0
nTasksProcessed = 0

splitterFitModules = ['SplitterFitFR', 'SplitterFitFNR','SplitterFitQR', 'SplitterFitCOIR', 'SplitterFitFNSR',
                      'BiplaneFitR', 'SplitterShiftEstFR', 'SplitterFitFusionR',
                      'SplitterObjFindR', 'SplitterFitInterpR', 'SplitterFitInterpQR', 'SplitterFitInterpNR', 'SplitterFitInterpBNR', 'SplitterROIExtractNR']

#from pylab import *

import copy

def tqPopFcn(workerN, NWorkers, NTasks):
    #let each task work on its own chunk of data ->
    return workerN * NTasks/NWorkers 
    
class fitResult(taskDef.TaskResult):
    def __init__(self, task, results, driftResults):
        taskDef.TaskResult.__init__(self, task)
        self.index = task.index #the task number so that the taskQueue know which task this was (used to manage the list of in-progress tasks)
        self.results = results # a numpy ndarray with the positions of the fitted molecules
        self.driftResults = driftResults # a numpy ndarray with the positions of fiducials used to track drift

class BufferManager(object):
    """Keeps track of data sources and buffering over individual fitTask instances"""
    def __init__(self):
        self.dBuffer = None
        self.bBuffer = None
        self.dataSourceID = None
        
    def updateBuffers(self, md, dataSourceModule, bufferLen):
        """Update the various buffers. """
        if dataSourceModule is None:
            #if the data source module is not specified, guess based on data source ID
            import PYME.IO.DataSources
            DataSource = PYME.IO.DataSources.getDataSourceForFilename(md.dataSourceID)
        else:
            DataSource = __import__('PYME.IO.DataSources.' + dataSourceModule, fromlist=['DataSource']).DataSource #import our data source

        #read the data
        if not self.dataSourceID == md.dataSourceID: #avoid unnecessary opening and closing 
            self.dBuffer = buffers.dataBuffer(DataSource(md.dataSourceID, md.taskQueue), bufferLen)
            self.bBuffer = None
        
        #fix our background buffers
        if md.getOrDefault('Analysis.PCTBackground', 0) > 0:
            if not isinstance(self.bBuffer, buffers.backgroundBufferM):
                self.bBuffer = buffers.backgroundBufferM(self.dBuffer, md['Analysis.PCTBackground'])
            else:
                self.bBuffer.pctile = md['Analysis.PCTBackground']
        else:
            if not isinstance(self.bBuffer, buffers.backgroundBuffer):
                self.bBuffer = buffers.backgroundBuffer(self.dBuffer)
                
        self.dataSourceID = md.dataSourceID

#instance of our buffer manager
bufferManager = BufferManager()

class CameraInfoManager(object):
    """Manages camera information such as dark frames, variance maps, and flatfielding"""
    def __init__(self):
        self._cache = {}

    def _parseROI(self, md):
        """Extract ROI coordinates from metadata"""
        x0 = (md['Camera.ROIPosX'] - 1)
        y0 = (md['Camera.ROIPosY'] - 1)
        x1 = x0 + md['Camera.ROIWidth']
        y1 = y0 + md['Camera.ROIHeight']

        return x0, y0, x1, y1

    def _fetchMap(self, md, mapName):
        """retrive a map, with a given name. First try and get it from the Queue,
        then try finding it locally"""
        try:
            varmap = md.taskQueue.getQueueData(md.dataSourceID, 'MAP',  mapName)
        except:
            fn = getFullExistingFilename(mapName)
            varmap = ImageStack(filename=fn).data[:,:,0].squeeze() #this should handle .tif, .h5, and a few others

        return varmap

    def _getMap(self, md, mapName):
        """Returns the map specified, from cache if possible"""
        if mapName is None or mapName == '' or mapName == '<none>':
            return None

        ROI = self._parseROI(md)
        mapKey = (mapName, ROI)

        try:
            mp = self._cache[mapKey]
        except KeyError: 
            #cache miss
            x0, y0, x1, y1 = ROI
            mp = self._fetchMap(md, mapName)[x0:x1, y0:y1]
            
            self._cache[mapKey] = mp

        return mp

    def getVarianceMap(self, md):
        """Returns the pixel variance map specified in the supplied metadata, from cache if possible.
        The variance map should be in units of *photoelectrons*."""
        varMapName = md.getOrDefault('Camera.VarianceMapID', None)

        mp = self._getMap(md, varMapName)

        if (mp is None):
            #default to uniform read noise
            rn = float(md['Camera.ReadNoise'])
            return rn*rn
        else:
            return mp


    def getDarkMap(self, md):
        """Returns the dark map specified in the supplied metadata, from cache if possible.
        The dark map is in units of camera counts"""
        darkMapName = md.getOrDefault('Camera.DarkMapID', None)

        mp = self._getMap(md, darkMapName)
        if (mp is None):
            return float(md.getOrDefault('Camera.ADOffset', 0))
        else:
            return mp

    def getFlatfieldMap(self, md):
        """Returns the flatfield map specified in the supplied metadata, from cache if possible
        The flatfield is a (floating point) value which is multiplied with the image to correct
        variations in response. It should (usually) have a mean value of 1."""
        flatfieldMapName = md.getOrDefault('Camera.FlatfieldMapID', None)

        mp = self._getMap(md, flatfieldMapName)

        if (mp is None):
            return 1.0
        else:
            return mp

    def correctImage(self, md, img):
        dk = self.getDarkMap(md)
        flat = self.getFlatfieldMap(md)

        return (img.astype('f')-dk)*flat

cameraMaps = CameraInfoManager()

def createFitTaskFromTaskDef(task):
    """
    Creates a fit task from a new-style json task definition
    Parameters
    ----------
    task : dict
        The parsed task definition. As the task definition will need to be parsed by the worker before we get here,
        we expect this to take the form of a python dictionary.

    Returns
    -------

    a fitTask instance

    """
    from PYME.IO import MetaDataHandler

    dataSourceID = task['inputs']['frames']
    frameIndex = int(task['taskdef']['frameIndex'])

    #logger.debug('Creating a task for %s - frame %d' % (dataSourceID, frameIndex))

    md = task['taskdef']['metadata']

    #sort out our metadata
    #TODO - Move this somewhere saner - e.g. a helper function in the MetaDataHandler module
    mdh = MetaDataHandler.NestedClassMDHandler()
    if isinstance(md, dict):
        #metadata was parsed with the enclosing json
        mdh.update(md)
    elif isinstance(md, str) or isinstance(md, unicode):
        if md.startswith('{'):
            #metadata is a quoted json dump
            import json
            mdh.update(json.loads(md))
        else:
            #metadata entry is a filename/URI
            from PYME.IO import unifiedIO
            if md.endswith('.json'):
                import json
                mdh.update(json.loads(unifiedIO.read(md)))
            else:
                raise NotImplementedError('Loading metadata from a URI in task description is not yet supported')

    return fitTask(dataSourceID=dataSourceID, frameIndex=frameIndex, metadata=mdh)

class fitTask(taskDef.Task):
    def __init__(self, dataSourceID, frameIndex, metadata, dataSourceModule=None, resultsURI=None):
        """
        Create a new fit task for performing single molecule localization tasks.

        Parameters
        ----------
        dataSourceID : str
            A filename or URI which identifies the data source
        frameIndex : int
            The frame to fit
        metadata : PYME.IO.MetaDataHandler object
            The image metadata. This defines most of the analysis parameters.
        dataSourceModule : str
            The name of the data source module to use. If None, the dataSourceModule is inferred from the dataSourceID.
        resultsURI : str
            A URI dictating where to store the analysis results.
        """
        
        taskDef.Task.__init__(self, resultsURI=resultsURI)

        self.dataSourceID = dataSourceID
        self.dataSourceModule = dataSourceModule
        self.index = frameIndex

        self.md = metadata
        self._fitMod = None

        #extract remaining parameters from metadata
        self.fitModule = self.md['Analysis.FitModule']

        self.threshold = self.md['Analysis.DetectionThreshold']
        self.SNThreshold = self.md.getOrDefault('Analysis.SNRThreshold', True)
        
        self.driftEst = self.md.getOrDefault('Analysis.TrackFiducials', False)
                 
        self.bufferLen = 50 #12
        if self.driftEst: 
            #increase the buffer length as we're going to look forward as well
            self.bufferLen = 50 #17

        self._get_bgindices()
        
    @property
    def fitMod(self):
        if self._fitMod is None:
            self._fitMod = __import__('PYME.localization.FitFactories.' + self.fitModule, fromlist=['PYME', 'localization', 'FitFactories']) #import our fitting module
         
        return self._fitMod
    
    @property
    def is_splitter_fit(self):
        return self.fitModule in splitterFitModules or getattr(self.fitMod, 'SPLITTER_FIT', False)
    

    def _get_bgindices(self):
        if not 'Analysis.BGRange' in self.md.getEntryNames():
            if 'Analysis.NumBGFrames' in self.md.getEntryNames():
                nBGFrames = self.md.Analysis.NumBGFrames
            else:
                nBGFrames = 10

            self.md.setEntry('Analysis.BGRange', (-nBGFrames, 0))

        self.bgindices = range(max(self.index + self.md['Analysis.BGRange'][0], self.md.getOrDefault('EstimatedLaserOnFrameNo', 0)),
                               max(self.index + self.md['Analysis.BGRange'][1], self.md.getOrDefault('EstimatedLaserOnFrameNo', 0)))
            
    def __mapSplitterCoords(self, x,y):
        vx = self.md['voxelsize.x']*1e3
        vy = self.md['voxelsize.y']*1e3
        
        x0 = (self.md['Camera.ROIPosX'] - 1)
        y0 = (self.md['Camera.ROIPosY'] - 1)
        
        if 'Splitter.Channel0ROI' in self.md.getEntryNames():
            xg, yg, w, h = self.md['Splitter.Channel0ROI']            
            xr, yr, w, h = self.md['Splitter.Channel1ROI']
        else:
            xg,yg, w, h = 0,0,self.data.shape[0], self.data.shape[1]
            xr, yr = w,h
            
        ch1 = (x>=(xr - x0))&(y >= (yr - y0))
            
        xn = x - (x >= (xg-x0+w))*(xr)
        yn = y - (y >= (yg-y0+h))*(yr)
        
        if not (('Splitter.Flip' in self.md.getEntryNames() and not self.md.getEntry('Splitter.Flip'))):          
            yn += ch1*(h - 2*yn) 
            
        #chromatic shift
        if 'chroma.dx' in self.md.getEntryNames():
            dx = self.md['chroma.dx'].ev((xn+x0)*vx, (yn+y0)*vy)/vx
            dy = self.md['chroma.dy'].ev((xn+x0)*vy, (yn+y0)*vy)/vy
        
            xn += dx*ch1
            yn += dy*ch1
       
        return np.clip(xn, 0, w-1), np.clip(yn, 0, h-1)
        
    def __remapSplitterCoords(self, x,y):
        vx = self.md['voxelsize.x']*1e3
        vy = self.md['voxelsize.y']*1e3
        
        x0 = (self.md['Camera.ROIPosX'] - 1)
        y0 = (self.md['Camera.ROIPosY'] - 1)
        
        if 'Splitter.Channel0ROI' in self.md.getEntryNames():
            xg, yg, w, h = self.md['Splitter.Channel0ROI']            
            xr, yr, w, h = self.md['Splitter.Channel1ROI']
        else:
            xg,yg, w, h = 0,0,self.data.shape[0], self.data.shape[1]
            xr, yr = w,h
            
        xn = x + (xr - xg)
        yn = y + (yr -yg)
        
        if not (('Splitter.Flip' in self.md.getEntryNames() and not self.md.getEntry('Splitter.Flip'))):          
            yn = (h - y) + yr - yg             
            
        #chromatic shift
        if 'chroma.dx' in self.md.getEntryNames():
            dx = self.md['chroma.dx'].ev((x+x0)*vx, (y+y0)*vy)/vx
            dy = self.md['chroma.dy'].ev((x+x0)*vx, (y+y0)*vy)/vy
        
            xn -= dx
            yn -= dy
       
        return xn, yn
        
    def _getSplitterROIs(self):
        if not '_splitterROICache' in dir(self):
            x0 = (self.md['Camera.ROIPosX'] - 1)
            y0 = (self.md['Camera.ROIPosY'] - 1)  
            
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
                
            w = min(wg, wr)
            h = min(hg, hr)
                    
            if ('Splitter.Flip' in self.md.getEntryNames() and not self.md.getEntry('Splitter.Flip')):
                step = 1
                self._splitterROICache = (slice(xg, xg+w, 1), slice(xr, xr+w, 1),slice(yg, yg+h, 1),slice(yr, yr+h, step))
            else:
                step = -1
                self._splitterROICache = (slice(xg, xg+w, 1), slice(xr, xr+w, 1),slice(yg, yg+h, 1),slice(yr+h, yr, step))
                
            
            
        return self._splitterROICache
        
    def _splitImage(self, img):
        xgs, xrs, ygs, yrs = self._getSplitterROIs()
        g = img[xgs, ygs]
        r = img[xrs, yrs]
        
        #print g.shape, r.shape
        
        return numpy.concatenate((g.reshape(g.shape[0], -1, 1), r.reshape(g.shape[0], -1, 1)),2)


    def __call__(self, gui=False, taskQueue=None):
        global dBuffer, bBuffer, dataSourceID, nTasksProcessed
        
        #create a local copy of the metadata        
        md = copy.copy(self.md)
        md.tIndex = self.index
        md.taskQueue = taskQueue
        md.dataSourceID = self.dataSourceID

        #logging.debug('dataSourceID: %s, cachedDSID: %s', md.dataSourceID, bufferManager.dataSourceID)

        #make sure we're buffering the right data stream
        bufferManager.updateBuffers(md, self.dataSourceModule, self.bufferLen)
        
        self.data = bufferManager.dBuffer.getSlice(self.index)
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('data: min - %3.2f, max - %3.2f, mean - %3.2f' % (self.data.min(), self.data.max(), self.data.mean()))
        nTasksProcessed += 1
        #print self.index

        #when camera buffer overflows, empty pictures are produced - deal with these here
        if self.data.max() == 0:
            return fitResult(self, [], [])
        
        #squash 4th dimension
        #NB - this now subtracts the ADOffset
        self.data = cameraMaps.correctImage(md, self.data.squeeze()).reshape((self.data.shape[0], self.data.shape[1],1))

        #calculate background
        self.bg = 0
        if not len(self.bgindices) == 0:
            self.bg = cameraMaps.correctImage(md, bufferManager.bBuffer.getBackground(self.bgindices)).reshape(self.data.shape)

        #calculate noise
        self.sigma = self.calcSigma(md, self.data)

        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('data_mean: %3.2f, bg: %3.2f, sigma: %3.2f' % (self.data.mean(), self.sigma.mean(), self.bg.mean()))
        
        #############################################
        # Special cases - defer object finding to fit module
        
        if self.fitModule == 'ConfocCOIR': #special case - no object finding
            self.res = self.fitMod.ConfocCOI(self.data, md, background = self.bg)
            return fitResult(self, self.res, [])
            
        if 'MULTIFIT' in dir(self.fitMod):
            #fit module does it's own object finding
            ff = self.fitMod.FitFactory(self.data, md, background = self.bg, noiseSigma=self.sigma)
            self.res = ff.FindAndFit(self.threshold, gui=gui, cameraMaps=cameraMaps)
            return fitResult(self, self.res, [])
            

        ##############################################        
        # Find candidate molecule positions
        bgd = (self.data.astype('f') - self.bg)
        
        #print bgd.shape, self.calcThreshold().shape

        if 'Splitter.TransmittedChannel' in self.md.getEntryNames():
            #don't find points in transmitted light channel
            transChan = md.getEntry('Splitter.TransmitedChannel')
            if transChan == 'Top':
                bgd[:, :(self.data.shape[1]/2)] = 0 #set upper half of image to zero
    
        #define splitter mapping function (if appropriate) for use in object finding
        sfunc = None        
        if self.is_splitter_fit:
            sfunc = self.__mapSplitterCoords

        #Choose which version of ofind to use
        if 'PRI.Axis' in self.md.getEntryNames() and not self.md['PRI.Axis'] == 'none':
            self.ofd = ofind_pri.ObjectIdentifier(bgd * (bgd > 0), md, axis = self.md['PRI.Axis'])
        else:# not 'PSFFile' in self.md.getEntryNames():
            filtRadiusLowpass = md.getOrDefault('Analysis.DetectionRadiusLowpass', 1.0)
            filtRadiusHighpass = md.getOrDefault('Analysis.DetectionRadiusHighpass', 3.0)
            self.ofd = ofind.ObjectIdentifier(bgd * (bgd > 0), filterRadiusLowpass=filtRadiusLowpass, filterRadiusHighpass=filtRadiusHighpass)
        #else: #if we've got a PSF then use cross-correlation object identificatio      
        #    self.ofd = ofind_xcorr.ObjectIdentifier(bgd * (bgd > 0), md, 7, 5e-2)
        
        debounce = self.md.getOrDefault('Analysis.DebounceRadius', 5)    
        discardClumpRadius = self.md.getOrDefault('Analysis.ClumpRejectRadius', 0)
            
        self.ofd.FindObjects(self.calcThreshold(),0, splitter=sfunc, debounceRadius=debounce, discardClumpRadius = discardClumpRadius)
        
        
        ####################################################
        # Find Fiducials
        if self.driftEst:
            self.driftEstInd = self.index + self.md.getOrDefault('Analysis.DriftIndices', np.array([-10, 0, 10]))        
            self.calObjThresh = self.md.getOrDefault('Analysis.FiducialThreshold', 6)
            fiducialROISize = self.md.getOrDefault('Analysis.FiducialROISize', 11)
            self._findFiducials(sfunc, debounce)
                
        
        #####################################################################
        #If we are using a splitter, chop the largest common ROI out of the two channels
        
        if self.is_splitter_fit:
            self.data = self._splitImage(self.data)
            self.sigma = self._splitImage(self.sigma)
            
            if not len(self.bgindices) == 0:
                self.bg = self._splitImage(self.bg)
                 
        
        #If we're running under a gui - display found objects
        if gui:
            self._displayFoundObjects()

        #########################################################
        #Create a fit 'factory'
        fitFac = self.fitMod.FitFactory(self.data, md, background = self.bg, noiseSigma = self.sigma)
        
        #perform fit for each point that we detected
        if 'FromPoints' in dir(self.fitMod):
            self.res = self.fitMod.FromPoints(self.ofd)
        elif 'FitResultsDType' in dir(self.fitMod): #legacy fit modules
            self.res = numpy.empty(len(self.ofd), self.fitMod.FitResultsDType)
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

        #Fit Fiducials NOTE: This is potentially broken        
        self.drRes = []
        if self.driftEst:
            fitFac = self.fitMod.FitFactory(self.data, md, noiseSigma = self.sigma)
            nToFit = min(10,len(self.ofdDr)) #don't bother fitting lots of calibration objects 
            if 'FitResultsDType' in dir(self.fitMod):
                self.drRes = numpy.empty(nToFit, self.fitMod.FitResultsDType)
                for i in range(nToFit):
                    p = self.ofdDr[i]
                    self.drRes[i] = fitFac.FromPoint(p.x, p.y, roiHalfSize=fiducialROISize)
            else:
                self.drRes  = [fitFac.FromPoint(p.x, p.y) for p in self.ofd[:nToFit]] 
                
            #print 'Fitted %d fiducials' % nToFit, len(self.drRes)


        return fitResult(self, self.res, self.drRes)

    @classmethod
    def calcSigma(cls, md, data):
        var = np.atleast_3d(cameraMaps.getVarianceMap(md))
        return np.sqrt(var + (float(md.Camera.NoiseFactor)**2)*(float(md.Camera.ElectronsPerCount)*float(md.Camera.TrueEMGain)*np.maximum(data, 1.0) + float(md.Camera.TrueEMGain)*float(md.Camera.TrueEMGain)))/float(md.Camera.ElectronsPerCount)
    
    def calcThreshold(self):
        #from scipy import ndimage
        if self.SNThreshold:
            fudgeFactor = 1 #to account for the fact that the blurring etc... in ofind doesn't preserve intensities - at the moment completely arbitrary so a threshold setting of 1 results in reasonable detection.
            #return self.calcSigma(self.md, self.data - self.md.Camera.ADOffset)*fudgeFactor*self.threshold 
            return (self.sigma*fudgeFactor*self.threshold).squeeze()
            #return (numpy.sqrt(self.md.Camera.ReadNoise**2 + numpy.maximum(self.md.Camera.ElectronsPerCount*(self.md.Camera.NoiseFactor**2)*(ndimage.gaussian_filter((self.data.astype('f') - self.md.Camera.ADOffset).sum(2), 2))*self.md.Camera.TrueEMGain, 1))/self.md.Camera.ElectronsPerCount)*fudgeFactor*self.threshold
        else:
            return self.threshold


    
    def _findFiducials(self, sfunc, debounce): 
        ####################################################
        # Find Fiducials

        self.mIm = numpy.ones(self.data.shape, 'f')
        
        mdnm  = 1./np.median((self.data/self.sigma).ravel())
        
        for dri in self.driftEstInd:
            bs = cameraMaps.correctImage(self.md, bufferManager.dBuffer.getSlice(dri).squeeze())
            bs = bs.reshape(self.data.shape)/self.sigma
            bs = bs*mdnm
            #multiply images together, thus favouring images which are on over multiple frames
            self.mIm = self.mIm*bs
        
        #self.mIm = numpy.absolute(self.mIm)
        if not 'PSFFile' in self.md.getEntryNames():
            self.ofdDr = ofind.ObjectIdentifier(self.mIm, filterRadiusLowpass=5, filterRadiusHighpass=9)
        else:
            self.ofdDr = ofind_xcorr.ObjectIdentifier(self.mIm, self.md.getEntry('PSFFile'), 7, 3e-2)
            
        thres = self.calObjThresh**len(self.driftEstInd)
        self.ofdDr.FindObjects(thres,0, splitter=sfunc, debounceRadius=debounce)
        
        #while len(self.ofdDr) >= 10: #just go for the brightest ones
        #    thres = thres * max(2, len(self.ofdDr)/5)
        #    self.ofdDr.FindObjects(thres,0, splitter=sfunc, debounceRadius=debounce)  
            
    def _displayFoundObjects(self):
        import pylab
        #cm = pylab.cm
        pylab.clf()
        pylab.imshow(self.ofd.filteredData.T, cmap=pylab.cm.hot, hold=False)
        xc = np.array([p.x for p in self.ofd])
        yc = np.array([p.y for p in self.ofd])
        pylab.plot(xc, yc, 'o', mew=2, mec='g', mfc='none', ms=9)

        if self.is_splitter_fit:
            xn, yn = self.__remapSplitterCoords(xc, yc)
            pylab.plot(xn, yn, 'o', mew=2, mec='r', mfc='none', ms=9)


        if self.driftEst:
            pylab.plot([p.x for p in self.ofdDr], [p.y for p in self.ofdDr], 'o', mew=2, mec='b', mfc='none', ms=9)
        #axis('image')
        #gca().set_ylim([255,0])
        pylab.colorbar()
        pylab.show()
