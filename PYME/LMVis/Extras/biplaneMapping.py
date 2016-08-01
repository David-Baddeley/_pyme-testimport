
import wx
import numpy as np
from PYME.Analysis.points import twoColour
from PYME.Analysis.points.DeClump import pyDeClump
import os
from PYME.IO.FileUtils import nameUtils
import cPickle

def foldX(pipeline):
    """
    At this point the origin of x should be the corner of the concatenated frame
    """
    xOG = pipeline['x']
    roiSizeNM = (pipeline.mdh['Multiview.ROISize'][1]*pipeline.mdh['voxelsize.x']*1000)  # voxelsize is in um
    xfold = xOG % roiSizeNM
    mvQuad = np.floor(xOG / roiSizeNM)

    pipeline.mapping.setMapping('xFolded', xfold)
    pipeline.mapping.setMapping('whichFOV', mvQuad)
    return

def plotRegistered(regX, regY, multiviewChannels, title=''):
    import matplotlib.pyplot as plt
    nChan = multiviewChannels.max()

    c = iter(plt.cm.rainbow(np.linspace(0, 1, nChan)))
    for ii in range(nChan):
        mask = (ii == multiviewChannels)
        plt.scatter(regX[mask], regY[mask], c=next(c))
    plt.title(title)
    return

def pairMolecules_old(xFold, y, whichFOV, combineDist, FOV1=0, FOV2=1):
    """
    This function will be depreciated, as it is not C-accelerated. Additionally,
    this function would need to be called nROI-1 times, as opposed to once.
    """
    interestingMolecules = np.logical_or(whichFOV == FOV1, whichFOV == FOV2)
    xx = xFold[interestingMolecules]
    yy = y[interestingMolecules]
    chan = whichFOV[interestingMolecules]
    numMol = len(xx)
    dist = np.zeros((numMol, numMol))
    for ind in range(numMol):
        for ii in range(numMol):
            dist[ind, ii] = np.sqrt((xx[ind] - xx[ii])**2 + (yy[ind] - yy[ii])**2)
    dist = dist + (dist == 0)*999999
    minDist = dist.min(axis=0)
    minLoc = dist.argmin(axis=0)

    # keepList = np.where(np.logical_and(FOV[minLoc] != FOV, minLoc[range(numMol)] == minLoc[minLoc[range(numMol)]]))

    # only keep molecule pairs that are mutually nearest neighbors, within a certain distance, and heterozygous in planes
    keep = np.logical_and(minLoc[range(numMol)] == minLoc[minLoc[range(numMol)]],
                          np.logical_and(minDist <= combineDist, chan != chan[minLoc]))
    keepList = np.where(keep)

    minLocKept = minLoc[keep]

    # numKept = len(keepList)
    chan1Keep = np.logical_and(keep, whichFOV == FOV1)
    pairs = minLocKept[chan1Keep]
    # chan2Keep = minLocKept[~chan1Keep] #  np.logical_and(keep, whichFOV == FOV2)
    x1 = xFold[chan1Keep]
    y1 = y[chan1Keep]
    x2 = xFold[pairs]
    y2 = y[pairs]


    return x1, y1, x2, y2

def pairMolecules(tIndex, x, y, deltaX, whichFOV, numFOV):
    # sort everything in frame order
    I = tIndex.argsort()
    tIndex = tIndex[I]
    x = x[I]
    y = y[I]
    whichFOV = whichFOV[I]

    # group within 100nm
    dX = 100.*np.ones_like(deltaX)
    # group localizations
    assigned = pyDeClump.findClumps(tIndex, x, y, dX)

    # only look at clumps with N=numFOVs, where each FOV is represented
    # clumps, nInClump = np.unique(assigned, return_counts=True)
    clumps = np.unique(assigned)
    keptClumps = [np.array_equal(np.unique(whichFOV[assigned == clumps[ii]]), np.arange(numFOV)) for ii in range(len(clumps))]

    keptMoles = []# assigned in clumps[np.where(keptClumps)]
    # np.array_equal(clumps, np.arange(1, np.max(assigned) + 1)) equaluates to True
    # assigned == np.any(clumps[keptClumps])
    for elem in assigned:
        keptMoles.append(elem in clumps[np.where(keptClumps)])
    keep = np.where(keptMoles)

    #return x[keptMoles], y[keptMoles], whichFOV[keptMoles], clumps[keptClumps]
    return x[keep], y[keep], whichFOV[keep], clumps[np.where(keptClumps)]

