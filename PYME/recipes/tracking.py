# -*- coding: utf-8 -*-
"""
Created on Tue Dec 29 19:59:15 2015

@author: david
"""
from .base import register_module, ModuleBase,Filter
from .traits import Input, Output, Float, Enum, CStr, Bool, Int, DictStrFloat, DictStrBool, on_trait_change

import numpy as np
import pandas as pd

from PYME.Analysis.Tracking import tracking
#from PYME.Analysis.Tracking import trackUtils

from PYME.IO import tabular

@register_module('TrackFeatures')
class TrackFeatures(ModuleBase):
    """Take just certain columns of a variable"""
    inputMeasurements = Input('measurements')
    outputTrackInfo = Output('track_info')
    outputTracks = Output('tracks')
    
    
    features = CStr('x, y')    
    pNew = Float(0.2)
    r0 = Float(500)
    pLinkCutoff = Float(0.2)
    
    minTrackLength = Int(5)
    maxParticleSize = Float(20)
    
    def __init__(self, *args, **kwargs):
        ModuleBase.__init__(self, *args, **kwargs)
        
        self._tracker = None        
        #self.clumps = []
        
    @on_trait_change('pNew, r0, pLinkCutoff')    
    def OnParamChange(self):
        if not self._tracker is None:
            self._tracker.pNew=self.pNew
            self._tracker.r0 = self.r0
            self._tracker.linkageCuttoffProb = self.pLinkCutoff
            
    @on_trait_change('features')   
    def OnFeaturesChanged(self):
        self._tracker = None
        
    def Track(self, objects, newTracker=False):
        """Track objects based on a given set of feature vectors"""
        from PYME.Analysis.Tracking import trackUtils

        if (self._tracker is None) or not (len(self._tracker.t) == len(objects['t'])) or newTracker:
            featNames = [s.strip() for s in self.features.split(',')]
            
            def _calcWeights(s):
                fw = s.split('*')
                if len(fw) == 2:
                    return float(fw[0]), fw[1]
                else:
                    return 1.0, s
                    
            
            weightedFeats = [_calcWeights(s) for s in featNames]
            
            feats = np.vstack([w*np.array(objects[fn]) for w, fn in weightedFeats])
            
            self._tracker = tracking.Tracker(np.array(objects['t']), feats)
            
            self._tracker.pNew=self.pNew
            self._tracker.r0 = self.r0
            self._tracker.linkageCuttoffProb = self.pLinkCutoff

        for i in range(1, (objects['t'].max() + 1)):
            L = self._tracker.calcLinkages(i,i-1)
            self._tracker.updateTrack(i, L)
            
        clumpSizes = np.zeros_like(self._tracker.clumpIndex)
        
        for i in set(self._tracker.clumpIndex):
            ind = (self._tracker.clumpIndex == i)
            
            clumpSizes[ind] = ind.sum()
            
        trackVelocities = trackUtils.calcTrackVelocity(objects['x'], objects['y'], self._tracker.clumpIndex)
        
        clumpInfo = {'clumpIndex': self._tracker.clumpIndex, 'clumpSize': clumpSizes, 'trackVelocity': trackVelocities}
            

        pipe = {}
        pipe.update(clumpInfo)
        pipe.update(objects)
        pipe = pd.DataFrame(pipe)
        
        if 'mdh' in dir(objects):
            #propagate metadata
            pipe.mdh = objects.mdh 
            
        clumps = trackUtils.ClumpManager(pipe)
        
        clumps = [c for c in clumps.all if (c.nEvents > self.minTrackLength) and (c.featuremean['area'] < self.maxParticleSize)]

        clumpInfo = pd.DataFrame(clumpInfo)
        
        if 'mdh' in dir(objects):
            #propagate metadata
            clumpInfo.mdh = objects.mdh
        
        return clumpInfo, clumps
        
    def execute(self, namespace):       
        meas = namespace[self.inputMeasurements]
        clumpInfo, clumps = self.Track(meas, True)
        namespace[self.outputTrackInfo] = clumpInfo
        namespace[self.outputTracks] = clumps

    
    def TrackWithPipeline(self, pipeline):
        """Support legacy interactive mode where we insert our results
        into the pipeline (used when called from PYME.DSView.modules.particleTracking)"""
        clumpInfo, clumps = self.Track(pipeline)

        pipeline.addColumn('clumpIndex', clumpInfo['clumpIndex'])
        pipeline.addColumn('clumpSize', clumpInfo['clumpSize'])
        pipeline.addColumn('trackVelocity', clumpInfo['trackVelocity'])
        
        #self.clumps = clumps        
        pipeline.clumps = clumps
        
        return clumps

