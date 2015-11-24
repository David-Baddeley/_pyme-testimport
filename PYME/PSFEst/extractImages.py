#!/usr/bin/python

##################
# extractImages.py
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

from numpy import *
from numpy.fft import *
import numpy
from PYME.Analysis.LMVis import inpFilt
import scipy.ndimage


def getPSFSlice(datasource, resultsSource, metadata, zm=None):
    f1 = inpFilt.resultsFilter(resultsSource, error_x=[1,30], A=[10, 500], sig=(150/2.35, 900/2.35))

    ims, pts, zvals, zis = extractIms(datasource, f1, metadata, zm)
    return getPSF(ims, pts, zvals, zis)

#def getPointPoss(dataSource, zm, zmid):
#    for i in range()

def extractIms(dataSource, results, metadata, zm =None, roiSize=10, nmax = 1000):
    ims = zeros((2*roiSize, 2*roiSize, len(results['x'])))
    points = (array([results['x']/(metadata.voxelsize.x *1e3), results['y']/(metadata.voxelsize.y *1e3), results['A']]).T)

    pts = numpy.round(points[:,:2])
    points[:,:2] = points[:,:2] - pts
    ts = results['tIndex']
    bs = results['fitResults_background']

    ind = (pts[:,0] > roiSize)*(pts[:,1] > roiSize)*(pts[:,0] < (dataSource.shape[0] - roiSize))*(pts[:,1] < (dataSource.shape[1] - roiSize))

    #print ind.sum()

    points = points[ind,:]
    pts = pts[ind,:]
    ts = ts[ind]
    bs = bs[ind]

    if not zm == None:
        zvals = array(list(set(zm.yvals)))
        zvals.sort()

        zv = zm(ts.astype('f'))
        #print zvals
        #print zv

        zis = array([numpy.argmin(numpy.abs(zvals - z)) for z in zv])
        #print zis
    else:
        zvals = array([0])
        zis = 0.*ts

    for i in range(len(ts)):
        x = pts[i,0]
        y = pts[i,1]

        t = ts[i]
        #print t

        ims[:,:,i] = dataSource[(x-roiSize):(x+roiSize), (y-roiSize):(y+roiSize), t].squeeze() - bs[i]

    return ims - metadata.Camera.ADOffset, points, zvals, zis


def getPSF(ims, points, zvals, zis):
    height, width = ims.shape[0],ims.shape[1]
    kx,ky = mgrid[:height,:width]#,:self.sliceShape[2]]

    kx = fftshift(kx - height/2.)/height
    ky = fftshift(ky - width/2.)/width
    

    d = zeros((height, width, len(zvals)))
    print((d.shape))

    for i in range(len(points)):
        F = fftn(ims[:,:,i])
        p = points[i,:]
        #print zis[i]
        #print ifftn(F*exp(-2j*pi*(kx*-p[0] + ky*-p[1]))).real.shape
        d[:,:,zis[i]] = d[:,:,zis[i]] + ifftn(F*exp(-2j*pi*(kx*-p[0] + ky*-p[1]))).real

    d = len(zvals)*d/(points[:,2].sum())
    
    #estimate background as a function of z by averaging rim pixels
    bg = (d[0,:,:].squeeze().mean(0) + d[-1,:,:].squeeze().mean(0) + d[:,0,:].squeeze().mean(0) + d[:,-1,:].squeeze().mean(0))/4
    d = d - bg[None,None,:]
    d = d/d.sum(1).sum(0)[None,None,:]

    return d

def getIntCenter(im):
    X, Y, Z = ogrid[0:im.shape[0], 0:im.shape[1], 0:im.shape[2]]

    #from pylab import *
    #imshow(im.max(2))

    X = X.astype('f') - X.mean()
    Y = Y.astype('f') - Y.mean()
    Z = Z.astype('f')

    im2 = im - im.min()
    im2 = im2 - 0.1*im2.max()
    im2 = im2*(im2 > 0)

    ims = im2.sum()

    x = (im2*X).sum()/ims
    y = (im2*Y).sum()/ims
    z = (im2*Z).sum()/ims

    #print x, y, z

    return x, y, z


def getPSF3D(im, points, PSshape = [30,30,30], blur=[.5, .5, 1]):
    sx, sy, sz = PSshape
    height, width, depth = 2*array(PSshape) + 1
    kx,ky,kz = mgrid[:height,:width,:depth]#,:self.sliceShape[2]]

    kx = fftshift(kx - height/2.)/height
    ky = fftshift(ky - width/2.)/width
    kz = fftshift(kz - depth/2.)/depth


    d = zeros((height, width, depth))
    print((d.shape))

    for px,py,pz in points:
        print((px, py, pz))
        px = int(px)
        py = int(py)
        pz = int(pz)
        imi = im[(px-sx):(px+sx+1),(py-sy):(py+sy+1),(pz-sz):(pz+sz+1)]
        print((imi.shape))
        dx, dy, dz = getIntCenter(imi)
        dz -= sz
        F = fftn(imi)
        d = d + ifftn(F*exp(-2j*pi*(kx*-dx + ky*-dy + kz*-dz))).real

    d = scipy.ndimage.gaussian_filter(d, blur)
    #estimate background as a function of z by averaging rim pixels
    #bg = (d[0,:,:].squeeze().mean(0) + d[-1,:,:].squeeze().mean(0) + d[:,0,:].squeeze().mean(0) + d[:,-1,:].squeeze().mean(0))/4
    d = d - d.min()
    d = d/d.max()

    return d
    
def backgroundCorrectPSFWF(d):
    import numpy as np
    from scipy import linalg
    
    zf = d.shape[2]/2
        
    #subtract a linear background in x
    Ax = np.vstack([np.ones(d.shape[0]), np.arange(d.shape[0])]).T        
    bgxf = (d[0,:,zf] + d[-1,:,zf])/2
    gx = linalg.lstsq(Ax, bgxf)[0]
    
    d = d - np.dot(Ax, gx)[:,None,None]
    
    #do the same in y
    Ay = np.vstack([np.ones(d.shape[1]), np.arange(d.shape[1])]).T        
    bgyf = (d[:,0,zf] + d[:,-1,zf])/2
    gy = linalg.lstsq(Ay, bgyf)[0]
    
    d = d - np.dot(Ay, gy)[None, :,None]
    
    
    #estimate background on central slice as mean of rim pixels
    #bgr = (d[0,:,zf].mean() + d[-1,:,zf].mean() + d[:,0,zf].mean() + d[:,-1,zf].mean())/4
    
    #sum over all pixels (and hence mean) should be preserved over z (for widefield psf)
    dm = d.mean(1).mean(0)
    
    bg = dm - dm[zf]
    
    return np.maximum(d - bg[None, None, :], 0) +  1e-5
