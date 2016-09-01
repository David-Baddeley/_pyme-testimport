#!/usr/bin/python
##################
# richardsonLucy.py
#
# Copyright David Baddeley, 2011
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
from scipy import *
from scipy.linalg import *
#from scipy.fftpack import fftn, ifftn, fftshift, ifftshift
from scipy import ndimage
import numpy
from scipy.fftpack import fftn, ifftn, fftshift, ifftshift
import fftw3f
import fftwWisdom
import numpy as np
import pylab as pl

from wiener import resizePSF

fftwWisdom.load_wisdom()
#import weave
#import cDec
#from PYME import pad
#import dec

NTHREADS = 8
FFTWFLAGS = ['measure']

class rldec:
    """Deconvolution class, implementing a variant of the Richardson-Lucy algorithm.

    Derived classed should additionally define the following methods:
    AFunc - the forward mapping (computes Af)
    AHFunc - conjugate transpose of forward mapping (computes \bar{A}^T f)
    LFunc - the likelihood function
    LHFunc - conj. transpose of likelihood function

    see dec_conv for an implementation of conventional image deconvolution with a
    measured, spatially invariant PSF
    """
    def __init__(self):
       pass

    def startGuess(self, data):
        """starting guess for deconvolution - can be overridden in derived classes
        but the data itself is usually a pretty good guess.
        """
        return 0*data + data.mean()


    def deconvp(self, args):
        """ convenience function for deconvolving in parallel using processing.Pool.map"""
        return self.deconv(*args)
        #return 0
    
    def pd(self, g, velx, vely, tvals):
        g_ = g.reshape(self.dataShape[0], self.dataShape[1], -1)
        velx_ = velx.reshape(self.dataShape)
        vely_ = vely.reshape(self.dataShape)
        #print self.xv.shape, velx_.shape, tvals.shape

        #xv = np.arange(len(g))
        x_new = self.xv[:,:,None] + velx_[:, :, None] * tvals[None, None, :]
        y_new = self.yv[:,:,None] + vely_[:, :, None] * tvals[None, None, :]
        #coords = np.array([(self.xv[:, None] + shifts).T])
        coords = np.concatenate([x_new[None, :,:,:], y_new[None, :,:,:], 0*y_new[None, :,:,:]], 0)
        #print coords.shape, g_.shape, coords.T.shape
        return ndimage.map_coordinates(g_, coords, mode='wrap').ravel()
        
    def dlHd(self,data, g, velx, tvals):
        pred = self.pd(g, velx, tvals)
        
        ddx = np.array([np.gradient(r) for r in pred])
        
        #imshow(ddx)
        #imshow(data/(pred + .01))
        #imshow((data/(pred + .01) - 1)*(tvals[:, None]*ddx))
        
        return ((data/(pred + .01) - 1)*tvals[:, None]*ddx).sum(0)
        
    def dlHd2(self,data, g, velx, tvals):
        pred = self.pd(g, velx, tvals)
        
        ddx = np.array([np.gradient(r) for r in pred])
        
        #imshow(ddx)
        #imshow(data/(pred + .01))
        #imshow((data/(pred + .01) - 1)*(tvals[:, None]*ddx))
        
        return ((data/(pred + .01) - 1)*ddx).sum(0)
    
    def updateVX(self, data, g, velx, tvals, beta = -.9, nIterates = 1):
        for i in range(nIterates):
            lh0 = ndimage.gaussian_filter(self.dlHd2(data, g, velx, tvals), 50)
            lh1 = ndimage.gaussian_filter(self.dlHd2(data, g, velx + .1, tvals), 50)
            
            upd = beta*.1*lh0/(lh1-lh0 + .001)
            
            #pl.plot(lh1 - lh0)
            #plot(lh1)
            #pl.plot(upd)
            velx[:] = ndimage.gaussian_filter(velx + upd, 50)
    
    def deconv(self, views, lamb, num_iters=10, weights = 1, bg = 0, vx = 0, vy=0):
        """This is what you actually call to do the deconvolution.
        parameters are:

        data - the raw data
        lamb - the regularisation parameter
        num_iters - number of iterations (note that the convergence is fast when
                    compared to many algorithms - e.g Richardson-Lucy - and the
                    default of 10 will usually already give a reasonable result)

        alpha - PSF phase - hacked in for variable phase 4Pi deconvolution, should
                really be refactored out into the dec_4pi classes.
        """
        #remember what shape we are
        self.dataShape = views[0].shape
        
        #print 'dc1'

        #guess a starting estimate for the object
        self.f = self.startGuess(np.mean(views, axis=0)).ravel() - bg
        self.fs = self.f.reshape(self.shape)
        #print 'dc2'

        #make things 1 dimensional
        #self.f = self.f.ravel()
        views = [d.ravel() for d in views]
        self.views = views
        #data = data.ravel()
        #weights = weights.ravel()
        #print 'dc3'

        if not np.shape(vx) == self.dataShape:
            self.vx = vx*np.ones_like(views[0]) #- 1.0#1.0
            self.vy = vy*np.ones_like(views[0])
        else:
            self.vx = vx #.ravel()
            self.vy = vy #.ravel()

        self.xv, self.yv = np.mgrid[0.:self.dataShape[0], 0.:self.dataShape[1]]
        #self.xv, self.yv = xv.ravel(), yv.ravel()

        mask = 1 - weights
        
        #print data.sum(), self.f.sum()

        self.loopcount=0
        
        self.tVals = arange(len(views))

        while self.loopcount  < num_iters:
            self.loopcount += 1
            adjF = 0#1.0
            #adjF = 1.0
            for j in range(len(views)):

                #the residuals
                vj = views[j]
                #vj = vj/vj.sum()
                pred =  self.Afunc(self.f)
                pred = self.pd(pred, self.vx, self.vy, self.tVals[j:j+1]).squeeze()
                #pl.plot(pred)
                #pred = pred/pred.sum()
                self.res = weights*(vj/(pred +1e-1 + 0+ bg)) +  mask;
                
                #adjF *= self.res
                #print vj.sum(), pred.sum()
    
                #adjustment
                adjFact = self.Ahfunc(self.res)
                adjFact = self.pd(adjFact, -self.vx, -self.vy, self.tVals[j:j+1]).squeeze()
                
                #adjF += adjFact
                adjF += adjFact
                #adjF = adjF*(.2 + .8*adjFact)
                #pl.figure()
                #pl.plot(self.res)
                #pl.plot(pred)
                #pl.plot(adjFact)
                
                #pl.figure()
                #pl.plot(adjF)
                #fnew = self.f*adjFact
                #fnew = fnew*self.f.sum()/fnew.sum()
    
            #fnew = self.f*adjF**(1./len(views))
            fnew = self.f*adjF*(1./len(views))
        
            fnew = fnew*self.f.sum()/fnew.sum()


           #set the current estimate to out new estimate
            self.f[:] = fnew
            
            #self.vx[:] = 0
            #self.updateVX(np.vstack(views), self.f, self.vx, self.tVals)
            #pl.subplot(311)
            #pl.plot(self.vx)
            #pl.subplot(312)    
            #pl.plot(fnew)
                #print(('Sum = %f' % self.f.sum()))
            
        #print 'dc3'

        return real(self.fs)