@register_module('LoadSpeckles')
class LoadSpeckles(ModuleBase):
    """Loads Speckle data as used by the karatekin lab"""
    inputImage = Input('', desc='The image to which the speckles file refers. Useful for determining speckle filename, series length, and voxelsize')
    speckleFilename = CStr('{DIRNAME}{SEP}{IMAGESTUB}speckles.csv',
                           desc='The filename of the speckle file. Anything in {} will be substituted with info from the input image.')
    #mappings = DictStrStr()
    outputName = Output('speckles')
    leadFrames = Int(10, desc='The number of frames to add to the trace before the start of the speckle')
    followFrames = Int(50, desc='The number of frames to add to the trace after the end of the speckle')

    def execute(self, namespace):
        from PYME.IO.FileUtils import readSpeckle
        from PYME.IO import MetaDataHandler
        import os

        fileInfo = {'SEP' : os.sep}

        seriesLength = 100000

        mdh = MetaDataHandler.NestedClassMDHandler()
        mdh['voxelsize.x'] = .001# default pixel size - FIXME
        mdh['voxelsize.y'] = .001

        if not self.inputImage == '':
            inp = namespace[self.inputImage]
            mdh.update(inp.mdh)
            seriesLength = inp.data.shape[2]

            try:
                fileInfo['DIRNAME'], fileInfo['IMAGENAME'] = os.path.split(inp.filename)
                fileInfo['IMAGESTUB'] = fileInfo['IMAGENAME'].split('MM')[0]
            except:
                pass

        speckleFN = self.speckleFilename.format(**fileInfo)

        specks = readSpeckle.readSpeckles(speckleFN)
        traces = readSpeckle.gen_traces_from_speckles(specks, leadFrames=self.leadFrames,
                                                      followFrames=self.followFrames, seriesLength=seriesLength)

        #turn this into an inputFilter object
        inp = tabular.recArrayInput(traces)

        #create a mapping to covert the co-ordinates in pixels to co-ordinates in nm
        map = tabular.mappingFilter(inp, x = 'x_pixels*%3.2f' % (1000*mdh['voxelsize.x']),
                                    y='y_pixels*%3.2f' % (1000 * mdh['voxelsize.y']))

        map.mdh = mdh

        namespace[self.outputName] = map


@register_module('ExtractTracks')
class ExtractTracks(ModuleBase):
    """Extract tracks from a measurement set with pre-assigned clump IDs"""
    inputMeasurements = Input('speckles', desc='a set of particle positions already containing a clumpIndex column which identifies groups of particles')
    #outputTrackInfo = CStr('track_info', desc='a pandas data frame with clumpSize and trackVelocity information')
    outputTracks = Output('tracks', desc='A clump / track manager object - aka the actual tracks')

    def execute(self, namespace):
        from PYME.Analysis.Tracking import trackUtils
        #print
        data = namespace[self.inputMeasurements]

        #print 'data.keys', data.keys()
        clumpIndex = data['clumpIndex']

        #clumpSizes = np.zeros_like(clumpIndex)

        #for i in set(clumpIndex):
        #    ind = (clumpIndex == i)

         #   clumpSizes[ind] = ind.sum()

        #trackVelocities = trackUtils.calcTrackVelocity(data['x'], data['y'], clumpIndex, data['t'])

        #clumpInfo = {'clumpSize': clumpSizes, 'trackVelocity': trackVelocities}

        clumps = trackUtils.ClumpManager(data)

        clumps = [c for c in clumps.all]

        #clumpInfo = pd.DataFrame(clumpInfo)

        if 'mdh' in dir(data):
            pass
            #propagate metadata
            #clumps.mdh = data.mdh
            #clumpInfo.mdh = data.mdh

        #namespace[self.outputTrackInfo] = clumpInfo
        namespace[self.outputTracks] = clumps

@register_module('FitFusionTraces')
class FitFusionTraces(ModuleBase):
    """Extract tracks from a measurement set with pre-assigned clump IDs"""
    inputTracks = Input('tracks', desc='A clump / track manager object - with tracks corresponding to vesicle fusion events')
    outputTracks = Output('fusion_tracks', desc='A clump / track manager object - which has tracks with fusion info')
    numLeadFrames = Int(10, desc='The number of frames which the profile extends before docking. This should be the same as in the LoadSpeckles module.')
    numFollowFrames = Int(50, desc='The number of frames the trace extends after fusion. This should be the same as in the LoadSpeckles module.')
    psfSigma = Float(1.5, desc='The std deviation of the microscope PSF, in pixels')
    startParams = DictStrFloat(desc='a dictionary of parameters whose start value should be over-ridden')
    paramsToFit = DictStrBool(desc='a dictionary of parameters whose fit status should be over-ridden. Use in conjunction with startParams to fix parameters at a given value')

    def execute(self, namespace):
        from PYME.experimental import fusionRadial
        from imp import reload
        reload(fusionRadial)
        tracks = namespace[self.inputTracks]

        clumps = [fusionRadial.FusionTrack(c, numLeadFrames=self.numLeadFrames, numFollowFrames=self.numFollowFrames, sig=self.psfSigma,
                              startParams=self.startParams, fitWhich=self.paramsToFit) for c in tracks]

        if 'mdh' in dir(tracks):
            pass

        namespace[self.outputTracks] = clumps
