# -*- coding: utf-8 -*-
"""
Created on Mon May 25 17:15:01 2015

@author: david
"""

from .base import ModuleBase, register_module, Filter
from PYME.recipes.traits import Input, Output, Float, Enum, CStr, Bool, Int,  File

#try:
#    from traitsui.api import View, Item, Group
#except SystemExit:
#    print('Got stupid OSX SystemExit exception - using dummy traitsui')
#    from PYME.misc.mock_traitsui import *

import numpy as np
from scipy import ndimage
from PYME.IO.image import ImageStack

@register_module('SimpleThreshold') 
class SimpleThreshold(Filter):
    threshold = Float(0.5)
    
    def applyFilter(self, data, chanNum, frNum, im):
        mask = data > self.threshold
        return mask

    def completeMetadata(self, im):
        im.mdh['Processing.SimpleThreshold'] = self.threshold
        
@register_module('FractionalThreshold') 
class FractionalThreshold(Filter):
    """Chose a threshold such that the given fraction of the total labelling is
    included in the mask.
    """
    fractionThreshold = Float(0.5)

    def applyFilter(self, data, chanNum, frNum, im):
        N, bins = np.histogram(data, bins=5000)
        #calculate bin centres
        bin_mids = (bins[:-1] )
        cN = np.cumsum(N*bin_mids)
        i = np.argmin(abs(cN - cN[-1]*(1-self.fractionThreshold)))
        threshold = bins[i]

        mask = data > threshold
        return mask

    def completeMetadata(self, im):
        im.mdh['Processing.FractionalThreshold'] = self.fractionThreshold
 
@register_module('Label')        
class Label(Filter):
    """Asigns a unique integer label to each contiguous region in the input mask.
    Optionally throws away all regions which are smaller than a cutoff size.
    """
    minRegionPixels = Int(10)
    
    def applyFilter(self, data, chanNum, frNum, im):
        mask = data > 0.5
        labs, nlabs = ndimage.label(mask)
        
        rSize = self.minRegionPixels
        
        if rSize > 1:
            m2 = 0*mask
            objs = ndimage.find_objects(labs)
            for i, o in enumerate(objs):
                r = labs[o] == i+1
                #print r.shape
                if r.sum() > rSize:
                    m2[o] += r
                                
            labs, nlabs = ndimage.label(m2 > 0)
            
        return labs

    def completeMetadata(self, im):
        im.mdh['Labelling.MinSize'] = self.minRegionPixels
        
