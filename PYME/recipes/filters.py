# -*- coding: utf-8 -*-
"""
Created on Fri Feb 20 17:11:05 2015

@author: david
"""
from .base import register_module, ModuleBase, Filter
from .traits import Input, Output, Float, Enum, CStr, Bool, Int
from scipy import ndimage
#from PYME.IO.image import ImageStack
import numpy as np

@register_module('GaussianFilter')    
class GaussianFilter(Filter):
    """
    Performs a Gaussian filter of the input image

    Parameters
    ----------

    sigmaX : std. deviation of filter kernel along x axis in pixels

    sigmaY : std. deviation of filter kernel along y axis in pixels

    sigmaZ : std. deviation of filter kernel along z  axisin pixels

    Notes
    -----

    * implemented as a call to `scipy.ndimage.gaussian_filter`
    * sigmaZ is ignored and a 2D filtering performed if ``processFramesIndividually`` is selected
    """
    sigmaY = Float(1.0)
    sigmaX = Float(1.0)
    sigmaZ = Float(1.0)
    #def __init__(self, **kwargs):
    #    pass
    @property
    def sigmas(self):
        return [self.sigmaX, self.sigmaY, self.sigmaZ]
    
    def applyFilter(self, data, chanNum, frNum, im):
        return ndimage.gaussian_filter(data, self.sigmas[:len(data.shape)])
    
    def completeMetadata(self, im):
        im.mdh['Processing.GaussianFilter'] = self.sigmas

@register_module('MedianFilter')         
class MedianFilter(Filter):
    """
    Performs a median filter of the input image

    Parameters
    ----------

    sizeX : size of filter kernel along x axis in pixels

    sizeY : size of filter kernel along y axis in pixels

    sizeZ : size of filter kernel along z  axisin pixels

    Notes
    -----

    * implemented as a call to `scipy.ndimage.median_filter`
    * sizeZ is ignored and a 2D filtering performed if ``processFramesIndividually`` is selected
    """
    sizeX = Float(1.0)
    sizeY = Float(1.0)
    sizeZ = Float(1.0)
    #def __init__(self, **kwargs):
    #    pass
    @property
    def sigmas(self):
        return [self.sizeX, self.sizeY, self.sizeZ]
    
    def applyFilter(self, data, chanNum, frNum, im):
        return ndimage.median_filter(data, self.sigmas[:len(data.shape)])
    
    def completeMetadata(self, im):
        im.mdh['Processing.MedianFilter'] = self.sigmas
        
@register_module('DespeckleFilter')         
class DespeckleFilter(Filter):
    """
    Attempts to remove speckle from an image.

    The despeckle filter functions by replacing a value of each pixel with the median of the *nPix* pixels within
    the filter support which are closest in intensity to the value of the pixel itself.

    Parameters
    ----------

    sizeX : size of filter kernel along x axis in pixels

    sizeY : size of filter kernel along y axis in pixels

    sizeZ : size of filter kernel along z  axis in pixels

    nPix : number of pixels to use for the median

    Notes
    -----

    * The design intent is an edge-preserving filter for images which have a lot of shot noise (e.g. STED images)
    * It is highly non-linear, and thus best suited for either treating images for display, or potentially segmentation.
      It should **NOT** be used if intensities need to be quantified or prior to operations such as deconvolution.
    * sizeZ is ignored and a 2D filtering performed if ``processFramesIndividually`` is selected
    """
    sizeX = Int(3)
    sizeY = Int(3)
    sizeZ = Int(3)
    nPix = Int(3)
    
    def _filt(self, data):
        v = data[data.size/2]
        
        dv = np.abs(data - v)
        
        I = np.argsort(dv)
        return np.median(data[I[:self.nPix]])
        
    #def __init__(self, **kwargs):
    #    pass
    @property
    def sigmas(self):
        return [self.sizeX, self.sizeY, self.sizeZ]
    
    def applyFilter(self, data, chanNum, frNum, im):
        return ndimage.generic_filter(data, self._filt, self.sigmas[:len(data.shape)])
    
    def completeMetadata(self, im):
        im.mdh['Processing.DespeckleFilter'] = self.sigmas

