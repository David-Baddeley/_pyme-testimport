#!/usr/bin/python

##################
# Gauss3DFitR.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import scipy
import numpy
from scipy.signal import interpolate
import scipy.ndimage as ndimage
from pylab import *
from PYME.PSFGen.ps_app import *

from PYME.Analysis._fithelpers import *

import copy_reg

def pickleSlice(slice):
        return unpickleSlice, (slice.start, slice.stop, slice.step)

def unpickleSlice(start, stop, step):
        return slice(start, stop, step)

copy_reg.pickle(slice, pickleSlice, unpickleSlice)



def f_Gauss3d(p, X, Y, Z):
    """3D PSF model function with constant background - parameter vector [A, x0, y0, z0, background]"""
    A, x0, y0, z0, wxy, wz, b = p
    #return A*scipy.exp(-((X-x0)**2 + (Y - y0)**2)/(2*s**2)) + b

    #print X.shape

    return A*scipy.exp(-((X-x0)**2 + (Y - y0)**2)/(2*wxy**2) - ((Z-z0)**2)/(2*wz**2)) + b

class GaussFitResult:
    def __init__(self, fitResults, metadata, slicesUsed=None, resultCode=None, fitErr=None):
        self.fitResults = fitResults
        self.metadata = metadata
        self.slicesUsed = slicesUsed
        self.resultCode=resultCode
        self.fitErr = fitErr
    
    def A(self):
        return self.fitResults[0]

    def x0(self):
        return self.fitResults[1]

    def y0(self):
        return self.fitResults[2]

    def z0(self):
        return self.fitResults[3]

    def background(self):
        return self.fitResults[4]

    def renderFit(self):
        #X,Y = scipy.mgrid[self.slicesUsed[0], self.slicesUsed[1]]
        #return f_gauss2d(self.fitResults, X, Y)
        X = 1e3*self.metadata.voxelsize.x*scipy.mgrid[self.slicesUsed[0]]
        Y = 1e3*self.metadata.voxelsize.y*scipy.mgrid[self.slicesUsed[1]]
        Z = 1e3*self.metadata.voxelsize.z*scipy.mgrid[self.slicesUsed[2]]
        P = scipy.arange(0,1.01,.1)
        return f_PSF3d(self.fitResults, X, Y, Z, P, 2*scipy.pi/525, 1.47, 10e3)
        #pass
        
def replNoneWith1(n):
	if n == None:
		return 1
	else:
		return n


fresultdtype=[('tIndex', '<i4'),('fitResults', [('A', '<f4'),('x0', '<f4'),('y0', '<f4'),('z0', '<f4'),('wxy', '<f4'),('wz', '<f4'), ('background', '<f4')]),('fitError', [('A', '<f4'),('x0', '<f4'),('y0', '<f4'),('z0', '<f4'),('wxy', '<f4'),('wz', '<f4'), ('background', '<f4')]), ('resultCode', '<i4'), ('slicesUsed', [('x', [('start', '<i4'),('stop', '<i4'),('step', '<i4')]),('y', [('start', '<i4'),('stop', '<i4'),('step', '<i4')]),('z', [('start', '<i4'),('stop', '<i4'),('step', '<i4')])])]

def Gauss3dFitResultR(fitResults, metadata, slicesUsed=None, resultCode=-1, fitErr=None):
	if slicesUsed == None:
		slicesUsed = ((-1,-1,-1),(-1,-1,-1),(-1,-1,-1))
	else: 		
		slicesUsed = ((slicesUsed[0].start,slicesUsed[0].stop,replNoneWith1(slicesUsed[0].step)),(slicesUsed[1].start,slicesUsed[1].stop,replNoneWith1(slicesUsed[1].step)),(slicesUsed[2].start,slicesUsed[2].stop,replNoneWith1(slicesUsed[2].step)))

	if fitErr == None:
		fitErr = -5e3*numpy.ones(fitResults.shape, 'f')

	#print slicesUsed

	tIndex = metadata.tIndex


	return numpy.array([(tIndex, fitResults.astype('f'), fitErr.astype('f'), resultCode, slicesUsed)], dtype=fresultdtype) 

class Gauss3dFitFactory:
    def __init__(self, data, metadata, background=None):
        self.data = data - metadata.Camera.ADOffset
        self.metadata = metadata
        self.background = background

    def __getitem__(self, key):
        #print key
        xslice, yslice, zslice = key

        #cut region out of data stack
        dataROI = self.data[xslice, yslice, zslice]

        #generate grid to evaluate function on
        X, Y, Z = mgrid[xslice, yslice, zslice]

        X = 1e3*self.metadata.voxelsize.x*X
        Y = 1e3*self.metadata.voxelsize.y*Y
        Z = 1e3*self.metadata.voxelsize.z*Z
        

        #imshow(dataROI[:,:,0])
        #estimate some start parameters...
        A = dataROI.max() - dataROI.min() #amplitude
        x0 =  X.mean()
        y0 =  Y.mean()
        z0 =  Z.mean()

        #try fitting with start value above and below current position,
        #at the end take the one with loeset missfit
        startParameters = [3*A, x0, y0, z0, 100, 250, dataROI.min()]
        

        #print startParameters        

        #estimate errors in data
        #sigma = (4 + scipy.sqrt(2*dataROI)/2)

        #print X.shape, dataROI.shape, zslice

        sigma = scipy.sqrt(self.metadata.Camera.ReadNoise**2 + (self.metadata.Camera.NoiseFactor**2)*self.metadata.Camera.ElectronsPerCount*self.metadata.Camera.TrueEMGain*scipy.maximum(dataROI, 1))/self.metadata.Camera.ElectronsPerCount
        #do the fit
        #(res, resCode) = FitModel(f_gauss2d, startParameters, dataMean, X, Y)
        #print X
        #print Y
        #print Z

        #fit with start values above current position        
        (res1, cov_x, infodict, mesg1, resCode) = FitModelWeighted(f_Gauss3d, startParameters, dataROI, sigma, X, Y, Z)
        misfit = (infodict['fvec']**2).sum()

        
        
        
        #print res
        #print scipy.sqrt(diag(cov_x))
        #return GaussianFitResult(res, self.metadata, (xslice, yslice, zslice), resCode)

        fitErrors=None
        try:
            fitErrors = scipy.sqrt(scipy.diag(cov_x)*(infodict['fvec']*infodict['fvec']).sum()/(len(dataMean.ravel())- len(res)))
        except Exception, e:
            pass
        
        return Gauss3dFitResultR(res1, self.metadata, (xslice, yslice, zslice), resCode, fitErrors)
        

    def FromPoint(self, x, y, z=None, roiHalfSize=8, axialHalfSize=5):
        if (z == None): # use position of maximum intensity
            z = self.data[x,y,:].argmax()

        x = round(x)
        y = round(y)
        z = round(z)

        return self[max((x - roiHalfSize), 0):min((x + roiHalfSize + 1),self.data.shape[0]), 
                    max((y - roiHalfSize), 0):min((y + roiHalfSize + 1), self.data.shape[1]), 
                    max((z - axialHalfSize), 0):min((z + axialHalfSize + 1), self.data.shape[2])]
        

FitFactory = Gauss3dFitFactory
FitResult = Gauss3dFitResultR
FitResultsDType = fresultdtype #only defined if returning data as numarray
