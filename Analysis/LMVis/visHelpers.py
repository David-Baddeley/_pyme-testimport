#!/usr/bin/python

##################
# visHelpers.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

#!/usr/bin/python
import scipy
import numpy
import numpy.ctypeslib

from PYME.Analysis.cModels.gauss_app import *
#import subprocess
from PYME.FileUtils import saveTiffStack
from matplotlib import delaunay

from math import floor

import sys

from PYME.Analysis import EdgeDB

#from edgeDB import genEdgeDB#, calcNeighbourDists

multiProc = False

try:
    import multiprocessing
    #import multiprocessing.sharedctypes
    from PYME.shmarray import shmarray
    multiProc = True
except:
    multiProc = False

#def as_mp_shared(x):
#    a = multiprocessing.sharedctypes.RawArray('d', x.size)
#    a2 = numpy.ctypeslib.as_array(a)
#    a2[:] = x[:]
#    return a


#if sys.platform == 'win32':
#    multiProc = False


class ImageBounds:
    def __init__(self, x0, y0, x1, y1, z0=0, z1=0):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.z0 = z0
        self.z1 = z1

    @classmethod
    def estimateFromSource(cls, ds):
        return cls(ds['x'].min(),ds['y'].min(),ds['x'].max(), ds['y'].max() )

    def width(self):
        return self.x1 - self.x0

    def height(self):
        return self.y1 - self.y0


class dummy:
    pass

class GeneratedImage(object):
    def __init__(self, img, imgBounds, pixelSize, sliceSize=0):
        self.img = img
        self.imgBounds = imgBounds

        self.pixelSize = pixelSize
        self.sliceSize = sliceSize

    def save(self, filename):
        if len(self.img.shape) == 2:
            self.save2D(filename)
        else:
            self.save3D(filename)

    def save2D(self, filename):
        import Image
        #save using PIL - because we're using float pretty much only tif will work
        im = Image.fromarray(self.img.astype('f'), 'F')

        im.tag = dummy()
        #set up resolution data - unfortunately in cm as TIFF standard only supports cm and inches
        res_ = int(1e-2/(self.pixelSize*1e-9))
        im.tag.tagdata={296:(3,), 282:(res_,1), 283:(res_,1)}

        im.save(filename)

    def save3D(self, filename):
#        import Image
#        command = ["tiffcp"]
#        # add options here, if any (e.g. for compression)
#
#        #im = im.astype('uint16')
#        #im = im.astype('>u2').astype('<u2')
#
#        for i in range(self.img.shape[2]):
#            framefile = "/tmp/frame%d.tif" % i
#
#            im = Image.fromarray(self.img[:,:,i].astype('f'), 'F')
#            im.save(framefile)
#            command.append(framefile)
#
#        command.append(filename)
#        subprocess.call(command)
#
#        # remove frame files here
#        subprocess.call('rm /tmp/frame*.tif', shell=True)

        #from PYME.FileUtils import saveTiffStack

        saveTiffStack.saveTiffMultipage(self.img, filename)

        

def genEdgeDB(T):
    #make ourselves a quicker way of getting at edge info.
    edb = []
    #edb = numpy.zeros((len(T.x), 2), dtype='O')
    for i in range(len(T.x)):
        edb.append(([],[]))
        #edb[i] = ([],[])

    for i in range(len(T.edge_db)):
        e0, e1 = T.edge_db[i]
        edbe0 = edb[e0]
        edbe1 = edb[e1]
        edbe0[0].append(i)
        edbe0[1].append(e1)
        edbe1[0].append(i)
        edbe1[1].append(e0)


    return edb

mpT = {}

def calcNeighbourDistPart(di, x, y, edb, nStart, nEnd):
    #global T
    #global edb
   
    #di = shmarray.zeros(nEnd - nStart)

    for i in range(nStart, nEnd):
        #incidentEdges = T.edge_db[edb[i][0]]
        #neighbourPoints = edb[i][1]
        #neighbours = edb.getVertexNeighbours(i)
        dist = edb.getVertexEdgeLengths(i)

        #print edb.edgeArray[i, 0]
        #print neighbours

        #incidentEdges = T.edge_db[edb[neighbourPoints[0]][0]]
        #for j in range(1, len(neighbourPoints)):
        #    incidentEdges = scipy.vstack((incidentEdges, T.edge_db[edb[neighbourPoints[j]][0]]))
        #dx = scipy.diff(T.x[incidentEdges])
        #dy = scipy.diff(T.y[incidentEdges])

        #dx = x[neighbours] - x[i]
        #dy = y[neighbours] - y[i]

        #print dx