#class rlbead(rl):
class rlbead(rldec):
    """Classical deconvolution using non-fft convolution - pot. faster for
    v. small psfs. Note that PSF must be symetric"""
    def psf_calc(self, psf, data_size):
        g = psf#/psf.sum();

        #keep track of our data shape
        self.height = data_size[0]
        self.width  = data_size[1]
        self.depth  = data_size[2]

        self.shape = data_size

        self.g = g;
        
        self.g2 = ndimage.convolve(g, g)

        #calculate OTF and conjugate transformed OTF
        #self.H = (fftn(g));
        #self.Ht = g.size*(ifftn(g));

    def Afunc(self, f):
        """Forward transform - convolve with the PSF"""
        fs = reshape(f, (self.height, self.width, self.depth))

        d = ndimage.convolve(fs, self.g)

        #d = real(d);
        return ravel(d)

    def Ahfunc(self, f):
        """Conjugate transform - convolve with conj. PSF"""
        fs = reshape(f, (self.height, self.width, self.depth))

        d = ndimage.correlate(fs, self.g)

        return ravel(d)

class dec_conv_slow(rldec):
    """Classical deconvolution with a stationary PSF"""
    def psf_calc(self, psf, data_size):
        """Precalculate the OTF etc..."""
#        pw = (numpy.array(data_size) - psf.shape)/2.
#        pw1 = numpy.floor(pw)
#        pw2 = numpy.ceil(pw)
#
#        g = psf/psf.sum()
#
#        #work out how we're going to need to pad to get the PSF the same size as our data
#        if pw1[0] < 0:
#            if pw2[0] < 0:
#                g = g[-pw1[0]:pw2[0]]
#            else:
#                g = g[-pw1[0]:]
#
#            pw1[0] = 0
#            pw2[0] = 0
#
#        if pw1[1] < 0:
#            if pw2[1] < 0:
#                g = g[-pw1[1]:pw2[1]]
#            else:
#                g = g[-pw1[1]:]
#
#            pw1[1] = 0
#            pw2[1] = 0
#
#        if pw1[2] < 0:
#            if pw2[2] < 0:
#                g = g[-pw1[2]:pw2[2]]
#            else:
#                g = g[-pw1[2]:]
#
#            pw1[2] = 0
#            pw2[2] = 0
#
#
#        #do the padding
#        #g = pad.with_constant(g, ((pw2[0], pw1[0]), (pw2[1], pw1[1]),(pw2[2], pw1[2])), (0,))
#        g_ = fftw3f.create_aligned_array(data_size, 'float32')
#        g_[:] = 0
#        #print g.shape, g_.shape, g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:-pw1[2]].shape
#        if pw1[2] == 0:
#            g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:] = g
#        else:
#            g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:-pw1[2]] = g
#        #g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:-pw1[2]] = g
#        g = g_

        g = resizePSF(psf, data_size)


        #keep track of our data shape
        self.height = data_size[0]
        self.width  = data_size[1]
        self.depth  = data_size[2]

        self.shape = data_size

        self.g = g;

        #calculate OTF and conjugate transformed OTF
        self.H = (fftn(g));
        self.Ht = g.size*(ifftn(g));


    def Lfunc(self, f):
        """convolve with an approximate 2nd derivative likelihood operator in 3D.
        i.e. [[[0,0,0][0,1,0][0,0,0]],[[0,1,0][1,-6,1][0,1,0]],[[0,0,0][0,1,0][0,0,0]]]
        """
        #make our data 3D again
        fs = reshape(f, (self.height, self.width, self.depth))
        a = -6*fs

        a[:,:,0:-1] += fs[:,:,1:]
        a[:,:,1:] += fs[:,:,0:-1]

        a[:,0:-1,:] += fs[:,1:,:]
        a[:,1:,:] += fs[:,0:-1,:]

        a[0:-1,:,:] += fs[1:,:,:]
        a[1:,:,:] += fs[0:-1,:,:]

        #flatten data again
        return ravel(cast['f'](a))

    Lhfunc=Lfunc

    def Afunc(self, f):
        """Forward transform - convolve with the PSF"""
        fs = reshape(f, (self.height, self.width, self.depth))

        F = fftn(fs)

        d = ifftshift(ifftn(F*self.H));

        d = real(d);
        return ravel(d)

    def Ahfunc(self, f):
        """Conjugate transform - convolve with conj. PSF"""
        fs = reshape(f, (self.height, self.width, self.depth))

        F = fftn(fs)
        d = ifftshift(ifftn(F*self.Ht));
        d = real(d);
        return ravel(d)

