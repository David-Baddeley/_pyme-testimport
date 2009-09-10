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
    print d.shape

    for i in range(len(points)):
        F = fftn(ims[:,:,i])
        p = points[i,:]
        #print zis[i]
        #print ifftn(F*exp(-2j*pi*(kx*-p[0] + ky*-p[1]))).real.shape
        d[:,:,zis[i]] = d[:,:,zis[i]] + ifftn(F*exp(-2j*pi*(kx*-p[0] + ky*-p[1]))).real

    d = len(zvals)*d/(points[:,2].sum())
    d = d - d.min(1).min(0)[None,None,:]
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
    im2 = im2 - 0.5*im2.max()
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
    print d.shape

    for px,py,pz in points:
        print px, py, pz
        imi = im[(px-sx):(px+sx+1),(py-sy):(py+sy+1),(pz-sz):(pz+sz+1)]
        print imi.shape
        dx, dy, dz = getIntCenter(imi)
        dz -= sz
        F = fftn(imi)
        d = d + ifftn(F*exp(-2j*pi*(kx*-dx + ky*-dy + kz*-dz))).real

    d = d - d.min()
    d = d/d.max()

    return scipy.ndimage.gaussian_filter(d, blur)