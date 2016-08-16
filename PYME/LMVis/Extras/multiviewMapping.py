
##################
# multiviewMapping.py
#
# Copyright Andrew Barentine, David Baddeley
# david.baddeley@yale.edu
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
# AESB 08, 2016
##################

import wx
import numpy as np
from PYME.Analysis.points.DeClump import pyDeClump
import os
from PYME.IO.FileUtils import nameUtils
import json
import importlib
import scipy.interpolate as terp
from PYME.LMVis.inpFilt import cachingResultsFilter  # mappingFilter  # fitResultsSource

def foldX_old(pipeline, x=None):
    """

    At this point the origin of x should be the corner of the concatenated frame

    Args:
        pipeline:

    Returns: nothing
        Adds folded x-coordinates to the pipeline
        Adds channel assignments to the pipeline

    """
    if not x.__class__ == np.ndarray:
        x = pipeline.selectedDataSource.resultsSource.fitResults['fitResults']['x0']
    roiSizeNM = (pipeline.mdh['Multiview.ROISize'][1]*pipeline.mdh['voxelsize.x']*1000)  # voxelsize is in um
    xfold = x % roiSizeNM
    mvQuad = np.floor(x / roiSizeNM)

    pipeline.mapping.setMapping('xFolded', xfold)
    pipeline.mapping.setMapping('whichChan', mvQuad)
    return

def foldX(pipeline):
    """

    At this point the origin of x should be the corner of the concatenated frame

    Args:
        pipeline:

    Returns: nothing
        Adds folded x-coordinates to the pipeline
        Adds channel assignments to the pipeline

    """
    roiSizeNM = (pipeline.mdh['Multiview.ROISize'][1]*pipeline.mdh['voxelsize.x']*1000)  # voxelsize is in um

    pipeline.mapping.addVariable('roiSizeNM', roiSizeNM)

    pipeline.addColumn('chromadx', 0*pipeline['x'])
    pipeline.addColumn('chromady', 0*pipeline['y'])

    pipeline.mapping.setMapping('whichChan', 'floor(x/roiSizeNM).astype(int)')
    pipeline.mapping.setMapping('x', 'x%roiSizeNM + chromadx')
    pipeline.mapping.setMapping('y', 'y + chromady')

    return

def plotFolded(X, Y, multiviewChannels, title=''):
    """

    Args:
        X: array of localization x-positions
        Y: array of localization y-positions
        multiviewChannels: array of channel assignment of localizations
        title: title of plot

    Returns: nothing
        Plots unclumped raw localizations folded into the first channel

    """
    import matplotlib.pyplot as plt
    plt.figure()
    nChan = len(np.unique(multiviewChannels))

    c = iter(plt.cm.rainbow(np.linspace(0, 1, nChan)))
    for ii in range(nChan):
        mask = (ii == multiviewChannels)
        plt.scatter(X[mask], Y[mask], c=next(c), label='Chan #%i' % ii)
    plt.title(title)
    plt.legend()
    return

'''def plotRegistered(regX, regY, numChan, title=''):
    """

    Args:
        regX: list in which each element is an array of registered x-positions of molecules for a single channel
        regY: list in which each element is an array of registered y-positions of molecules for a single channel
        numChan: number of multiview channels
        title: title of plot

    Returns: nothing
        Plots molecules using the format that localization-clump positions are stored in.

    """
    import matplotlib.pyplot as plt
    plt.figure()
    c = iter(plt.cm.rainbow(np.linspace(0, 1, numChan)))
    for ii in range(numChan):
        plt.scatter(regX[ii], regY[ii], c=next(c), label='Chan #%i' % ii)
    plt.title(title)
    plt.legend()
    return'''

