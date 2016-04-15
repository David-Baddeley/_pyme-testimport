# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 10:45:44 2016

@author: david
"""
import numpy as np
from scipy import ndimage


def of(im1, im2, filt_rad=10, support_rad = 10):
    gf = ndimage.gaussian_filter
    
    im1_f = gf(im1, filt_rad)
    im2_f = gf(im2, filt_rad)
    imm = 0.5*(im1_f+im2_f)
    
    dIdx, dIdy = np.gradient(imm)
    
    dIdt = im2_f - im1_f
    
    M = np.concatenate([np.concatenate([gf(dIdx*dIdx, support_rad)[:,:,None], gf(dIdx*dIdy, support_rad)[:,:,None]], 2)[:,:,:,None],
                  np.concatenate([gf(dIdx*dIdy, support_rad)[:,:,None], gf(dIdy*dIdy, support_rad)[:,:,None]], 2)[:,:,:,None]], 3)
    b = - np.concatenate([gf(dIdx*dIdt, support_rad)[:,:,None], gf(dIdy*dIdt, support_rad)[:,:,None]], 2)
    
    #print M.shape
    
    MI = np.linalg.inv(M)
    
    #print MI.shape, b.shape
    
    MIb= (MI*b[:,:,:,None]).sum(3)
    
    return MIb[:,:,0], MIb[:,:,1]
    
def reg_of(im1, im2, filt_rad=10, support_rad = 10, reg_l = 0):
    '''Calculates the optical flow between im1 and im2.
    
    Images are smoothed first, using a filter of radius filt_rad. The flow is then
    calculated with a Gaussian support function of radius support_rad. An optional
    regularization term, reg_l allows penalization of high flow velocities.
    
    See "Optical Flow Estimation", Fleet and Weiss 2006 for underlying maths. Our
    implementation is based on Section 2, "Basic gradient-based estimation", and 
    attempts to find a least-squares which minimizes:
    
    $$E(\tilde{u}) = \sum_{\tilde{x}}g(\tilde{x})\left[\tilde{u} \cdot \nabla I(\tilde{x}, t) + I_t(\tilde{x}, t)\right]^2$$
    
    Note that the reglarization is not described in Fleet and Wiess, but works by
    adding an L1-norm term to the equation to be minimized, resulting in the following 
    equation:
    
    $$E(\tilde{u}) = \sum_{\tilde{x}}g(\tilde{x})\left[\tilde{u} \cdot \nabla I(\tilde{x}, t) + I_t(\tilde{x}, t)\right]^2 + \lambda \|\tilde{u}\|^2$$
    '''
    gf = ndimage.gaussian_filter
    
    im1_f = gf(im1, filt_rad)
    im2_f = gf(im2, filt_rad)
    imm = 0.5*(im1_f+im2_f)
    
    dIdx, dIdy = np.gradient(imm)
    
    dIdt = im2_f - im1_f
    
    M = np.concatenate([np.concatenate([gf(dIdx*dIdx, support_rad)[:,:,None] + reg_l, gf(dIdx*dIdy, support_rad)[:,:,None]], 2)[:,:,:,None],
                  np.concatenate([gf(dIdx*dIdy, support_rad)[:,:,None], gf(dIdy*dIdy, support_rad)[:,:,None] + reg_l], 2)[:,:,:,None]], 3)
    b = - np.concatenate([gf(dIdx*dIdt, support_rad)[:,:,None], gf(dIdy*dIdt, support_rad)[:,:,None]], 2)
    
    #print M.shape
    
    MI = np.linalg.inv(M)
    
    #print MI.shape, b.shape
    
    MIb= (MI*b[:,:,:,None]).sum(3)
    
    return MIb[:,:,0], MIb[:,:,1]