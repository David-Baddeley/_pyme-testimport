#!/usr/bin/python

##################
# remFitBuf.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import numpy
from PYME.Acquire.Hardware.Simulator.fakeCam import NoiseMaker
#import numpy as np

splitterFitModules = ['SplitterFitFR','SplitterFitQR','SplitterFitCOIR', 'BiplaneFitR', 'SplitterShiftEstFR', 'SplitterObjFindR', 'SplitterFitPsfIR']

from pylab import *
import copy
from PYME.Acquire import MetaDataHandler

#[A, x0, y0, 250/2.35, dataMean.min(), .001, .001]

class fitTestJig(object):
    def __init__(self, metadata, fitModule = None):
        self.md = copy.copy(metadata)
        if fitModule == None:
            self.fitModule = self.md.getEntry('Analysis.FitModule')
        else:
            self.fitModule = fitModule
        self.md.tIndex = 0

        self.noiseM = NoiseMaker(EMGain=150, floor=self.md.Camera.ADOffset)


    @classmethod
    def fromMDFile(cls, mdfile):
        return cls(MetaDataHandler.SimpleMDHandler(mdfile))


    def runTests(self, params=None, param_jit=None, nTests=100):
        if not params:
            params = self.md['Test.DefaultParams']
        if not param_jit:
            param_jit = self.md['Test.ParamJitter']
            
        self.fitMod = __import__('PYME.Analysis.FitFactories.' + self.fitModule, fromlist=['PYME', 'Analysis','FitFactories']) #import our fitting module
        self.res = numpy.empty(nTests, self.fitMod.FitResultsDType)
        ps = numpy.zeros((nTests, len(params)), 'f4')

        rs=5
        for i in range(nTests):
            p = array(params) + array(param_jit)*(2*rand(len(param_jit)) - 1)
            p[0] = abs(p[0])
            ps[i, :] = p
            self.data, self.x0, self.y0, self.z0 = self.fitMod.FitFactory.evalModel(p, self.md, roiHalfSize=rs)#, roiHalfSize= roiHalfWidth))
            
            #print self.data.shape

            self.d2 = self.noiseM.noisify(self.data)
            
            #print self.d2.shape

            self.fitFac = self.fitMod.FitFactory(atleast_3d(self.d2), self.md, background = 0)
            self.res[i] = self.fitFac.FromPoint(rs, rs, roiHalfSize=rs)

        
        self.ps = ps.view(self.res['fitResults'].dtype)
        #return ps.view(self.res['fitResults'].dtype), self.res


    def plotRes(self, varName):
        #print self.ps
        from pylab import *
        figure()
        #print varName
        xv = self.ps[varName].ravel()
        
        sp = self.res['startParams'][varName]
        yv = self.res['fitResults'][varName]

        if hasattr(self, varName):
            sp += self.__getattribute__(varName)
            yv += self.__getattribute__(varName)

        err = self.res['fitError'][varName]

        plot([xv.min(), xv.max()], [xv.min(), xv.max()])
        plot(xv, sp, '+', label='Start Est')
        errorbar(xv, yv, err, fmt='x', label='Fitted')

        ylim((yv - maximum(err, 0)).min(), (yv + maximum(err, 0)).max())
        legend()

        title(varName)
        xlabel('True Position')
        ylabel('Estimated Position')









    