#!/usr/bin/python

import scipy
from Hardware.Simulator import fakeCam, fakePiezo, lasersliders, dSimControl
from Hardware import fakeShutters

#import PYME.cSMI as example

scope.fakePiezo = fakePiezo.FakePiezo(100)
scope.piezos.append((scope.fakePiezo, 1, 'Fake z-piezo'))

scope.cam = fakeCam.FakeCamera(70*scipy.arange(-128.0, 128.0), 70*scipy.arange(-128.0, 128.0), fakeCam.NoiseMaker(), scope.fakePiezo)


#setup for the channels to aquire - b/w camera, no shutters
class chaninfo:
    names = ['bw']
    cols = [1] #1 = b/w, 2 = R, 4 = G1, 8 = G2, 16 = B
    hw = [0] #unimportant - as we have no shutters
    itimes = [100]

scope.chaninfo = chaninfo

scope.shutters = fakeShutters

lsf = lasersliders.LaserSliders(scope.cam)
lsf.Show()

dsc = dSimControl.dSimControl(None, scope)
dsc.Show()

#import remFitPSF
#import Pyro
#tq = Pyro.core.getProxyForURI('PYRONAME://taskQueue')

#import MetaData

#md = MetaData.MetaData(MetaData.VoxelSize(0.07,0.07,0.2))

#def postTask(hi=None):
#    im = example.CDataStack_AsArray(scope.pa.ds,0)[:,:,0]
#    t = remFitPSF.fitTask(im, 10,md)
#    tq.postTask(t)

#scope.pa.WantFrameNotification.append(postTask)

import HDFSpoolFrame
frs = HDFSpoolFrame.FrSpool(None, scope, 'd:\\%(username)s\\%(day)d-%(month)d-%(year)d\\')
frs.Show()


from PYME import cSMI
import time

Is = []

def calcSum(caller):
    Is.append(cSMI.CDataStack_AsArray(caller.ds, 0).sum())

scope.pa.WantFrameNotification.append(calcSum)