#        xv = T.x[incidentEdges]
#        dx = xv[:,1] - xv[:,0]
#        yv = T.y[incidentEdges]
#        dy = yv[:,1] - yv[:,0]

        #dist = (dx**2 + dy**2)

        #dist = scipy.sqrt(dist)

        #di[i] = scipy.mean(scipy.sqrt(dist))
        di[i] = scipy.mean(dist)

    #return di


#if False:
#    def calcNeighbourDists(T):
#        edb = EdgeDB.EdgeDB(T, shm=True)
#
#        N = len(T.x)
#
#        di = shmarray.zeros(N)
#
#        taskSize = N/multiprocessing.cpu_count()
#        taskEdges = range(0,N, taskSize) + [N]
#        #print taskEdges
#
#        tasks = [(taskEdges[i], taskEdges[i+1]) for i in range(len(taskEdges)-1)]
#
#        x = shmarray.create_copy(T.x)
#        y = shmarray.create_copy(T.y)
#
#
#        processes = [multiprocessing.Process(target = calcNeighbourDistPart, args=(di, x, y, edb) + t) for t in tasks]
#
#        for p in processes:
#            p.start()
#
#        for p in processes:
#            p.join()
#
#        #print di[:100]
#
#
#        return di
#else:
def calcNeighbourDists(T):
    #edb = genEdgeDB(T)

    edb = EdgeDB.EdgeDB(T)

    #N = len(T.x)
    #di = numpy.zeros(N)

    #calcNeighbourDistPart(di, T.x, T.y, edb, 0, N)

    return edb.getNeighbourDists()




def Gauss2D(Xv,Yv, A,x0,y0,s):
    r = genGauss(Xv,Yv,A,x0,y0,s,0,0,0)
    #r.strides = r.strides #Really dodgy hack to get around something which numpy is not doing right ....
    return r

def rendGauss(x,y, sx, imageBounds, pixelSize):
    fuzz = 3*scipy.median(sx)
    roiSize = int(fuzz/pixelSize)
    fuzz = pixelSize*roiSize

    #print imageBounds.x0
    #print imageBounds.x1
    #print fuzz

    #print pixelSize

    X = numpy.arange(imageBounds.x0 - fuzz,imageBounds.x1 + fuzz, pixelSize)
    Y = numpy.arange(imageBounds.y0 - fuzz,imageBounds.y1 + fuzz, pixelSize)

    #print X
    
    im = scipy.zeros((len(X), len(Y)), 'f')

    #record our image resolution so we can plot pts with a minimum size equal to res (to avoid missing small pts)
    delX = scipy.absolute(X[1] - X[0]) 
    
    for i in range(len(x)):
        ix = scipy.absolute(X - x[i]).argmin()
        iy = scipy.absolute(Y - y[i]).argmin()

        
        imp = Gauss2D(X[(ix - roiSize):(ix + roiSize + 1)], Y[(iy - roiSize):(iy + roiSize + 1)],1, x[i],y[i],max(sx[i], delX))
        im[(ix - roiSize):(ix + roiSize + 1), (iy - roiSize):(iy + roiSize + 1)] += imp

    im = im[roiSize:-roiSize, roiSize:-roiSize]

    return im

def rendTri(T, imageBounds, pixelSize, c=None, im=None):
    from PYME.Analysis.SoftRend import drawTriang, drawTriangles
    xs = T.x[T.triangle_nodes]
    ys = T.y[T.triangle_nodes]

    a = numpy.vstack((xs[:,0] - xs[:,1], ys[:,0] - ys[:,1])).T
    b = numpy.vstack((xs[:,0] - xs[:,2], ys[:,0] - ys[:,2])).T
    b2 = numpy.vstack((xs[:,1] - xs[:,2], ys[:,1] - ys[:,2])).T

    #area of triangle
    #c = 0.5*numpy.sqrt((b*b).sum(1) - ((a*b).sum(1)**2)/(a*a).sum(1))*numpy.sqrt((a*a).sum(1))

    #c = 0.5*numpy.sqrt((b*b).sum(1)*(a*a).sum(1) - ((a*b).sum(1)**2))

    #c = numpy.maximum(((b*b).sum(1)),((a*a).sum(1)))

    if c == None:
        if numpy.version.version > '1.2':
            c = numpy.median([(b * b).sum(1), (a * a).sum(1), (b2 * b2).sum(1)], 0)
        else:
            c = numpy.median([(b * b).sum(1), (a * a).sum(1), (b2 * b2).sum(1)])

    a_ = ((a*a).sum(1))
    b_ = ((b*b).sum(1))
    b2_ = ((b2*b2).sum(1))
    #c_neighbours = c[T.triangle_neighbors].sum(1)
    #c = 1.0/(c + c_neighbours + 1)
    #c = numpy.maximum(c, self.pixelsize**2)
    c = 1.0/(c + 1)

    sizeX = (imageBounds.x1 - imageBounds.x0)/pixelSize
    sizeY = (imageBounds.y1 - imageBounds.y0)/pixelSize

    xs = (xs - imageBounds.x0)/pixelSize
    ys = (ys - imageBounds.y0)/pixelSize

    if im == None:
        im = numpy.zeros((sizeX, sizeY))

