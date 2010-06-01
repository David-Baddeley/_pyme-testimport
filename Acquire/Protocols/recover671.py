#!/usr/bin/python

##################
# prebleach671.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

#import all the stuff to make this work
from PYME.Acquire.protocol import *
import numpy

#define a list of tasks, where T(when, what, *args) creates a new task
#when is the frame number, what is a function to be called, and *args are any
#additional arguments
taskList = [
T(-1, scope.turnAllLasersOff),
T(-1, SetEMGain,150),
T(20, scope.filterWheel.fw.setPos, 6),
T(21, scope.l671.TurnOn),
T(40, SetEMGain,0),
T(60, scope.filterWheel.fw.setPos, 1),
T(80, scope.filterWheel.fw.setPos, 6),
T(81, SetEMGain,150),
T(90, MainFrame.pan_spool.OnBAnalyse, None),
T(1500, scope.filterWheel.fw.setPos, 5),
T(1600, scope.filterWheel.fw.setPos, 6),
T(2500, scope.l671.TurnOff),
T(2500, scope.filterWheel.fw.setPos, 3),
T(2501, scope.l671.TurnOn),
T(2600, scope.l671.TurnOff),
T(2600, scope.filterWheel.fw.setPos, 6),
T(2601, scope.l671.TurnOn),
T(3500, scope.filterWheel.fw.setPos, 1),
T(3600, scope.filterWheel.fw.setPos, 6),
T(maxint, scope.turnAllLasersOff),
]

#optional - metadata entries
metaData = [
('Protocol.DarkFrameRange', (0, 20)),
('Protocol.DataStartsAt', 82)
]

#must be defined for protocol to be discovered
PROTOCOL = TaskListProtocol(taskList, metaData)
PROTOCOL_STACK = ZStackTaskListProtocol(taskList, 20, 100, metaData, randomise = False)