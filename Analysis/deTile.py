import numpy as np
from scipy import fftpack, ndimage
from PYME.Acquire.Hardware import splitter

from pylab import *


def findRectangularROIs(mask):
    #break up any L shaped rois
    #figure(1)
    #imshow(mask)
    #figure(2)
    #plot(np.abs(np.diff(mask, axis=0)).sum(1))
    #print mask.shape
    mask = mask *np.hstack(([1.], np.abs(np.diff(mask, axis=0)).sum(1) == 0))[:, None]

    labels, nLabels = ndimage.label(mask)

    #print nLabels

    rois = []

    #roisizes = np.array([(labels == i).sum() for i in range(1, nLabels +1)])

    for i in range(1, nLabels +1):

        m2 = (labels == i)

        #print m2.sum()
        xc = np.where(m2.sum(1))[0]
        yc = np.where(m2.sum(0))[0]

        if len(xc) > 5 and len(yc) > 5:
            rois.append([xc[0], yc[0], xc[-1], yc[-1]])

    #print xc[0], yc[0], xc[-1], yc[-1]

    return rois


def calcCorrShift(im1, im2):
    im1 = im1 - im1.mean()
    im2 = im2 - im2.mean()
    xc = np.abs(ifftshift(ifftn(fftn(im1)*ifftn(im2))))

    xct = (xc - xc.max()/1.1)*(xc > xc.max()/1.1)
    print xct.shape

    #figure(1)
    #imshow(xct)

    dx, dy =  ndimage.measurements.center_of_mass(xct)

    return dx - im1.shape[0]/2, dy - im1.shape[1]/2


def tile(ds, xm, ym, mdh, split=True, skipMoveFrames=True, shiftfield=None, mixmatrix=[[1.,0.],[0.,1.]], correlate=False):
    frameSizeX, frameSizeY, numFrames = ds.shape[:3]

    if split:
        frameSizeY /=2
        nchans = 2
        unmux = splitter.Unmixer(shiftfield, 1e3*mdh.getEntry('voxelsize.x'))
    else:
        nchans = 1

    #x & y positions of each frame
    xps = xm(np.arange(numFrames))
    yps = ym(np.arange(numFrames))

    #print xps
    
    #convert to pixels
    xdp = 300 + ((xps - xps.min()) / (1e-3*mdh.getEntry('voxelsize.x'))).round()
    ydp = 300 + ((yps - yps.min()) / (1e-3*mdh.getEntry('voxelsize.y'))).round()

    #print xdp

    #work out how big our tiled image is going to be
    imageSizeX = np.ceil(xdp.max() + frameSizeX + 300)
    imageSizeY = np.ceil(ydp.max() + frameSizeY + 300)

    #allocate an empty array for the image
    im = np.zeros([imageSizeX, imageSizeY, nchans])

    # and to record occupancy (to normalise overlapping tiles)
    occupancy = np.zeros([imageSizeX, imageSizeY, nchans])

    #calculate a weighting matrix (to allow feathering at the edges - TODO)
    weights = np.ones((frameSizeX, frameSizeY, nchans))
    weights[:, :10, :] = 0 #avoid splitter edge artefacts
    weights[:, -10:, :] = 0

    ROIX1 = mdh.getEntry('Camera.ROIPosX')
    ROIY1 = mdh.getEntry('Camera.ROIPosY')

    ROIX2 = ROIX1 + mdh.getEntry('Camera.ROIWidth')
    ROIY2 = ROIY1 + mdh.getEntry('Camera.ROIHeight')

    offset = mdh.getEntry('Camera.ADOffset')

#    #get a sorted list of x and y values
#    xvs = list(set(xdp))
#    xvs.sort()
#
#    yvs = list(set(ydp))
#    yvs.sort()

    for i in range(mdh.getEntry('Protocol.DataStartsAt'), numFrames):
        if xdp[i - 1] == xdp[i] or not skipMoveFrames:
            d = ds[:,:,i]
            if split:
                d = np.concatenate(unmux.Unmix(d, mixmatrix, offset, [ROIX1, ROIY1, ROIX2, ROIY2]), 2)

            if correlate:
                imr = (im[xdp[i]:(xdp[i]+frameSizeX), ydp[i]:(ydp[i]+frameSizeY), :]/occupancy[xdp[i]:(xdp[i]+frameSizeX), ydp[i]:(ydp[i]+frameSizeY), :]).sum(2)
                alreadyThere = (weights*occupancy[xdp[i]:(xdp[i]+frameSizeX), ydp[i]:(ydp[i]+frameSizeY), :]).sum(2) > 0

                if (alreadyThere.sum() > 50):
                    dx = 0
                    dy = 0
                    rois = findRectangularROIs(alreadyThere)

                    for r in rois:
                        x0,y0,x1,y1 = r
                        print r
                        dx_, dy_ = calcCorrShift(d.sum(2)[x0:x1, y0:y1], imr[x0:x1, y0:y1])
                        dx += dx_
                        dy += dy_
                    
                    dx = -np.round(dx/len(rois))
                    dy = -np.round(dy/len(rois))

                    print dx, dy

                    #dx, dy = (0,0)
                else:
                    dx, dy = (0,0)

                im[(xdp[i]+dx):(xdp[i]+frameSizeX + dx), (ydp[i] + dy):(ydp[i]+frameSizeY + dy), :] += weights*d
                occupancy[(xdp[i] + dx):(xdp[i]+frameSizeX + dx), (ydp[i]+dy):(ydp[i]+frameSizeY + dy), :] += weights
                
            else:
                im[xdp[i]:(xdp[i]+frameSizeX), ydp[i]:(ydp[i]+frameSizeY), :] += weights*d
                occupancy[xdp[i]:(xdp[i]+frameSizeX), ydp[i]:(ydp[i]+frameSizeY), :] += weights

    ret =  (im/occupancy).squeeze()
    ret[occupancy == 0] = 0 #fix up /0s

    return ret