#    for i in range(xs.shape[0]):
#        xi = xs[i, :]
#        yi = ys[i, :]
#
#        #if (xi > 0).all() and (xi< (sizeX - 1)).all() and (yi > 0).all() and (yi< (sizeY-1)).all():
#        drawTriang(im, xi[0], yi[0], xi[1], yi[1], xi[2], yi[2], c[i])

#    import threading
#    N = xs.shape[0]
#    t1 = threading.Thread(target=drawTriangles, args = (im, xs[:(N/2),:], ys[:(N/2),:], c[:(N/2)]))
#    t2 = threading.Thread(target=drawTriangles, args = (im, xs[(N/2):,:], ys[(N/2):,:], c[(N/2):]))
#
#    t1.start()
#    t2.start()
#
#    t1.join()
#    t2.join()
    drawTriangles(im, xs, ys, c)

    return im

jParms = {}

def rendJitTri(im, x, y, jsig, mcp, imageBounds, pixelSize, n=1):
    for i in range(n):
        #global jParms
        #locals().update(jParms)
        scipy.random.seed()

        Imc = scipy.rand(len(x)) < mcp
        if type(jsig) == numpy.ndarray:
            #print jsig.shape, Imc.shape
            jsig = jsig[Imc]
        T = delaunay.Triangulation(x[Imc] +  jsig*scipy.randn(Imc.sum()), y[Imc] +  jsig*scipy.randn(Imc.sum()))

        #return T
        rendTri(T, imageBounds, pixelSize, im=im)




if multiProc:
    def rendJitTriang(x,y,n,jsig, mcp, imageBounds, pixelSize):
        import threading
        sizeX = int((imageBounds.x1 - imageBounds.x0)/pixelSize)
        sizeY = int((imageBounds.y1 - imageBounds.y0)/pixelSize)

        im = shmarray.zeros((sizeX, sizeY))

        x = shmarray.create_copy(x)
        y = shmarray.create_copy(y)
        if type(jsig) == numpy.ndarray:
            jsig = shmarray.create_copy(jsig)

        #pool = multiprocessing.Pool()

        #Ts = pool.map(gJitTriang, range(n))

        nCPUs = multiprocessing.cpu_count()

        tasks = (n/nCPUs)*numpy.ones(nCPUs, 'i')
        tasks[:(n%nCPUs)] += 1

        processes = [multiprocessing.Process(target = rendJitTri, args=(im, x, y, jsig, mcp, imageBounds, pixelSize, nIt)) for nIt in tasks]

        for p in processes:
            p.start()

        for p in processes:
            p.join()

        return im/n
else:
    def rendJitTriang(x,y,n,jsig, mcp, imageBounds, pixelSize):
        sizeX = (imageBounds.x1 - imageBounds.x0)/pixelSize
        sizeY = (imageBounds.y1 - imageBounds.y0)/pixelSize

        im = numpy.zeros((sizeX, sizeY))

        for i in range(n):
            Imc = scipy.rand(len(x)) < mcp
            if type(jsig) == numpy.ndarray:
                #print jsig.shape, Imc.shape
                jsig = jsig[Imc]
            T = delaunay.Triangulation(x[Imc] +  jsig*scipy.randn(Imc.sum()), y[Imc] +  jsig*scipy.randn(Imc.sum()))
            rendTri(T, imageBounds, pixelSize, im=im)

        return im/n


