#!/usr/bin/python

##################
# init_TIRF.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

from PYME.Acquire.Hardware.Old import Sensicam
#from PYME.Acquire.Hardware.AndorIXon import AndorControlFrame

from PYME.Acquire.Hardware import fakeShutters
import time

InitBG('CCD Camera', '''
scope.cam = Sensicam.CCamera()
scope.cam.Init()
from PYME.Acquire.Hardware.Old.Sensicam import sensicamMetadata
camMD = sensicamMetadata.sensicamMD(scope.cam)
''')
#InitGUI('''
#acf = AndorControlFrame.AndorPanel(MainFrame, scope.cam, scope)
#camPanels.append((acf, 'Andor EMCCD Properties'))
#''')

#setup for the channels to aquire - b/w camera, no shutters
class chaninfo:
    names = ['bw']
    cols = [1] #1 = b/w, 2 = R, 4 = G1, 8 = G2, 16 = B
    hw = [fakeShutters.CH1] #unimportant - as we have no shutters
    itimes = [100]

scope.chaninfo = chaninfo
scope.shutters = fakeShutters


#Piezo stage
InitBG('Piezo', '''
from PYME.Acquire.Hardware.Piezos import piezo_e255
scope.piezoz = piezo_e255.piezo_e255('COM2')
scope.piezoz.MoveTo(scope.piezoz.GetChannelObject(), 50.0)
scope.piezos.append((scope.piezoz, scope.piezoz.GetChannelObject(), 'Object'))
''')

InitGUI('''
from PYME.Acquire.Hardware import focusKeys
fk = focusKeys.FocusKeys(MainFrame, menuBar1, scope.piezos[-1])
time1.WantNotification.append(fk.refresh)
''')




#DigiData
#scope.lasers = []
InitBG('Lasers', '''
from PYME.Acquire.Hardware import lasers

pport = lasers.PPort()
scope.l671 = lasers.ParallelSwitchedLaser('671',pport,0)
scope.l488 = lasers.ParallelSwitchedLaser('488',pport,1)

scope.lasers = [scope.l488,scope.l671]
''')

InitGUI('''
if 'lasers'in dir(scope):
    from PYME.Acquire.Hardware import LaserControlFrame
    lcf = LaserControlFrame.LaserControlLight(MainFrame,scope.lasers)
    time1.WantNotification.append(lcf.refresh)
    toolPanels.append((lcf, 'Laser Control'))
''')

#Stepper motor
InitBG('Stepper Motor', '''
from PYME.Acquire.Hardware.Old import SMI1
import wx

scope.step = SMI1.CStepOp()
time1.WantNotification.append(scope.step.ContIO)

mb = wx.MessageDialog(sh.GetParent(), 'Continue with Calibration of stage?\\nPLEASE CHECK that the slide holder has been removed\\n(and then press OK)', 'Stage Callibration', wx.YES_NO|wx.NO_DEFAULT)
ret = mb.ShowModal()
if (ret == wx.ID_YES):
    scope.step.Init(1)
else:
    scope.step.Init(2)

''')


#must be here!!!
joinBGInit() #wait for anyhting which was being done in a separate thread
time.sleep(1)
scope.initDone = True