def pairMolecules(tIndex, x, y, whichChan, deltaX=[None], appearIn=np.arange(4), nFrameSep=5):
    """
    pairMolecules uses pyDeClump functions to group localization clumps into molecules for registration.

    Args:
        tIndex: from fitResults
        x: x positions of localizations AFTER having been folded into the first channel
        y: y positions of localizations
        whichChan: a vector containing channel assignments for each localization
        numChan: number of multiview channels
        deltaX: distance within which neighbors will be clumped is set by 2*deltaX[i])**2
        appearances: number of channels that must be present in a clump to be clumped

    Returns:
        x and y positions of molecules that were clumped, which channel those localizations are from,
        and which clump they were assigned to. Note that outputs are length = #molecules, and the keep
        vector that is return needs to be applied as: xkept = x[keep] in order to only look at kept molecules.
        Note that the returned x, y, tIndex and whichChan are resorted.

    """
    # group within a certain distance, potentially based on localization uncertainty
    if not deltaX[0]:
        deltaX = 100.*np.ones_like(x)
    # group localizations
    assigned = pyDeClump.findClumps(tIndex, x, y, deltaX, nFrameSep)
    print assigned.min()
    # only look at clumps with localizations from each channel
    clumps = np.unique(assigned)
    # Note that this will never be a keep clump if an ignore channel is present...
    keptClumps = [np.array_equal(np.unique(whichChan[assigned == clumps[ii]]), appearIn) for ii in range(len(clumps))]
    #keptClumps = [(len(np.unique(whichChan[assigned == clumps[ii]])) >= appearances) for ii in range(len(clumps))]

    keptMoles = []
    # np.array_equal(clumps, np.arange(1, np.max(assigned) + 1)) evaluates to True
    for elem in assigned:
        keptMoles.append(elem in clumps[np.where(keptClumps)])
    keep = np.where(keptMoles)

    # don't clump molecules from the wrong channel (done by parsing modified whichChan to this function)
    ignoreChan = whichChan < 0
    numClump = np.max(assigned)
    igVec = np.arange(numClump + 1, numClump + 1 + sum(ignoreChan))
    # give ignored channel localizations unique clump assignments
    assigned[ignoreChan] = igVec


    return assigned, keep

def applyShiftmaps_old(pipeline, shiftWallet, numChan):
    """
    applyShiftmaps loads multiview shiftmap parameters from multiviewMapper.shiftWallet, reconstructs the shiftmap
    objects, applies them to the multiview data, and maps the positions registered to the first channel to the pipeline

    Args:
        x: vector of localization x-positions
        y: vector of localization y-positions
        numChan: number of multiview channels

    Returns: nothing
        Maps shifted x-, and y-positions into the pipeline
        xReg and yReg are both lists, where each element is an array of positions corresponding to a given channel

    """
    fres = pipeline.selectedDataSource.resultsSource.fitResults
    try:
        alreadyDone = pipeline.mapping.registered
        return
    except:
        pass

    # import shiftModel to be reconstructed
    model = shiftWallet['shiftModel'].split('.')[-1]
    shiftModule = importlib.import_module(shiftWallet['shiftModel'].split('.' + model)[0])
    shiftModel = getattr(shiftModule, model)


    x, y = pipeline.mapping.xFolded, fres['fitResults']['y0']
    chan = pipeline.mapping.whichChan
    # note that this will not throw out localizations outside of the frame, this will need to be done elsewhere
    for ii in range(1, numChan):
        chanMask = chan == ii
        x = x + chanMask*shiftModel(dict=shiftWallet['Chan0%s.X' % ii]).ev(x, y)
        y = y + chanMask*shiftModel(dict=shiftWallet['Chan0%s.Y' % ii]).ev(x, y)

    # flag that this data has already been registered so it is not registered again
    pipeline.mapping.setMapping('registered', True)
    return x, y

