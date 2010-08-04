from scipy.interpolate import splprep, splev
import numpy

splines = {}


def calibrate(interpolator, md, roiSize=5):
    #global zvals, dWidth
    #generate grid to evaluate function on
    X, Y, Z = interpolator.getCoords(md, slice(-roiSize,roiSize), slice(-roiSize,roiSize), 0)

    z = numpy.arange(-500, 500, 10)
    ps = []

    for z0 in z:
        d = interpolator.interp(X, Y, Z + z0)
        ps.append(_calcParams(d, X, Y))

    ps = numpy.array(ps)
    A, xp, yp, dw = ps.T

    sp, u = splprep([A], u=z, s=10)
    splines['A'] = sp

    sp, u = splprep([xp], u=z, s=10)
    splines['xp'] = sp

    sp, u = splprep([yp], u=z, s=10)
    splines['yp'] = sp

    #now for z - want this as function of dw (the difference in x & y std. deviations)
    #first look at dw as a function of z & smooth
    sp, u = splprep([dw], u=z, s=10)
    splines['dw'] = sp
    dw2 = splev(z, sp)[0] #evaluate to give smoothed dw values

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

    sp, u = splprep([zm], u=dwm, s=10)
    splines['z'] = sp


def _calcParams(data, X, Y):
    '''calculates the \sigma_x - \sigma_y term used for z position estimation'''
    A = data.max() - data.min() #amplitude

    dr = numpy.maximum(data - data.min() - 0.5*A, 0).squeeze()
    drs = dr.sum()

    x0 = (X[:,None]*dr).sum()/drs
    y0 = (Y[None, :]*dr).sum()/drs

    sig_xl = (numpy.maximum(0, x0 - X)[:,None]*dr).sum()/(drs)
    #sig_xr = (numpy.maximum(0, X - x0)[:,None]*dr).sum()/(drs)

    sig_yu = (numpy.maximum(0, y0 - Y)[None, :]*dr).sum()/(drs)
    #sig_yd = (numpy.maximum(0, Y - y0)[None, :]*dr).sum()/(drs)

    return A, x0, y0, sig_xl - sig_yu


def getStartParameters(data, X, Y, Z=None):
    A, x0, y0, dw = _calcParams(data, X, Y)

    #lookup z
    #clamp dw to valid region
    dw_ = min(max(dw, splines['z'][0][0]), splines['z'][0][-1])
    z0 = max(min(splev(dw_, splines['z'])[0], 500), -500)

    #correct position & intensity estimates for z position
    A = A/splev(z0, splines['A'])[0]
    x0 = x0 - splev(z0, splines['xp'])[0]
    y0 = y0 - splev(z0, splines['yp'])[0]

    b = data.min()

    return [A, x0, y0, -z0, b]
