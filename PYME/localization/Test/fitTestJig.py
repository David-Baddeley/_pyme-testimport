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

import numpy
from PYME.Acquire.Hardware.Simulator.fakeCam import NoiseMaker
#import numpy as np

splitterFitModules = ['SplitterFitFR','SplitterFitQR','SplitterFitCOIR', 'BiplaneFitR', 'SplitterShiftEstFR', 'SplitterObjFindR', 'SplitterFitPsfIR']

from pylab import *
import copy
from PYME.IO import MetaDataHandler
from PYME.Acquire.Hardware import EMCCDTheory
from scipy import optimize

def emg(v, rg):
    return (EMCCDTheory.M((80. + v)/(255 + 80.), 6.6, -70, 536, 2.2) - rg)**2

#[A, x0, y0, 250/2.35, dataMean.min(), .001, .001]

class fitTestJig(object):
    def __init__(self, metadata, fitModule = None):
        self.md = copy.copy(metadata)
        if fitModule == None:
            self.fitModule = self.md.getEntry('Analysis.FitModule')
        else:
            self.fitModule = fitModule
        self.md.tIndex = 0
        
        self.bg = 0
        if 'Test.Background' in self.md.getEntryNames():
            self.bg = float(self.md['Test.Background'])
            
        emGain = optimize.fmin(emg, 150, args=[self.md.Camera.TrueEMGain])[0]

        self.noiseM = NoiseMaker(EMGain=emGain, floor=self.md.Camera.ADOffset, background=self.bg, QE=1.0)


    @classmethod
    def fromMDFile(cls, mdfile):
        return cls(MetaDataHandler.SimpleMDHandler(mdfile))


    def runTests(self, params=None, param_jit=None, nTests=100):
        if not params:
            params = self.md['Test.DefaultParams']
        if not param_jit:
            param_jit = self.md['Test.ParamJitter']
            
        self.fitMod = __import__('PYME.localization.FitFactories.' + self.fitModule, fromlist=['PYME', 'localization', 'FitFactories']) #import our fitting module
        self.res = numpy.empty(nTests, self.fitMod.FitResultsDType)
        ps = numpy.zeros((nTests, len(params)), 'f4')

        rs=11
        
        
        
        md2 = copy.copy(self.md)
        if 'Test.PSFFile' in self.md.getEntryNames():
            md2['PSFFile'] = self.md['Test.PSFFile']
        
        for i in range(nTests):
            p = array(params) + array(param_jit)*(2*rand(len(param_jit)) - 1)
            p[0] = abs(p[0])
            ps[i, :] = p
            self.data, self.x0, self.y0, self.z0 = self.fitMod.FitFactory.evalModel(p, md2, roiHalfSize=rs)#, roiHalfSize= roiHalfWidth))
            
            #print self.data.shape
            
            #from PYME.DSView import View3D
            #View3D(self.data)

            self.d2 = self.noiseM.noisify(self.data)
            #print self.d2.min(), self.d2.max(), self.data.min(), self.data.max()
            
            #print self.d2.shape
            
            bg = self.bg*self.md.Camera.TrueEMGain/self.md.Camera.ElectronsPerCount
            
            #print bg, self.md.Camera.ADOffset

            self.fitFac = self.fitMod.FitFactory(atleast_3d(self.d2), self.md, background = bg + self.md.Camera.ADOffset)
            self.res[i] = self.fitFac.FromPoint(rs, rs)#, roiHalfSize=rs)

        
        self.ps = ps.view(self.res['fitResults'].dtype)
        
        #self.calcMEs()
        #return ps.view(self.res['fitResults'].dtype), self.res
        
    def calcMEs(self):
        for varName in self.ps.dtype.names:
            yv = self.res['fitResults'][varName]
            if hasattr(self, varName):
                yv += self.__getattribute__(varName)
                
            me = ((self.ps[varName].ravel() - yv)**2).mean()
            print(('%s: %3.2f' % (varName, me)))
            
    def error(self, varName):
        xv = self.ps[varName].ravel()
        yv = self.res['fitResults'][varName]
        if hasattr(self, varName):
            yv = yv + self.__getattribute__(varName)
            
        return yv - xv

    def plotRes(self, varName):
        #print self.ps
        from pylab import *
        figure()
        #print varName
        xv = self.ps[varName].ravel()
        
        sp = self.res['startParams'][varName]
        yv = self.res['fitResults'][varName]

        if hasattr(self, varName):
            sp = sp + self.__getattribute__(varName)
            yv = yv + self.__getattribute__(varName)

        err = self.res['fitError'][varName]

        plot([xv.min(), xv.max()], [xv.min(), xv.max()])
        plot(xv, sp, '+', label='Start Est')
        errorbar(xv, yv, err, fmt='x', label='Fitted')

        ylim((yv - maximum(err, 0)).min(), (yv + maximum(err, 0)).max())
        legend()

        title(varName)
        xlabel('True Position')
        ylabel('Estimated Position')









    