def rendJitTet(x,y,z,n,jsig, jsigz, mcp, imageBounds, pixelSize, zb,sliceSize=100):
    import gen3DTriangs

    sizeX = (imageBounds.x1 - imageBounds.x0)/pixelSize
    sizeY = (imageBounds.y1 - imageBounds.y0)/pixelSize

    x = (x - imageBounds.x0)/pixelSize
    y = (y - imageBounds.y0)/pixelSize

    jsig = jsig/pixelSize
    jsigz = jsigz/sliceSize

    z = (z - zb[0])/sliceSize

    sizeZ  = floor((zb[1] + sliceSize - zb[0])/sliceSize)

    im = numpy.zeros((sizeX, sizeY, sizeZ), order='F')

    for i in range(n):
        Imc = scipy.rand(len(x)) < mcp
        if type(jsig) == numpy.ndarray:
            print jsig.shape, Imc.shape
            jsig = jsig[Imc]
            jsigz = jsigz[Imc]

        gen3DTriangs.renderTetrahedra(im, x[Imc]+ jsig*scipy.randn(Imc.sum()), y[Imc]+ jsig*scipy.randn(Imc.sum()), z[Imc]+ jsigz*scipy.randn(Imc.sum()), scale = [1,1,1], pixelsize=[1,1,1])

    return im/n


def rendHist(x,y, imageBounds, pixelSize):
    X = numpy.arange(imageBounds.x0,imageBounds.x1, pixelSize)
    Y = numpy.arange(imageBounds.y0,imageBounds.y1, pixelSize)
    
    im, edx, edy = scipy.histogram2d(x,y, bins=(X,Y))

    return im

def rendHist3D(x,y,z, imageBounds, pixelSize, zb,sliceSize=100):
    X = numpy.arange(imageBounds.x0,imageBounds.x1, pixelSize)
    Y = numpy.arange(imageBounds.y0,imageBounds.y1, pixelSize)
    Z = numpy.arange(zb[0], zb[1] + sliceSize, sliceSize)

    im, ed = scipy.histogramdd([x,y, z], bins=(X,Y,Z))

    return im


def Gauss3d(X, Y, Z, x0, y0, z0, wxy, wz):
    """3D PSF model function with constant background - parameter vector [A, x0, y0, z0, background]"""
    #A, x0, y0, z0, wxy, wz, b = p
    #return A*scipy.exp(-((X-x0)**2 + (Y - y0)**2)/(2*s**2)) + b

    #print X.shape

    return scipy.exp(-((X[:,None]-x0)**2 + (Y[None,:] - y0)**2)/(2*wxy**2) - ((Z-z0)**2)/(2*wz**2))/((2*scipy.pi*wxy**2)*scipy.sqrt(2*scipy.pi*wz**2))

def rendGauss3D(x,y, z, sx, sz, imageBounds, pixelSize, zb, sliceSize=100):
    fuzz = 3*scipy.median(sx)
    roiSize = int(fuzz/pixelSize)
    fuzz = pixelSize*roiSize

    #print imageBounds.x0
    #print imageBounds.x1
    #print fuzz

    #print pixelSize

    X = numpy.arange(imageBounds.x0 - fuzz,imageBounds.x1 + fuzz, pixelSize)
    Y = numpy.arange(imageBounds.y0 - fuzz,imageBounds.y1 + fuzz, pixelSize)
    Z = numpy.arange(zb[0], zb[1], sliceSize)

    #print X

    im = scipy.zeros((len(X), len(Y), len(Z)), 'f')

    #record our image resolution so we can plot pts with a minimum size equal to res (to avoid missing small pts)
    delX = scipy.absolute(X[1] - X[0])

    #for zn in range(len(Z)):
    for i in range(len(x)):
        ix = scipy.absolute(X - x[i]).argmin()
        iy = scipy.absolute(Y - y[i]).argmin()
        iz = scipy.absolute(Z - z[i]).argmin()

        iz_min = max(iz - 3, 0)
        iz_max = min(iz + 4, len(Z))


        imp = genGauss3D(X[(ix - roiSize):(ix + roiSize + 1)], Y[(iy - roiSize):(iy + roiSize + 1)],Z[iz_min:iz_max], 1.,x[i],y[i],z[i], max(sx[i], delX),max(sz[i], sliceSize))
        #print imp.shape
        #print im[(ix - roiSize):(ix + roiSize + 1), (iy - roiSize):(iy + roiSize + 1), zn].shape
        im[(ix - roiSize):(ix + roiSize + 1), (iy - roiSize):(iy + roiSize + 1), iz_min:iz_max] += imp

    im = im[roiSize:-roiSize, roiSize:-roiSize, :]

    return im