class dec_conv(rldec):
    """Classical deconvolution with a stationary PSF"""
    def psf_calc(self, psf, data_size):
        """Precalculate the OTF etc..."""
#        pw = (numpy.array(data_size) - psf.shape)/2.
#        pw1 = numpy.floor(pw)
#        pw2 = numpy.ceil(pw)
#
#        g = psf/psf.sum()
#
#        #work out how we're going to need to pad to get the PSF the same size as our data
#        if pw1[0] < 0:
#            if pw2[0] < 0:
#                g = g[-pw1[0]:pw2[0]]
#            else:
#                g = g[-pw1[0]:]
#
#            pw1[0] = 0
#            pw2[0] = 0
#
#        if pw1[1] < 0:
#            if pw2[1] < 0:
#                g = g[-pw1[1]:pw2[1]]
#            else:
#                g = g[-pw1[1]:]
#
#            pw1[1] = 0
#            pw2[1] = 0
#
#        if pw1[2] < 0:
#            if pw2[2] < 0:
#                g = g[-pw1[2]:pw2[2]]
#            else:
#                g = g[-pw1[2]:]
#
#            pw1[2] = 0
#            pw2[2] = 0
#
#
#        #do the padding
#        #g = pad.with_constant(g, ((pw2[0], pw1[0]), (pw2[1], pw1[1]),(pw2[2], pw1[2])), (0,))
#        g_ = fftw3f.create_aligned_array(data_size, 'float32')
#        g_[:] = 0
#        #print g.shape, g_.shape, g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:-pw1[2]].shape
#        if pw1[2] == 0:
#            g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:] = g
#        else:
#            g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:-pw1[2]] = g
#        #g_[pw2[0]:-pw1[0], pw2[1]:-pw1[1], pw2[2]:-pw1[2]] = g
#        g = g_
        
        
        print psf.sum()
        
        g = resizePSF(psf, data_size)
        print g.sum()


        #keep track of our data shape
        self.height = data_size[0]
        self.width  = data_size[1]
        self.depth  = data_size[2]

        self.shape = data_size
        
        print('Calculating OTF') 

        FTshape = [self.shape[0], self.shape[1], self.shape[2]/2 + 1]

        self.g = g.astype('f4');
        self.g2 = 1.0*self.g[::-1, ::-1, ::-1]

        #allocate memory
        self.H = fftw3f.create_aligned_array(FTshape, 'complex64')
        self.Ht = fftw3f.create_aligned_array(FTshape, 'complex64')
        #self.f = zeros(self.shape, 'f4')
        #self.res = zeros(self.shape, 'f4')
        #self.S = zeros((size(self.f), 3), 'f4')

        self._F = fftw3f.create_aligned_array(FTshape, 'complex64')
        self._r = fftw3f.create_aligned_array(self.shape, 'f4')
        #S0 = self.S[:,0]

        #create plans & calculate OTF and conjugate transformed OTF
        fftw3f.Plan(self.g, self.H, 'forward')()
        fftw3f.Plan(self.g2, self.Ht, 'forward')()

        self.Ht /= g.size;
        self.H /= g.size;
        
        print('Creating plans for FFTs - this might take a while')

        #calculate plans for other ffts
        self._plan_r_F = fftw3f.Plan(self._r, self._F, 'forward', flags = FFTWFLAGS, nthreads=NTHREADS)
        self._plan_F_r = fftw3f.Plan(self._F, self._r, 'backward', flags = FFTWFLAGS, nthreads=NTHREADS)
        
        fftwWisdom.save_wisdom()
        
        print('Done planning')


    def Lfunc(self, f):
        """convolve with an approximate 2nd derivative likelihood operator in 3D.
        i.e. [[[0,0,0][0,1,0][0,0,0]],[[0,1,0][1,-6,1][0,1,0]],[[0,0,0][0,1,0][0,0,0]]]
        """
        #make our data 3D again
        fs = reshape(f, (self.height, self.width, self.depth))
        a = -6*fs

        a[:,:,0:-1] += fs[:,:,1:]
        a[:,:,1:] += fs[:,:,0:-1]

        a[:,0:-1,:] += fs[:,1:,:]
        a[:,1:,:] += fs[:,0:-1,:]

        a[0:-1,:,:] += fs[1:,:,:]
        a[1:,:,:] += fs[0:-1,:,:]

        #flatten data again
        return ravel(cast['f'](a))

    Lhfunc=Lfunc

    def Afunc(self, f):
        """Forward transform - convolve with the PSF"""
        #fs = reshape(f, (self.height, self.width, self.depth))
        self._r[:] = f.reshape(self._r.shape)

        #F = fftn(fs)

        #d = ifftshift(ifftn(F*self.H));
        self._plan_r_F()
        self._F *= self.H
        self._plan_F_r()

        #d = real(d);
        return ravel(ifftshift(self._r))

    def Ahfunc(self, f):
        """Conjugate transform - convolve with conj. PSF"""
#        fs = reshape(f, (self.height, self.width, self.depth))
#
#        F = fftn(fs)
#        d = ifftshift(ifftn(F*self.Ht));
#        d = real(d);
#        return ravel(d)
        self._r[:] = f.reshape(self._r.shape)

        self._plan_r_F()
        self._F *= self.Ht
        self._plan_F_r()

        return ravel(ifftshift(self._r))