def applyShiftmaps(pipeline, shiftWallet, numChan):
    """
    applyShiftmaps loads multiview shiftmap parameters from multiviewMapper.shiftWallet, reconstructs the shiftmap
    objects, applies them to the multiview data, and maps the positions registered to the first channel to the pipeline

    Args:
        x: vector of localization x-positions
        y: vector of localization y-positions
        numChan: number of multiview channels

    Returns: nothing
        Maps shifted x-, and y-positions into the pipeline
        xReg and yReg are both lists, where each element is an array of positions corresponding to a given channel

    """
    #fres = pipeline.selectedDataSource.resultsSource.fitResults
    #try:
    #    alreadyDone = pipeline.mapping.registered
    #    return
    #except:
    #    pass

    # import shiftModel to be reconstructed
    model = shiftWallet['shiftModel'].split('.')[-1]
    shiftModule = importlib.import_module(shiftWallet['shiftModel'].split('.' + model)[0])
    shiftModel = getattr(shiftModule, model)


    x, y = pipeline.mapping['x'], pipeline.mapping['y']

    # FIXME: the camera roi positions below would not account for the multiview data source
    #x = x + pipeline.mdh['Camera.ROIX0']*pipeline.mdh['voxelsize.x']*1.0e3
    #y = y + pipeline.mdh['Camera.ROIY0']*pipeline.mdh['voxelsize.y']*1.0e3
    chan = pipeline.mapping['whichChan']

    dx = 0
    dy = 0
    for ii in range(1, numChan):
        chanMask = chan == ii
        dx = dx + chanMask*shiftModel(dict=shiftWallet['Chan0%s.X' % ii]).ev(x, y)
        dy = dy + chanMask*shiftModel(dict=shiftWallet['Chan0%s.Y' % ii]).ev(x, y)

    pipeline.addColumn('chromadx', dx)
    pipeline.addColumn('chromady', dy)

def astigMAPism(fres, stigLib, chanPlane):
    """
    Look up table
    Args:
        sigVals:

    Returns:

    """
    # fres = pipeline.selectedDataSource.resultsSource.fitResults
    numMols = len(fres['fitResults_x0'])
    whichChan = np.array(fres['whichChan'], dtype=np.int32)
    # stigLib['zRange'] contains the extrema of acceptable z-positions looking over all channels
    zVal = np.arange(stigLib['zRange'][0], stigLib['zRange'][1])

    sigCalX = {}
    sigCalY = {}

    z = np.zeros(numMols)

    # generate look up table of sorts
    for ii in np.unique(whichChan):
        zdat = np.array(stigLib['PSF%i' % ii]['z'])
        # find indices of range we trust
        zrange = stigLib['PSF%i' % ii]['zrange']
        lowsubZ , upsubZ = np.absolute(zdat - zrange[0]), np.absolute(zdat - zrange[1])
        lowZLoc = np.argmin(lowsubZ)
        upZLoc = np.argmin(upsubZ)

        sigCalX['chan%i' % ii] = terp.UnivariateSpline(zdat[lowZLoc:upZLoc],
                                                       np.array(stigLib['PSF%i' % ii]['sigmax'])[lowZLoc:upZLoc], ext='zeros')(zVal)
                                                            # bbox=stigLib['PSF%i' % ii]['zrange'], ext='zeros')(zVal)
        sigCalY['chan%i' % ii] = terp.UnivariateSpline(zdat[lowZLoc:upZLoc],
                                                       np.array(stigLib['PSF%i' % ii]['sigmay'])[lowZLoc:upZLoc], ext='zeros')(zVal)
        sigCalX['chan%i' % ii][sigCalX['chan%i' % ii] == 0] = 1e5  # np.nan_to_num(np.inf)
        sigCalY['chan%i' % ii][sigCalY['chan%i' % ii] == 0] = 1e5  # np.nan_to_num(np.inf)
        '''for mi in range(numMols):
            if whichChan[mi] == ii:
                wx = 1./fres['fitError']['sigmaxPlane%i' % chanPlane[ii]][mi]**2
                wy = 1./fres['fitError']['sigmayPlane%i' % chanPlane[ii]][mi]**2
                errX = wx*(fres['fitResults']['sigmaxPlane%i' % chanPlane[ii]][mi] - sigCalX['chan%i' % ii])**2
                errY = wy*(fres['fitResults']['sigmayPlane%i' % chanPlane[ii]][mi] - sigCalY['chan%i' % ii])**2
                #wx = 1./fres['fitError']['sigmaxPlane%i' % chanPlane[ii]][mi]**2
                #wy = 1./fres['fitError']['sigmayPlane%i' % chanPlane[ii]][mi]**2
                #errX = wx*(fres['fitResults']['sigmaxPlane%i' % chanPlane[ii]][mi] - sigCalX['chan%i' % ii])**2
                #errY = wy*(fres['fitResults']['sigmayPlane%i' % chanPlane[ii]][mi] - sigCalY['chan%i' % ii])**2
                # find minimum
                try:
                    z[mi] = zVal[np.nanargmin(errX + errY)]
                except:
                    print('No sigmas in correct plane for this molecule')'''
    for mi in range(numMols):
        chans = np.where(fres['planeCounts'][mi] > 0)[0]
        # cnum = len(chans)
        errX, errY = 0, 0
        for ci in chans:
            wx = 1./(fres['fitError_sigmaxPlane%i' % chanPlane[ci]][mi])**2
            wy = 1./(fres['fitError_sigmayPlane%i' % chanPlane[ci]][mi])**2
            errX += wx*(fres['fitResults_sigmaxPlane%i' % chanPlane[ci]][mi] - sigCalX['chan%i' % ci])**2
            errY += wy*(fres['fitResults_sigmayPlane%i' % chanPlane[ci]][mi] - sigCalY['chan%i' % ci])**2
        try:
            z[mi] = zVal[np.nanargmin(errX + errY)]
        except:
            print('No sigmas in correct plane for this molecule')
    #pipeline.selectedDataSource.addColumn('zPos', z)
    #pipeline.Rebuild()
    return z