@register_module('SelectLabel') 
class SelectLabel(Filter):
    """Creates a mask corresponding to all pixels with the given label"""
    label = Int(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        mask = (data == self.label)
        return mask

    def completeMetadata(self, im):
        im.mdh['Processing.SelectedLabel'] = self.label

@register_module('LocalMaxima')         
class LocalMaxima(Filter):
    threshold = Float(.3)
    minDistance = Int(10)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.feature
        im = data.astype('f')/data.max()
        return skimage.feature.peak_local_max(im, threshold_abs = self.threshold, min_distance = self.minDistance, indices=False)

    def completeMetadata(self, im):
        im.mdh['LocalMaxima.threshold'] = self.threshold
        im.mdh['LocalMaxima.minDistance'] = self.minDistance
        
        
@register_module('OpticalFlow')         
class OpticalFlow(ModuleBase):
    filterRadius = Float(1)
    supportRadius = Float(10) 
    regularizationLambda = Float(0)
    inputName = Input('input')
    outputNameX = Output('flow_x')
    outputNameY = Output('flow_y')
    
    def calc_flow(self, data, chanNum):
        from PYME.Analysis import optic_flow
        
        flow_x = []
        flow_y = []
        
        for i in range(0, data.shape[2]):
            dx, dy = 0,0
            
            if i >=1:
                dx, dy = optic_flow.reg_of(data[:,:,i-1, chanNum].squeeze(), data[:,:,i, chanNum].squeeze(), self.filterRadius, self.supportRadius, self.regularizationLambda)
            if (i < (data.shape[2] - 1)):
                dx_, dy_ = optic_flow.reg_of(data[:,:,i, chanNum].squeeze(), data[:,:,i+1, chanNum].squeeze(), self.filterRadius, self.supportRadius, self.regularizationLambda)
                dx = dx + dx_
                dy = dy + dy_

            flow_x.append(np.atleast_3d(dx))
            flow_y.append(np.atleast_3d(dy))                
        
        
        return np.concatenate(flow_x, 2),np.concatenate(flow_y, 2) 
        
    def execute(self, namespace):
        image = namespace[self.inputName]
        flow_x = []
        flow_y = []
        for chanNum in range(image.data.shape[3]):
            fx, fy = self.calc_flow(image.data, chanNum)
            flow_x.append(fx)
            flow_y.append(fy)
        
        im = ImageStack(flow_x, titleStub = self.outputNameX)
        im.mdh.copyEntriesFrom(image.mdh)
        im.mdh['Parent'] = image.filename
        
        self.completeMetadata(im)
        namespace[self.outputNameX] = im
        
        im = ImageStack(flow_y, titleStub = self.outputNameY)
        im.mdh.copyEntriesFrom(image.mdh)
        im.mdh['Parent'] = image.filename
        
        self.completeMetadata(im)
        namespace[self.outputNameY] = im
        
    def completeMetadata(self, im):
        im.mdh['OpticalFlow.filterRadius'] = self.filterRadius
        im.mdh['OpticalFlow.supportRadius'] = self.supportRadius
        
@register_module('Gradient')         
class Gradient2D(ModuleBase):   
    inputName = Input('input')
    outputNameX = Output('grad_x')
    outputNameY = Output('grad_y')
    
    def calc_grad(self, data, chanNum):
        grad_x = []
        grad_y = []
        
        for i in range(0, data.shape[2]):
            dx, dy = np.gradient(data[:,:,i, chanNum].squeeze())
            grad_x.append(np.atleast_3d(dx))
            grad_y.append(np.atleast_3d(dy))                
        
        
        return np.concatenate(grad_x, 2),np.concatenate(grad_y, 2) 
        
    def execute(self, namespace):
        image = namespace[self.inputName]
        grad_x = []
        grad_y = []
        for chanNum in range(image.data.shape[3]):
            fx, fy = self.calc_grad(image.data, chanNum)
            grad_x.append(fx)
            grad_y.append(fy)
        
        im = ImageStack(grad_x, titleStub = self.outputNameX)
        im.mdh.copyEntriesFrom(image.mdh)
        im.mdh['Parent'] = image.filename
        
        #self.completeMetadata(im)
        namespace[self.outputNameX] = im
        
        im = ImageStack(grad_y, titleStub = self.outputNameY)
        im.mdh.copyEntriesFrom(image.mdh)
        im.mdh['Parent'] = image.filename
        
        #self.completeMetadata(im)
        namespace[self.outputNameY] = im


@register_module('Gradient3D')
class Gradient3D(ModuleBase):
    inputName = Input('input')
    outputNameX = Output('grad_x')
    outputNameY = Output('grad_y')
    outputNameZ = Output('grad_z')

    def calc_grad(self, data, chanNum):
        dx, dy, dz = np.gradient(np.atleast_3d(data[:,:,:,chanNum].squeeze()))

        return dx, dy, dz

    def execute(self, namespace):
        image = namespace[self.inputName]
        grad_x = []
        grad_y = []
        grad_z = []

        for chanNum in range(image.data.shape[3]):
            fx, fy, fz = self.calc_grad(image.data, chanNum)
            grad_x.append(fx)
            grad_y.append(fy)
            grad_z.append(fz)

        im = ImageStack(grad_x, titleStub=self.outputNameX)
        im.mdh.copyEntriesFrom(image.mdh)
        namespace[self.outputNameX] = im

        im = ImageStack(grad_y, titleStub=self.outputNameY)
        im.mdh.copyEntriesFrom(image.mdh)
        namespace[self.outputNameY] = im

        im = ImageStack(grad_z, titleStub=self.outputNameY)
        im.mdh.copyEntriesFrom(image.mdh)
        namespace[self.outputNameZ] = im

@register_module('DirectionToMask3D')
class DirectionToMask3D(ModuleBase):
    """
    Estimates the direction from a pixel to the edge of a mask.
    """
    inputName = Input('input')
    outputNameX = Output('grad_x')
    outputNameY = Output('grad_y')
    outputNameZ = Output('grad_z')

    kernelSize = Int(7)

    def calc_grad(self, data, chanNum):
        from scipy import ndimage

        data = np.atleast_3d(data[:,:,:,chanNum].squeeze())

        ks = float(self.kernelSize)
        X,Y,Z = np.mgrid[-ks:(ks+1), -ks:(ks+1), -ks:(ks+1)]
        R = np.sqrt(X*X + Y*Y + Z*Z)

        kernel_norm = 1.0/R
        kernel_norm[ks,ks,ks] = 0

        kernel_x = X/(R*R)
        kernel_x[ks, ks, ks] = 0

        kernel_y = Y / (R * R)
        kernel_y[ks, ks, ks] = 0

        kernel_z = Z / (R * R)
        kernel_z[ks, ks, ks] = 0

        norm = np.maximum(0.01, ndimage.convolve(data, kernel_norm))

        dx = ndimage.convolve(data, kernel_x)/norm
        dy = ndimage.convolve(data, kernel_y) / norm
        dz = ndimage.convolve(data, kernel_z) / norm

        norm2 = np.maximum(.01, np.sqrt(dx*dx + dy*dy + dz*dz))

        return dx/norm2, dy/norm2, dz/norm2

    def execute(self, namespace):
        image = namespace[self.inputName]
        grad_x = []
        grad_y = []
        grad_z = []

        for chanNum in range(image.data.shape[3]):
            fx, fy, fz = self.calc_grad(image.data, chanNum)
            grad_x.append(fx)
            grad_y.append(fy)
            grad_z.append(fz)

        im = ImageStack(grad_x, titleStub=self.outputNameX)
        im.mdh.copyEntriesFrom(image.mdh)
        namespace[self.outputNameX] = im

        im = ImageStack(grad_y, titleStub=self.outputNameY)
        im.mdh.copyEntriesFrom(image.mdh)
        namespace[self.outputNameY] = im

        im = ImageStack(grad_z, titleStub=self.outputNameY)
        im.mdh.copyEntriesFrom(image.mdh)
        namespace[self.outputNameZ] = im

@register_module('VectorfieldCurl')
class VectorfieldCurl(ModuleBase):
    """Calculates the curl of a vector field defined by three inputs.


    Notes
    -----

    returns
    .. math::

        (\frac{\del F_z}{\del y} - \frac{\del F_y}{\del z}, \frac{\del F_x}{\del z} - \frac{\del F_z}{\del x}, \frac{\del F_y}{\del x} - \frac{\del F_x}{\del y})$$
    """
    inputX = Input('inp_x')
    inputY = Input('inp_y')
    inputZ = Input('inp_z')

    outputX = Output('out_x')
    outputY = Output('out_y')
    outputZ = Output('out_z')


    def execute(self, namespace):
        Fx = namespace[self.inputX].data[:,:,:,0].squeeze()
        Fy = namespace[self.inputY].data[:, :, :, 0].squeeze()
        Fz = namespace[self.inputZ].data[:, :, :, 0].squeeze()

        mdh = namespace[self.inputX].mdh

        dFzdx, dFzdy, dFzdz = np.gradient(Fz)
        dFydx, dFydy, dFydz = np.gradient(Fy)
        dFxdx, dFxdy, dFxdz = np.gradient(Fx)

        im = ImageStack(dFzdy - dFydz, titleStub=self.outputX)
        im.mdh.copyEntriesFrom(mdh)
        namespace[self.outputX] = im

        im = ImageStack(dFxdz - dFzdx, titleStub=self.outputY)
        im.mdh.copyEntriesFrom(mdh)
        namespace[self.outputY] = im

        im = ImageStack(dFydx - dFzdy, titleStub=self.outputZ)
        im.mdh.copyEntriesFrom(mdh)
        namespace[self.outputZ] = im

@register_module('VectorfieldNorm')
class VectorfieldNorm(ModuleBase):
    """Calculates the norm of a vector field defined by three inputs.


    Notes
    -----

    returns
    .. math::

        sqrt(x*x + y*y + z*z)

    Also works for 2D vector fields if inputZ is an empty string.
    """
    inputX = Input('inp_x')
    inputY = Input('inp_y')
    inputZ = Input('inp_z')

    outputName = Output('output')

    def execute(self, namespace):
        x = namespace[self.inputX].data[:,:,:,0].squeeze()
        y = namespace[self.inputY].data[:, :, :, 0].squeeze()
        if self.inputZ == '':
            z = 0
        else:
            z = namespace[self.inputZ].data[:, :, :, 0].squeeze()

        mdh = namespace[self.inputX].mdh

        norm = np.sqrt(x*x + y*y + z*z)

        im = ImageStack(norm, titleStub=self.outputName)
        im.mdh.copyEntriesFrom(mdh)
        namespace[self.outputName] = im


@register_module('ProjectOnVector')         
class ProjectOnVector(ModuleBase):
    """Project onto a set of direction vectors, producing p and s components"""
    inputX = Input('inputX')
    inputY = Input('inputY')
    inputDirX = Input('dirX')
    inputDirY = Input('dirY')
    
    outputNameP = Output('proj_p')
    outputNameS = Output('proj_s')
    
    def do_proj(self, inpX, inpY, dirX, dirY):
        """project onto basis vectors"""
        norm = np.sqrt(dirX*dirX + dirY*dirY)
        dx, dy = dirX/norm, dirY/norm
        
        projX = inpX*dx + inpY*dy
        projY = -inpX*dy + inpY*dx
        
        return projX, projY      
    
    def calc_proj(self, inpX, inpY, dirX, dirY, chanNum):
        proj_p = []
        proj_s = []
        
        for i in range(0, inpX.shape[2]):
            pp, ps = self.do_proj(inpX[:,:,i, chanNum].squeeze(), inpY[:,:,i, chanNum].squeeze(),
                                  dirX[:,:,i, chanNum].squeeze(), dirY[:,:,i, chanNum].squeeze())
            proj_p.append(np.atleast_3d(pp))
            proj_s.append(np.atleast_3d(ps))                
        
        
        return np.concatenate(proj_p, 2),np.concatenate(proj_s, 2) 
        
    def execute(self, namespace):
        inpX = namespace[self.inputX]
        inpY = namespace[self.inputY]
        dirX = namespace[self.inputDirX]
        dirY = namespace[self.inputDirY]
        
        proj_p = []
        proj_s = []
        for chanNum in range(inpX.data.shape[3]):
            fx, fy = self.calc_proj(inpX.data, inpY.data, dirX.data, dirY.data, chanNum)
            proj_p.append(fx)
            proj_s.append(fy)
        
        im = ImageStack(proj_p, titleStub = self.outputNameP)
        im.mdh.copyEntriesFrom(inpX.mdh)
        im.mdh['Parent'] = inpX.filename
        
        #self.completeMetadata(im)
        namespace[self.outputNameP] = im
        
        im = ImageStack(proj_s, titleStub = self.outputNameS)
        im.mdh.copyEntriesFrom(inpX.mdh)
        im.mdh['Parent'] = inpX.filename
        
        #self.completeMetadata(im)
        namespace[self.outputNameS] = im
        

@register_module('Deconvolve')         
class Deconvolve(Filter):
    offset = Float(0)
    method = Enum('Richardson-Lucy', 'ICTM') 
    iterations = Int(10)
    psfType = Enum('file', 'bead', 'Lorentzian', 'Gaussian')
    psfFilename = CStr('') #only used for psfType == 'file'
    lorentzianFWHM = Float(50.) #only used for psfType == 'Lorentzian'
    gaussianFWHM = Float(50.) #only used for psfType == 'Lorentzian'
    beadDiameter = Float(200.) #only used for psfType == 'bead'
    regularisationLambda = Float(0.1) #Regularisation - ICTM only
    padding = Int(0) #how much to pad the image by (to reduce edge effects)
    zPadding = Int(0) # padding along the z axis
    
    _psfCache = {}
    _decCache = {}

    def default_traits_view(self):
        from traitsui.api import View, Item, Group, ListEditor
        from PYME.ui.custom_traits_editors import CBEditor

        return View(Item(name='inputName', editor=CBEditor(choices=self._namespace_keys)),
                    Item(name='outputName'),
                    Item(name='processFramesIndividually'),
                    Group(Item(name='method'),
                          Item(name='iterations'),
                          Item(name='offset'),
                          Item(name='padding'),
                          Item(name='zPadding'),
                          Item(name='regularisationLambda', visible_when='method=="ICTM"'),
                          label='Deconvolution Parameters'),
                    Group(Item(name='psfType'),
                          Item(name='psfFilename', visible_when='psfType=="file"'),
                          Item(name='lorentzianFWHM', visible_when='psfType=="Lorentzian"'),
                          Item(name='gaussianFWHM', visible_when='psfType=="Gaussian"'),
                          Item(name='beadDiameter', visible_when='psfType=="bead"'),
                          label='PSF Parameters'),
                    resizable = True,
                    buttons   = [ 'OK' ])
                

    
    def GetPSF(self, vshint):
        from PYME.IO.load_psf import load_psf
        psfKey = (self.psfType, self.psfFilename, self.lorentzianFWHM, self.gaussianFWHM, self.beadDiameter, vshint)
        
        if not psfKey in self._psfCache.keys():
            if self.psfType == 'file':
                psf, vs = load_psf(self.psfFilename)
                psf = np.atleast_3d(psf)
                
                vsa = np.array([vs.x, vs.y, vs.z])
                
                if not np.allclose(vshint, vsa, rtol=.03):
                    psf = ndimage.zoom(psf, vshint/vsa)
                
                self._psfCache[psfKey] = (psf, vs)        
            elif (self.psfType == 'Lorentzian'):
                from scipy import stats
                sc = self.lorentzianFWHM/2.0
                X, Y = np.mgrid[-30.:31., -30.:31.]
                R = np.sqrt(X*X + Y*Y)
                
                if not vshint is None:
                    vx = vshint[0]
                else:
                    vx = sc/2.
                
                vs = type('vs', (object,), dict(x=vx/1e3, y=vx/1e3))
                
                psf = np.atleast_3d(stats.cauchy.pdf(vx*R, scale=sc))
                    
                self._psfCache[psfKey] = (psf/psf.sum(), vs)
                
            elif (self.psfType == 'Gaussian'):
                from scipy import stats
                sc = self.gaussianFWHM/2.35
                X, Y = np.mgrid[-30.:31., -30.:31.]
                R = np.sqrt(X*X + Y*Y)
                
                if not vshint is None:
                    vx = vshint[0]
                else:
                    vx = sc/2.
                
                vs = type('vs', (object,), dict(x=vx/1e3, y=vx/1e3))
                
                psf = np.atleast_3d(stats.norm.pdf(vx*R, scale=sc))
                    
                self._psfCache[psfKey] = (psf/psf.sum(), vs)
            elif (self.psfType == 'bead'):
                from PYME.Deconv import beadGen
                psf = beadGen.genBeadImage(self.beadDiameter/2, vshint)
                
                vs = type('vs', (object,), dict(x=vshint[0]/1e3, y=vshint[1]/1e3))
                
                self._psfCache[psfKey] = (psf/psf.sum(), vs)
                
                
        return self._psfCache[psfKey]
        
    def GetDec(self, dp, vshint):
        """Get a (potentially cached) deconvolution object"""
        from PYME.Deconv import dec, richardsonLucy
        decKey = (self.psfType, self.psfFilename, self.lorentzianFWHM, self.beadDiameter, vshint, dp.shape, self.method)
        
        if not decKey in self._decCache.keys():
            psf = self.GetPSF(vshint)[0]
            
            #create the right deconvolution object
            if self.method == 'ICTM':
                if self.psfType == 'bead':
                    dc = dec.dec_bead()
                else:
                    dc = dec.dec_conv()
            else:
                if self.psfType == 'bead':
                    dc = richardsonLucy.rlbead()
                else:
                    dc = richardsonLucy.dec_conv()
                    
            #resize the PSF to fit, and do any required FFT planning etc ...
            dc.psf_calc(psf, dp.shape)
            
            self._decCache[decKey] = dc
            
        return self._decCache[decKey]
            
    
    def applyFilter(self, data, chanNum, frNum, im):
        d = np.atleast_3d(data.astype('f') - self.offset)
        #vx, vy, vz = np.array(im.voxelsize)*1e-3
        
        #Pad the data (if desired)
        if self.padding > 0:
            padsize = np.array([self.padding, self.padding, self.zPadding])
            dp = np.ones(np.array(d.shape) + 2*padsize, 'f')*d.mean()
            weights = np.zeros_like(dp)
            px, py, pz = padsize

            dp[px:-px, py:-py, pz:-pz] = d
            weights[px:-px, py:-py, pz:-pz] = 1.
            weights = weights.ravel()
        else: #no padding
            dp = d
            weights = 1
            
        #psf, vs = self.GetPSF(im.voxelsize)
        
        #Get appropriate deconvolution object        
        dec = self.GetDec(dp, im.voxelsize)
        
        #run deconvolution
        res = dec.deconv(dp, self.regularisationLambda, self.iterations, weights).reshape(dec.shape)
        
        #crop away the padding
        if self.padding > 0:
            res = res[px:-px, py:-py, pz:-pz]
        
        return res

    def completeMetadata(self, im):
        im.mdh['Deconvolution.Offset'] = self.offset
        im.mdh['Deconvolution.Method'] = self.method
        im.mdh['Deconvolution.Iterations'] = self.iterations
        im.mdh['Deconvolution.PsfType'] = self.psfType
        im.mdh['Deconvolution.PSFFilename'] = self.psfFilename
        im.mdh['Deconvolution.LorentzianFWHM'] = self.lorentzianFWHM
        im.mdh['Deconvolution.BeadDiameter'] = self.beadDiameter
        im.mdh['Deconvolution.RegularisationLambda'] = self.regularisationLambda
        im.mdh['Deconvolution.Padding'] = self.padding
        im.mdh['Deconvolution.ZPadding'] = self.zPadding
        

@register_module('DeconvolveMotionCompensating')
class DeconvolveMotionCompensating(Deconvolve):
    method = Enum('Richardson-Lucy')
    
    def GetDec(self, dp, vshint):
        """Get a (potentially cached) deconvolution object"""
        from PYME.Deconv import richardsonLucyMVM
        decKey = (self.psfType, self.psfFilename, self.lorentzianFWHM, self.beadDiameter, vshint, dp.shape, self.method)
        
        if not decKey in self._decCache.keys():
            psf = self.GetPSF(vshint)[0]
            
            #create the right deconvolution object
            if self.psfType == 'bead':
                dc = richardsonLucyMVM.rlbead()
            else:
                dc = richardsonLucyMVM.dec_conv()
            
            #resize the PSF to fit, and do any required FFT planning etc ...
            dc.psf_calc(psf, np.atleast_3d(dp).shape)
            
            self._decCache[decKey] = dc
        
        return self._decCache[decKey]
    
    def applyFilter(self, data, chanNum, frNum, im):
        from PYME.Analysis import optic_flow
        d = np.atleast_3d(data.astype('f') - self.offset)
    
        #Pad the data (if desired)
        if False: #self.padding > 0:
            padsize = np.array([self.padding, self.padding, self.zPadding])
            dp = np.ones(np.array(d.shape) + 2 * padsize, 'f') * d.mean()
            weights = np.zeros_like(dp)
            px, py, pz = padsize
        
            dp[px:-px, py:-py, pz:-pz] = d
            weights[px:-px, py:-py, pz:-pz] = 1.
            weights = weights.ravel()
        else: #no padding
            #dp = d
            weights = 1
    
        #Get appropriate deconvolution object
        rmv = self.GetDec(d, im.voxelsize)

        mFr = min(frNum + 2, im.data.shape[2] -1)
        if frNum < mFr:
            dx, dy = optic_flow.reg_of(im.data[:,:,frNum,chanNum].squeeze(), im.data[:,:,mFr, chanNum].squeeze(), 5, 10, 1)
        else:
            dx, dy = 0,0
    
        #run deconvolution
        mFr = min(frNum + 5, im.data.shape[2])
        res = rmv.deconv(np.atleast_3d(im.data[:,:,frNum:mFr, chanNum].astype('f').squeeze()) ,
                         0, 20, bg=0, vx = -dx*4000., vy = -dy*4000).squeeze().reshape(d.shape)
    
        #crop away the padding
        if self.padding > 0:
            res = res[px:-px, py:-py, pz:-pz]
    
        return res
        
        

    
@register_module('DistanceTransform')     
class DistanceTransform(Filter):    
    def applyFilter(self, data, chanNum, frNum, im):
        mask = 1.0*(data > 0.5)
        voxelsize = np.array(im.voxelsize)[:mask.ndim]
        dt = -ndimage.distance_transform_edt(data, sampling=voxelsize)
        dt = dt + ndimage.distance_transform_edt(1 - ndimage.binary_dilation(mask), sampling=voxelsize)
        return dt

@register_module('BinaryDilation')      
class BinaryDilation(Filter):
    iterations = Int(1)
    radius = Float(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.morphology
        
        if len(data.shape) == 3: #3D
            selem = skimage.morphology.ball(self.radius)
        else:
            selem = skimage.morphology.disk(self.radius)
        return ndimage.binary_dilation(data, selem)

@register_module('BinaryErosion')         
class BinaryErosion(Filter):
    iterations = Int(1)
    radius = Float(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.morphology
        
        if len(data.shape) == 3: #3D
            selem = skimage.morphology.ball(self.radius)
        else:
            selem = skimage.morphology.disk(self.radius)
        return ndimage.binary_erosion(data, selem)

@register_module('BinaryFillHoles')         
class BinaryFillHoles(Filter):
    iterations = Int(1)
    radius = Float(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.morphology
        
        if len(data.shape) == 3: #3D
            selem = skimage.morphology.ball(self.radius)
        else:
            selem = skimage.morphology.disk(self.radius)
        return ndimage.binary_fill_holes(data, selem)
        
@register_module('GreyDilation')      
class GreyDilation(Filter):
    iterations = Int(1)
    radius = Float(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.morphology
        
        if len(data.shape) == 3: #3D
            selem = skimage.morphology.ball(self.radius)
        else:
            selem = skimage.morphology.disk(self.radius)
        return ndimage.grey_dilation(data, structure=selem)

@register_module('GreyErosion')         
class GreyErosion(Filter):
    iterations = Int(1)
    radius = Float(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.morphology
        
        if len(data.shape) == 3: #3D
            selem = skimage.morphology.ball(self.radius)
        else:
            selem = skimage.morphology.disk(self.radius)
        return ndimage.grey_erosion(data, structure=selem)
        
@register_module('WhiteTophat')         
class WhiteTophat(Filter):
    iterations = Int(1)
    radius = Float(1)
    
    def applyFilter(self, data, chanNum, frNum, im):
        import skimage.morphology
        
        if len(data.shape) == 3: #3D
            selem = skimage.morphology.ball(self.radius)
        else:
            selem = skimage.morphology.disk(self.radius)
        return ndimage.white_tophat(data, structure=selem)


@register_module('Watershed')         
class Watershed(ModuleBase):
    """Module with one image input and one image output"""
    inputImage = Input('input')
    inputMarkers = Input('markers')
    inputMask = Input('')
    outputName = Output('watershed')
    
    processFramesIndividually = Bool(False)
    
    def filter(self, image, markers, mask=None):
        if self.processFramesIndividually:
            filt_ims = []
            for chanNum in range(image.data.shape[3]):
                if not mask is None:
                    filt_ims.append(np.concatenate([np.atleast_3d(self.applyFilter(image.data[:,:,i,chanNum].squeeze(), markers.data[:,:,i,chanNum].squeeze(), mask.data[:,:,i,chanNum].squeeze())) for i in range(image.data.shape[2])], 2))
                else:
                    filt_ims.append(np.concatenate([np.atleast_3d(self.applyFilter(image.data[:,:,i,chanNum].squeeze(), markers.data[:,:,i,chanNum].squeeze())) for i in range(image.data.shape[2])], 2))
        else:
            if not mask is None:
                filt_ims = [np.atleast_3d(self.applyFilter(image.data[:,:,:,chanNum].squeeze(), markers.data[:,:,:,chanNum].squeeze(), mask.data[:,:,:,chanNum].squeeze())) for chanNum in range(image.data.shape[3])]
            else:
                filt_ims = [np.atleast_3d(self.applyFilter(image.data[:,:,:,chanNum].squeeze(), mask.data[:,:,:,chanNum].squeeze())) for chanNum in range(image.data.shape[3])]
            
        im = ImageStack(filt_ims, titleStub = self.outputName)
        im.mdh.copyEntriesFrom(image.mdh)
        im.mdh['Parent'] = image.filename
        
        #self.completeMetadata(im)
        
        return im
        
    def applyFilter(self, image,markers, mask=None):
        import skimage.morphology

        img = ((image/image.max())*2**15).astype('int16')         
        
        if not mask is None:
            return skimage.morphology.watershed(img, markers.astype('int16'), mask = mask.astype('int16'))
        else:
            return skimage.morphology.watershed(img, markers.astype('int16'))
        
    def execute(self, namespace):
        image = namespace[self.inputImage]
        markers =  namespace[self.inputMarkers]
        if self.inputMask in ['', 'none', 'None']:
            namespace[self.outputName] = self.filter(image, markers)
        else:
            mask = namespace[self.inputMask]
            namespace[self.outputName] = self.filter(image, markers, mask)




        
