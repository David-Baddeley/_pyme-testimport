#!/usr/bin/python

##################
# astigEstimator.py
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
'''Calculates starting parameters for fitting to an astigmatic PSF. Note that this is already
somewhat more sophisticated than the entire 3D anaylsis used by 'QuickPalm' and the like as
it attempts to correct for coupling between the lateral centroid and defocus'''

from scipy.interpolate import splprep, splev
import numpy
#from pylab import *

splines = {}
rawMeas = {}

sintheta = 0
costheta = 1

TWOCHANNEL = True

def calibrate(interpolator, md, roiSize=5):
    global sintheta, costheta, calibrated
    #global zvals, dWidth
    #generate grid to evaluate function on
    X, Y, Z, safeRegion = interpolator.getCoords(md, slice(-roiSize,roiSize), slice(-roiSize,roiSize), slice(0, 2))
    #print Z, safeRegion
    axialShift = md.Analysis.AxialShift

    if len(X.shape) > 1: #X is a matrix
        X_ = X[:, 0, 0]
        Y_ = Y[0, :, 0]
    else:
        X_ = X
        Y_ = Y

    z = numpy.arange(-500, 500, 10)
    ps = []

    #astigmatic PSF is not necessarily aligned to the axes
    #TODO - estimate rotation rather than requiring it as a parameter
    if 'PSFRotation' in md.getEntryNames():
        theta = numpy.pi*md.PSFRotation/180.
    else:
        theta = 0

    costheta = numpy.cos(theta)
    sintheta = numpy.sin(theta)
    
    print axialShift

    for z0 in z:    
        d1 = interpolator.interp(X, Y, Z + z0)
        d2 = interpolator.interp(X, Y, Z + z0 + axialShift)
#        if z0 % 100 == 0:
#            figure()
#            imshow(d)
        ps.append(_calcParams(numpy.concatenate([numpy.atleast_3d(d1), numpy.atleast_3d(d2)], 2), X_, Y_))

    ps = numpy.array(ps)
    A, xp, yp, s0, s1 = ps.T
    
    dw = s1 - s0
    
    #xp = xp - xp[z.size/2]
    #yp = yp - yp[z.size/2]

    rawMeas['A'] = A
    rawMeas['xp'] = xp
    rawMeas['yp'] = yp
    rawMeas['s0'] = s0
    rawMeas['s1'] = s1
    rawMeas['dw'] = dw

    sp, u = splprep([A], u=z, s=1)
    splines['A'] = sp

    sp, u = splprep([xp], u=z, s=1)
    splines['xp'] = sp

    sp, u = splprep([yp], u=z, s=1)
    splines['yp'] = sp

    #now for z - want this as function of dw (the difference in x & y std. deviations)
    #first look at dw as a function of z & smooth
    sp, u = splprep([dw], u=z, s=5)
    splines['dw'] = sp
    dw2 = splev(z, sp)[0] #evaluate to give smoothed dw values
    
#    imx = dw2.argmax()
#    imn = dw2.argmin()
#    
#    print imn, imx
#    
#    if imx > imn:
#        zm = z[imn:imx]
#        dwm = dw2[imn:imx]
#    else:
#        zm = z[imn:imx:-1]#[::-1]
#        dwm = dw2[imn:imx:-1]#[::-1]
#        
#        print zm, dwm

    #unfortunately dw is not always monotonic - pull out the central section that is
    d_dw = numpy.diff(splev(numpy.arange(-500, 501, 10), sp)[0])

    #find whether gradient is +ve or negative
    sgn = numpy.sign(d_dw)

    #take all bits having the same gradient sign as the central bit
    mask = sgn == sgn[len(sgn)/2]

    zm = z[mask]
    dwm = dw2[mask]
    
    #now sort the values by dw, so we can use dw as the dependant variable
    I = dwm.argsort()
    zm = zm[I]
    dwm = dwm[I]

    sp, u = splprep([zm], u=dwm, s=1)
    splines['z'] = sp




def _calcParams(data, X, Y):
    '''calculates the \sigma_x - \sigma_y term used for z position estimation'''
    A = data.max(1).max(0) - data.min() #amplitude
    
    #threshold at half maximum and subtract threshold
    dr = numpy.maximum(data - data.min() - .5*A[None,None, :], 0).squeeze()
    dr = dr/dr.sum(1).sum(0)[None,None,:]
    #print dr.sum(1).sum(0)[None,None,:] 

    x0 = (X[:,None, None]*dr).sum(1).sum(0)
    y0 = (Y[None, :, None]*dr).sum(1).sum(0)
    
    #print x0

    xn = X[:,None, None] - x0[None,None, :]
    yn = Y[None, :, None] - y0[None,None, :]
    
    #r = numpy.sqrt(xn*xn + yn*yn)

    sig = numpy.sqrt((xn*xn*dr + yn*yn*dr).sum(1).sum(0)) #+ (xn*xn*dr).sum(1).sum(0)
    
    #print A.mean(), x0[0], y0[0], sig[1] - sig[0]
    return A.mean(), x0[0], y0[0], sig[0], sig[1]


def getStartParameters(data, X, Y, Z=None):
    A, x0, y0, s0, s1 = _calcParams(data, X, Y)
    
    dw = s1 - s0

    #clamp dw to valid region
    dw_ = min(max(dw, splines['z'][0][0]), splines['z'][0][-1])
    #lookup z
    z0 = max(min(splev(dw_, splines['z'])[0], 1000), -1000)
    #print z0

    #correct position & intensity estimates for z position
    A = A/splev(z0, splines['A'])[0]
    x0 = x0 - splev(z0, splines['xp'])[0]
    y0 = y0 - splev(z0, splines['yp'])[0]

    b = data.min()

    return [A, x0, y0, -z0, b]