def coalesceDict(inD, assigned):  #, notKosher=None):
    """
    Agregates clumps to a single event
    Note that this will evaluate the lazy pipeline events and add them into the dict as an array, not a code
    object
    """
    NClumps = int(np.max(assigned))  # len(np.unique(assigned))  #

    #work out what the data type for our declumped data should be
    #dt = deClumpedDType(fitResults)

     #np.empty(NClumps, dt)
    fres = {}

    #dtr = '%df4' % len(f['fitResults'].dtype)

    clist = [[] for i in xrange(NClumps)]
    for i, c in enumerate(assigned):
        clist[int(c-1)].append(i)


    for rkey in inD.keys():
        skey = rkey.split('_')

        if skey[0] == 'fitResults':
            fres[rkey] = np.empty(NClumps)
            errKey = 'fitError_' + skey[1]
            fres[errKey] = np.empty(NClumps)
            for i in xrange(NClumps):
                ci = clist[i]
                fres[rkey][i], fres[errKey][i] = pyDeClump.weightedAverage_(inD[rkey][ci], inD[errKey][ci], None)
        elif rkey == 'tIndex':
            fres[rkey] = np.empty(NClumps)
            for i in xrange(NClumps):
                ci = clist[i]
                fres['tIndex'][i] = inD['tIndex'][ci].min()

        elif rkey == 'whichChan':
            fres[rkey] = np.empty(NClumps, dtype=np.int32)
            if 'planeCounts' in inD.keys():
                fres['planeCounts'] = np.empty((NClumps, inD['planeCounts'].shape[1]))
                for i in xrange(NClumps):
                    ci = clist[i]
                    cl = inD[rkey][ci]

                    fres[rkey][i] = np.array(np.bincount(cl).argmax(), dtype=np.int32)  # set channel to mode

                    #if np.logical_and(len(np.unique(cl)) > 1, np.any([entry in cl for entry in notKosher])):

                    #fres['planeCounts'][i] = inD['planeCounts'][ci][:].sum(axis=0)
                    fres['planeCounts'][i][:] = 0  # inD['planeCounts'][ci][:].sum(axis=0)
                    cind, counts = np.unique(cl, return_counts=True)
                    #fres['planeCounts'][i][:] = 0  # zero everything since the array will be empty, and we don't know numChan
                    fres['planeCounts'][i][cind] += counts.astype(np.int32)

            else:
                for i in xrange(NClumps):
                    ci = clist[i]
                    cl = inD[rkey][ci]

                    fres[rkey][i] = np.array(np.bincount(cl).argmax(), dtype=np.int32)  # set channel to mode

        elif rkey == 'planeCounts' or skey[0] == 'fitError':
            pass

        else:  # settle for the unweighted mean
            fres[rkey] = np.empty(NClumps)
            for i in xrange(NClumps):
                ci = clist[i]
                fres[rkey][i] = inD[rkey][ci].mean()

    return fres