@register_module('MeanFilter') 
class MeanFilter(Filter):
    """
    Performs a mean / uniform filter of the input image

    Parameters
    ----------

    sizeX : size of filter kernel along x axis in pixels

    sizeY : size of filter kernel along y axis in pixels

    sizeZ : size of filter kernel along z  axis in pixels

    Notes
    -----

    * implemented as a call to `scipy.ndimage.mean_filter`
    * sizeZ is ignored and a 2D filtering performed if ``processFramesIndividually`` is selected
    """
    sizeX = Float(1.0)
    sizeY = Float(1.0)
    sizeZ = Float(1.0)
    #def __init__(self, **kwargs):
    #    pass
    @property
    def sigmas(self):
        return [self.sizeX, self.sizeY, self.sizeZ]
    
    def applyFilter(self, data, chanNum, frNum, im):
        return ndimage.mean_filter(data, self.sigmas[:len(data.shape)])
    
    def completeMetadata(self, im):
        im.mdh['Processing.MeanFilter'] = self.sigmas

@register_module('Zoom')         
class Zoom(Filter):
    """
    Zoom / resize an image using ``ndimage.zoom``

    Parameters
    ----------

    zoom : factor by which to zoom the image

    Notes
    -----
    * zoom is isotropic in 3D if ``processFramesIndividually`` is ``False``
    * zoom only zooms in x and y if ``processFramesIndividually`` is ``True``

    """
    zoom = Float(1.0)
    
    def applyFilter(self, data, chanNum, frNum, im):
        return ndimage.zoom(data, self.zoom)
    
    def completeMetadata(self, im):
        im.mdh['Processing.Zoom'] = self.zoom
        im.mdh['voxelsize.x'] = im.mdh['voxelsize.x']/self.zoom
        im.mdh['voxelsize.y'] = im.mdh['voxelsize.y']/self.zoom
        
        if not self.processFramesIndividually:
            im.mdh['voxelsize.z'] = im.mdh['voxelsize.z']/self.zoom

@register_module('MaskEdges')
class MaskEdges(Filter):
    """
    Sets the edge pixels of an image to zero.

    Used to prevent objects near the edge of an image from being detected if they might not be processed properly in
    subsequent object measurement or fitting routines.

    Parameters
    ----------

    widthPxels : the distance from the edge to mask with 0s
    """
    widthPixels = Int(10)

    def applyFilter(self, data, chanNum, frNum, im):
        dm = data.copy()
        dm[:self.widthPixels, :] = 0
        dm[-self.widthPixels:, :] = 0
        dm[:, :self.widthPixels] = 0
        dm[:, -self.widthPixels:] = 0
        return dm
            
@register_module('DoGFilter')         
class DoGFilter(Filter):
    """Difference of Gaussians

    Blurs the image with 2 different sized Gaussians and subtracts them. Commonly used to detect points or blobs. The
    smaller Gaussian should be set to match the desired blob size and acts as a noise reduction filter, wheras the
    larger Gaussian (which is subtracted) can be thought of as a form of local background estimation.

    Parameters
    ----------

    sigmaX, sigmaY, sigmaZ : std. deviation of the smaller Gaussian.

    sigmaX2, sigmaY2, sigmaZ2 : std. deviations of the larger Gaussian

    Notes
    -----

    * implemented as 2 calls to `scipy.ndimage.gaussian_filter`
    * sigmaZ and sigmaZ2 are ignored and a 2D filtering performed if ``processFramesIndividually`` is selected

    """
    sigmaY = Float(1.0)
    sigmaX = Float(1.0)
    sigmaZ = Float(1.0)
    
    sigma2Y = Float(1.0)
    sigma2X = Float(1.0)
    sigma2Z = Float(1.0)

    #def __init__(self, **kwargs):
    #    pass
    @property
    def sigmas(self):
        return [self.sigmaX, self.sigmaY, self.sigmaZ]
        
    @property
    def sigma2s(self):
        return [self.sigma2X, self.sigma2Y, self.sigma2Z]
    
    def applyFilter(self, data, chanNum, frNum, im):
        return ndimage.gaussian_filter(data, self.sigmas[:len(data.shape)]) - ndimage.gaussian_filter(data, self.sigma2s[:len(data.shape)])
    
    def completeMetadata(self, im):
        im.mdh['Processing.GaussianFilter'] = self.sigmas



 
#d = {}
#d.update(locals())
#moduleList = [c for c in d if _issubclass(c, ModuleBase) and not c == ModuleBase]       