class biplaneMapper:
    def __init__(self, visFr):
        self.visFr = visFr

        ID_REGISTER_BIPLANE = wx.NewId()
        visFr.extras_menu.Append(ID_REGISTER_BIPLANE, "Biplane - Register Channels")
        visFr.Bind(wx.EVT_MENU, self.OnRegisterBiplane, id=ID_REGISTER_BIPLANE)

        ID_MAP_BIPLANE = wx.NewId()
        visFr.extras_menu.Append(ID_MAP_BIPLANE, "Biplane - Map Z")
        visFr.Bind(wx.EVT_MENU, self.OnFoldAndMap, id=ID_MAP_BIPLANE)
        return

    def applyShiftmaps(self, shiftMapsX, shiftMapsY, xFolded, y, whichFOV, numFOV):
        pipeline = self.visFr.pipeline

        xReg = xFolded + [(whichFOV == ii)*shiftMapsX[ii](xFolded) for ii in range(numFOV)]
        yReg = y + [(whichFOV == ii)*shiftMapsY[ii](y) for ii in range(numFOV)]

        pipeline.mapping.setMapping('xReg', xReg)
        pipeline.mapping.setMapping('yReg', yReg)
        return

    def OnFoldAndMap(self, event):
        pipeline = self.visFr.pipeline

        try:  # load shiftmaps, if present
            numFOV = pipeline.mdh['Multiview.NumROIs']
            self.shiftMapsX = [pipeline.mdh['shiftMapsX.FOV%d' % ii] for ii in range(numFOV)]
            self.shiftMapsY = [pipeline.mdh['shiftMapsY.FOV%d' % ii] for ii in range(numFOV)]

            fid = open(inputFile)
            spx, spy = cPickle.load(fid)
            fid.close()
        except KeyError:
            raise UserWarning('Shiftmaps or number of FOVs not found in metadata')
            return

        foldX(pipeline)

        print('length is %i, max is %d' % (len(pipeline.mapping.__dict__['xFolded']), np.max(pipeline.mapping.__dict__['xFolded'])))
        print('Number of ROIs: %f' % np.max(pipeline.mapping.__dict__['whichFOV']))
        plotRegistered(pipeline.mapping.__dict__['xFolded'], pipeline['y'],
                            pipeline.mapping.__dict__['whichFOV'], 'Raw')

        self.applyShiftmaps(pipeline.mapping.__dict__['xFolded'], pipeline['y'],
                            pipeline.mapping.__dict__['whichFOV'], numFOV)

    def OnRegisterBiplane(self, event):
        from PYME.Analysis.points import twoColour
        pipeline = self.visFr.pipeline

        try:
            numFOV = pipeline.mdh['Multiview.NumROIs']
        except KeyError:
            raise UserWarning('You are either not looking at Biplane Data, or your metadata is incomplete')
            return

        foldX(pipeline)

        print('length is %i, max is %d' % (len(pipeline.mapping.__dict__['xFolded']), np.max(pipeline.mapping.__dict__['xFolded'])))
        print('Number of ROIs: %f' % np.max(pipeline.mapping.__dict__['whichFOV']))

        # Now we need to match up molecules
        #combineDist = 20
        x, y, FOV, clumps = pairMolecules(pipeline['tIndex'], pipeline.mapping.__dict__['xFolded'], pipeline['y'],
                      pipeline['error_x'], pipeline.mapping.__dict__['whichFOV'], numFOV)

        # Generate raw shift vectors (map of displacements between channels) for each FOV
        #xRawShiftVec = [twoColour.genShiftVectors(x[FOV == 0], x[FOV == ii]) for ii in range(1, numFOV)]
        #yRawShiftVec = [twoColour.genShiftVectors(y[FOV == 0], y[FOV == ii]) for ii in range(1, numFOV)]
        numClumps = len(clumps)
        chan1 = (FOV == 0)
        dx = np.zeros((numFOV - 1, numClumps))
        dy = np.zeros_like(dx)
        dxErr = np.ones_like(dx)
        dyErr = np.ones_like(dx)
        for ii in range(numFOV-1):
            chan = (FOV == (ii+1))
            dx[ii, :] = x[chan] - x[chan1]
            dy[ii, :] = y[chan] - y[chan1]
            # TODO: weight dx and dy estimates on x and y localization uncertainty
            # dxErr =
            # dyErr =

        # Generate shiftmaps

        dxx, dyy, spx, spy, good = [twoColour.genShiftVectorFieldQ(x[chan1], y[chan1], dx[ii, :], dy[ii, :], dxErr[ii, :], dyErr[ii, :]) for ii in range(numFOV-1)]

        # apply shiftmaps
        # possible fixme: do we want to plot only results used for generating shiftmap?
        self.applyShiftmaps(spx, spy, x, y, FOV, numFOV)

        # plot unshifted and shifted
        plotRegistered(pipeline.mapping.__dict__['xFolded'], pipeline['y'],
                            pipeline.mapping.__dict__['whichFOV'], 'Raw Folding')

        plotRegistered(pipeline.mapping.__dict__['xReg'], pipeline['yReg'],
                            pipeline.mapping.__dict__['whichFOV'], 'After Registration')

        # store shiftmaps in metadata
        pipeline.mdh.setEntry('chroma.dx', dxx)
        pipeline.mdh.setEntry('chroma.dy', dyy)
        # save shiftmaps (spx and spy)
        defFile = os.path.splitext(os.path.split(self.visFr.GetTitle())[-1])[0] + '.sf'

        fdialog = wx.FileDialog(None, 'Save shift field as ...',
            wildcard='Shift Field file (*.sf)|*.sf', style=wx.SAVE, defaultDir = nameUtils.genShiftFieldDirectoryPath(), defaultFile=defFile)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            fpath = fdialog.GetPath()
            #save as a pickle containing the data and voxelsize

            fid = open(fpath, 'wb')
            cPickle.dump((spx, spy), fid, 2)
            fid.close()


def Plug(visFr):
    """Plugs this module into the gui"""
    biplaneMapper(visFr)