class multiviewMapper:
    """

    multiviewMapper provides methods for registering multiview channels as acquired in multicolor or biplane imaging.
    Image frames for multiview data should have channels concatonated horizontally, such that the x-dimension is the
    only dimension that needs to be folded into the first channel.
    The shiftmaps are functions that interface like bivariate splines, but can be recreated from a dictionary of their
    fit-model parameters, which are stored in a dictionary in the shiftmap object.
    In the multiviewMapper class, shiftmaps for multiview data sources are stored in a dictionary of dictionaries.
    Each shiftmap is stored as a dictionary so that it can be easily written into a human-readable json file. These
    shiftmaps are then stored in the shiftWallet dictionary.

    """
    def __init__(self, visFr):
        self.visFr = visFr

        ID_CALIBRATE_SHIFTS = wx.NewId()
        visFr.extras_menu.Append(ID_CALIBRATE_SHIFTS, "Multiview - Calibrate Shifts")
        visFr.Bind(wx.EVT_MENU, self.OnCalibrateShifts, id=ID_CALIBRATE_SHIFTS)

        ID_MAP_XY = wx.NewId()
        visFr.extras_menu.Append(ID_MAP_XY, "Multiview - Map XY")
        visFr.Bind(wx.EVT_MENU, self.OnFoldAndMapXY, id=ID_MAP_XY)

        ID_MAP_Z = wx.NewId()
        visFr.extras_menu.Append(ID_MAP_Z, "Astigmatism - Map Z")
        visFr.Bind(wx.EVT_MENU, self.OnMapZ, id=ID_MAP_Z)
        return

    def applyShiftmaps_nonOrderConserving(self, x, y, shiftWallet, numChan):
        """
        applyShiftmaps loads multiview shiftmap parameters from multiviewMapper.shiftWallet, reconstructs the shiftmap
        objects, applies them to the multiview data, and maps the positions registered to the first channel to the pipeline

        Args:
            x: vector of localization x-positions
            y: vector of localization y-positions
            numChan: number of multiview channels

        Returns: nothing
            Maps shifted x-, and y-positions into the pipeline
            xReg and yReg are both lists, where each element is an array of positions corresponding to a given channel

        """
        pipeline = self.visFr.pipeline

        # import shiftModel to be reconstructed
        model = shiftWallet['shiftModel'].split('.')[-1]
        shiftModule = importlib.import_module(shiftWallet['shiftModel'].split('.' + model)[0])
        shiftModel = getattr(shiftModule, model)

        # Note: this does not keep
        xReg, yReg, chan = [x[0]], [y[0]], [np.zeros_like(x[0])]
        for ii in range(1, numChan):
            xReg.append(x[ii] + shiftModel(dict=shiftWallet['Chan0%s.X' % ii]).ev(x[ii], y[ii]))
            yReg.append(y[ii] + shiftModel(dict=shiftWallet['Chan0%s.Y' % ii]).ev(x[ii], y[ii]))
            chan.append(ii*np.ones_like(xReg[ii]))

        xReg = np.hstack(xReg)
        yReg = np.hstack(yReg)
        chan = np.hstack(chan)

        pipeline.mapping.setMapping('xReg', xReg)
        pipeline.mapping.setMapping('yReg', yReg)
        pipeline.mapping.setMapping('regChan', chan)
        #pipeline['xReg'] = xReg
        #pipeline['yReg'] = yReg
        return

    def OnFoldAndMapXY(self, event):
        """
        OnFoldAndMap uses shiftmaps stored in metadata (by default) or loaded through the GUI to register multiview channelss
        to the first channel.
        Args:
            event: GUI event

        Returns: nothing
            x- and y-positions will be registered to the first channel and stored in the pipeline dictionary as xReg and
            yReg. Their structure is described in applyShiftmaps

        """
        pipeline = self.visFr.pipeline
        fres = pipeline.selectedDataSource.resultsSource.fitResults

        try:  # load shiftmaps from metadata, if present
            shiftWallet = pipeline.mdh['Shiftmap']
        except AttributeError:
            try:  # load through GUI dialog
                fdialog = wx.FileDialog(None, 'Load shift field', wildcard='Shift Field file (*.sf)|*.sf',
                                        style=wx.OPEN, defaultDir=nameUtils.genShiftFieldDirectoryPath())
                succ = fdialog.ShowModal()
                if (succ == wx.ID_OK):
                    fpath = fdialog.GetPath()
                    # load json
                    fid = open(fpath, 'r')
                    shiftWallet = json.load(fid)
                    fid.close()
            except:
                raise IOError('Shiftmaps not found in metadata and could not be loaded from file')

        from PYME.LMVis.inpFilt import fitResultsSource
        numChan = pipeline.mdh['Multiview.NumROIs']
        # fold x-positions into the first channel
        foldX(pipeline)

        plotFolded(pipeline['x'], pipeline['y'],
                            pipeline['whichChan'], 'Raw')

        # apply shiftmaps
        #x, y = applyShiftmaps(pipeline, shiftWallet, numChan)
        applyShiftmaps(pipeline, shiftWallet, numChan)

        # create new data source
        #fres = pipeline.selectedDataSource.resultsSource.fitResults
        #regFres = np.copy(fres)
        #regFres['fitResults']['x0'], regFres['fitResults']['y0'] = x, y
        #pipeline.addDataSource('RegisteredXY', fitResultsSource(regFres))
        #pipeline.selectDataSource('RegisteredXY')

    def OnCalibrateShifts(self, event):
        """

        OnRegisterMultiview generates multiview shiftmaps on bead-data. Only beads which show up in all channels are
        used to generate the shiftmap.

        Args:
            event: GUI event

        Returns: nothing
            Writes shiftmapWallet into metadata as well as saving a json formatted .sf file through a GUI dialog
        """
        from PYME.Analysis.points import twoColour
        pipeline = self.visFr.pipeline

        try:
            numChan = pipeline.mdh['Multiview.NumROIs']
        except AttributeError:
            raise AttributeError('You are either not looking at multiview Data, or your metadata is incomplete')

        # fold x position of channels into the first, note that we are using the filtered results
        foldX(pipeline)

        plotFolded(pipeline['x'], pipeline['y'], pipeline['whichChan'], 'Raw')
        # sort in frame order
        I = pipeline['tIndex'].argsort()
        xsort, ysort = pipeline['x'][I], pipeline['y'][I]
        chanSort = pipeline['whichChan'][I]

        # Match up molecules, note that all inputs must be sorted in frame order!
        clumpID, keep = pairMolecules(pipeline['tIndex'][I], xsort, ysort, chanSort,
                                      appearIn=np.arange(numChan))  #, pipeline['error_x'])

        #FIXME: COALESCE HERE
        fres = {}
        for pkey in pipeline.keys():
            fres[pkey] = pipeline[pkey][I][keep]

        # make sure clumpIDs are contiguous from [1, numClumps)
        assigned = -1*np.ones_like(clumpID[keep])
        clumpVec = np.unique(clumpID[keep])
        for ci in range(len(assigned)):  # range(len(clumpVec)):
            #cMask = clumpID[keep] == clumpVec[ci]
            assigned[ci] = ci + 1  #FIXME: cluster assignments currently must start from 1, which is mean.

        cFres = coalesceDict(fres, assigned)
        #FIXME: plot clumped
        plotFolded(cFres['x'], cFres['y'],
                            cFres['whichChan'], 'Clumped')

        # only look at the ones which showed up in all channels
        x = xsort[keep]
        y = ysort[keep]
        Chan = chanSort[keep]
        clumpID = clumpID[keep]
        # Generate raw shift vectors (map of displacements between channels) for each channel
        molList = np.unique(clumpID)
        numMoles = len(molList)

        dx = np.zeros((numChan - 1, numMoles))
        dy = np.zeros_like(dx)
        dxErr = np.zeros_like(dx)
        dyErr = np.zeros_like(dx)
        xClump, yClump, xStd, yStd = [], [], [], []
        shiftWallet = {}
        # dxWallet, dyWallet = {}, {}
        for ii in range(numChan):
            chanMask = (Chan == ii)
            xChan = np.zeros(numMoles)
            yChan = np.zeros(numMoles)
            xChanStd = np.zeros(numMoles)
            yChanStd = np.zeros(numMoles)


            for ind in range(numMoles):
                # merge clumps within channels
                clumpMask = np.where(np.logical_and(chanMask, clumpID == molList[ind]))
                xChan[ind] = x[clumpMask].mean()
                yChan[ind] = y[clumpMask].mean()
                xChanStd[ind] = x[clumpMask].std()
                yChanStd[ind] = y[clumpMask].std()

            xClump.append(xChan)
            yClump.append(yChan)
            xStd.append(xChanStd)
            yStd.append(yChanStd)

            if ii > 0:
                dx[ii - 1, :] = xClump[0] - xClump[ii]
                dy[ii - 1, :] = yClump[0] - yClump[ii]
                dxErr[ii - 1, :] = np.sqrt(xStd[ii]**2 + xStd[0]**2)
                dyErr[ii - 1, :] = np.sqrt(yStd[ii]**2 + yStd[0]**2)
                # generate shiftmap between ii-th channel and the 0th channel
                dxx, dyy, spx, spy, good = twoColour.genShiftVectorFieldQ(xClump[0], yClump[0], dx[ii-1, :], dy[ii-1, :], dxErr[ii-1, :], dyErr[ii-1, :])
                # store shiftmaps in multiview shiftWallet
                shiftWallet['Chan0%s.X' % ii], shiftWallet['Chan0%s.Y' % ii] = spx.__dict__, spy.__dict__
                # dxWallet['Chan0%s' % ii], dyWallet['Chan0%s' % ii] = dxx, dyy


        shiftWallet['shiftModel'] = '.'.join([spx.__class__.__module__, spx.__class__.__name__])

        applyShiftmaps(pipeline, shiftWallet, numChan)

        plotFolded(pipeline['x'], pipeline['y'],
                            pipeline['whichChan'], 'All beads after Registration')

        # cFres['whichChan'] = cFres['whichChan'].astype(np.float64)
        pipeline.addDataSource('XY-Registered', cachingResultsFilter(cFres))
        pipeline.selectDataSource('XY-Registered')
        applyShiftmaps(pipeline, shiftWallet, numChan)

        plotFolded(pipeline['x'], pipeline['y'],
                            pipeline['whichChan'], 'Clumps after Registration')


        # save shiftmaps
        defFile = os.path.splitext(os.path.split(self.visFr.GetTitle())[-1])[0] + 'MultiView.sf'

        fdialog = wx.FileDialog(None, 'Save shift field as ...',
            wildcard='Shift Field file (*.sf)|*.sf', style=wx.SAVE, defaultDir=nameUtils.genShiftFieldDirectoryPath(), defaultFile=defFile)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            fpath = fdialog.GetPath()

            fid = open(fpath, 'wb')
            json.dump(shiftWallet, fid)
            fid.close()

    def OnMapZ(self, event):
        pipeline = self.visFr.pipeline

        # get channel and color info
        try:
            numChan = pipeline.mdh['Multiview.NumROIs']
            try:
                chanColor = [0, 1, 1, 0]#pipeline.mdh['Multiview.ChannelColor']  # Bewersdorf Biplane example: [0, 1, 1, 0]
            except AttributeError:
                chanColor = [0 for c in range(numChan)]
            try:
                chanPlane = [0, 0, 1, 1]#pipeline.mdh['Multiview.ChannelPlane']  # Bewersdorf Biplane example: [0, 0, 1, 1]
            except AttributeError:
                chanPlane = [0 for c in range(numChan)]
            numPlanes = len(np.unique(chanPlane))
        except AttributeError:  # default to non-multiview options
            numChan = 1
            chanColor = [0]
            numPlanes = 1

        try:  # load astigmatism calibrations from metadata, if present
            stigLib = pipeline.mdh['astigLib']
        except AttributeError:
            try:  # load through GUI dialog
                fdialog = wx.FileDialog(None, 'Load Astigmatism Calibration', #wildcard='Shift Field file (*.sf)|*.sf',
                                        wildcard='AstigMAPism file (*.am)|*.am', style=wx.OPEN, defaultDir=nameUtils.genShiftFieldDirectoryPath())
                succ = fdialog.ShowModal()
                if (succ == wx.ID_OK):
                    fpath = fdialog.GetPath()
                    # load json
                    fid = open(fpath, 'r')
                    stigLib = json.load(fid)
                    fid.close()
            except:
                raise IOError('Astigmatism sigma-Z mapping information not found')

        # make sure xy-registration has already happened:
        if 'registered' not in pipeline.keys():
            print('registering multiview channels in x-y plane')
            self.OnFoldAndMapXY(event)

        # add separate sigmaxy columns for each plane
        for pind in range(numPlanes):
            pMask = [chanPlane[p] == pind for p in pipeline.mapping['whichChan']]

            pipeline.addColumn('fitResults_sigmaxPlane%i' % pind, pMask*pipeline.mapping['fitResults_sigmax'])
            pipeline.addColumn('fitResults_sigmayPlane%i' % pind, pMask*pipeline.mapping['fitResults_sigmay'])
            pipeline.addColumn('fitError_sigmaxPlane%i' % pind, pMask*pipeline.mapping['fitError_sigmax'])
            pipeline.addColumn('fitError_sigmayPlane%i' % pind, pMask*pipeline.mapping['fitError_sigmay'])
            # replace zeros in fiterror with infs so their weights are zero
            pipeline.mapping['fitError_sigmaxPlane%i' % pind][pipeline.mapping['fitError_sigmaxPlane%i' % pind] == 0] = np.inf
            pipeline.mapping['fitError_sigmayPlane%i' % pind][pipeline.mapping['fitError_sigmayPlane%i' % pind] == 0] = np.inf

        ni = len(pipeline.mapping['whichChan'])
        fres = {}
        for pkey in pipeline.keys():
            fres[pkey] = pipeline[pkey]

        fres['planeCounts'] = np.zeros((len(fres['fitResults_x0']), numChan))

        for cind in np.unique(chanColor):
            # copy pipeline keys and sort in order of frames
            I = np.argsort(fres['tIndex'])
            for pkey in pipeline.keys():
                fres[pkey] = fres[pkey][I]

            # make sure NaNs (awarded when there is no sigma in a given plane of a clump) do not carry over from when
            # ignored channel localizations were clumped by themselves
            for pp in range(numPlanes):
                fres['fitResults_sigmaxPlane%i' % pp][np.isnan(fres['fitResults_sigmaxPlane%i' % pp])] = 0
                fres['fitResults_sigmayPlane%i' % pp][np.isnan(fres['fitResults_sigmayPlane%i' % pp])] = 0

            # trick pairMolecules function by tweaking the channel vector
            planeInColorChan = np.copy(fres['whichChan'])
            chanColor = np.array(chanColor)
            ignoreChans = np.where(chanColor != cind)[0]
            igMask = [mm in ignoreChans.tolist() for mm in planeInColorChan]
            planeInColorChan[np.where(igMask)] = -9  # must be negative to be ignored

            # assign molecules to clumps
            clumpID, paired = pairMolecules(fres['tIndex'], fres['fitResults_x0'], fres['fitResults_y0'],
                                            planeInColorChan, deltaX=fres['fitError_x0'],
                                            appearIn=np.where(chanColor == cind)[0], nFrameSep=1)

            # make sure clumpIDs are contiguous from [0, numClumps)
            assigned = -1*np.ones_like(clumpID)
            clumpVec = np.unique(clumpID)
            for ci in range(len(clumpVec)):
                cMask = clumpID == clumpVec[ci]
                assigned[cMask] = ci + 1  #FIXME: cluster assignments currently must start from 1, which is mean.

            # coalesce clumped localizations into single data point
            fres = coalesceDict(fres, assigned)  #, ignoreChans)

        print('Clumped %i localizations' % (ni - len(fres['whichChan'])))

        # look up z-positions
        z = astigMAPism(fres, stigLib, chanPlane)
        fres['astigZ'] = z

        # make sure there is no z, so that focus will be added during addDataSource
        del fres['z']
        pipeline.addDataSource('Zmapped', cachingResultsFilter(fres))
        pipeline.selectDataSource('Zmapped')



def Plug(visFr):
    """Plugs this module into the gui"""
    multiviewMapper(visFr)
