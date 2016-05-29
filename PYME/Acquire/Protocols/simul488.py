#!/usr/bin/python

##################
# standard488.py
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

#import all the stuff to make this work
from PYME.Acquire.protocol import *
import numpy

#define a list of tasks, where T(when, what, *args) creates a new task
#when is the frame number, what is a function to be called, and *args are any
#additional arguments
taskList = [
T(-1, scope.turnAllLasersOff),
#T(20, scope.l488.SetPower, 1000),
#T(20, scope.l405.SetPower, 50),
#T(20, scope.l488.TurnOn),
#T(20, scope.l405.TurnOn),
T(20, scope.state.update, {'Lasers.l488.Power' : 1000, 'Lasers.l405.Power' : 50, 
                           'Lasers.l488.On' : True, 'Lasers.l405.On' : True}),
T(30, MainFrame.pan_spool.OnBAnalyse, None)
]

#optional - metadata entries
metaData = [
('Protocol.DarkFrameRange', (0, 20)),
('Protocol.DataStartsAt', 21)
]

#optional - pre-flight check
#a list of checks which should be performed prior to launching the protocol
#syntax: C(expression to evaluate (quoted, should have boolean return), message to display on failure),
preflight = [
#C('scope.cam.GetEMGain() == 150', 'Was expecting an intial e.m. gain of 150'),
#C('scope.cam.GetROIX1() > 0', 'Looks like no ROI has been set'),
#C('scope.cam.GetIntegTime() <= 50', 'Camera integration time may be too long'),
]

#must be defined for protocol to be discovered
PROTOCOL = TaskListProtocol(taskList, metaData, preflight)
PROTOCOL_STACK = ZStackTaskListProtocol(taskList, 20, 100, metaData, preflight, randomise = False)
