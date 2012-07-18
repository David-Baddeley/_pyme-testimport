#!/usr/bin/python

##################
# piezo_e816.py
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

import Mercury as m
import time
import numpy  as np

import threading

class tPoll(threading.Thread):
    def __init__(self, stepper):
        self.stepper = stepper
        self.kill = False
        threading.Thread.__init__(self)
        
    def run(self):
        while not self.kill:
            try:
                self.stepper.RefreshPos()
            except:
                pass
            time.sleep(.02)

class mercuryJoystick:
    def __init__(self, stepper):
        self.stepper = stepper

    def Enable(self, enabled = True):
        if not self.IsEnabled() == enabled:
            self.stepper.SetJoystick(enabled)

    def IsEnabled(self):
        return self.stepper.joystickOn


class mercuryStepper:
    def __init__(self, comPort=5, baud=9600, axes=['A', 'B'], steppers=['M-229.25S', 'M-229.25S']):
        self.axes = axes
        self.steppers = steppers
        self.joystickOn = False

        self.joystick = mercuryJoystick(self)

        self.lock = threading.RLock()
        
        self.lock.acquire()

        #connect to the controller
        self.connID = m.ConnectRS232(comPort, baud)

        if self.connID == -1:
            raise RuntimeError('Could not connect to Mercury controller')

        #tell the controller which stepper motors it's driving
        m.CST(self.connID, ''.join(self.axes), '\n'.join(self.steppers))

        #initialise axes
        m.INI(self.connID, ''.join(self.axes))

        #callibrate axes using reference switch
        m.REF(self.connID, ''.join(self.axes))

        while np.any(m.IsReferencing(self.connID, ''.join(self.axes))):
            time.sleep(.5)

        self.minTravel = m.qTMN(self.connID, ''.join(self.axes))
        self.maxTravel = m.qTMX(self.connID, ''.join(self.axes))

        self.last_poss = m.qPOS(self.connID, ''.join(self.axes))
        self.moving = m.IsMoving(self.connID, ''.join(self.axes))
        self.onTarget = sum(m.qONT(self.connID, ''.join(self.axes))) == len(self.axes)

        self.lock.release()

        self.poll = tPoll(self)
        self.poll.start()

    def SetSoftLimits(self, axis, lims):
        self.lock.acquire()
        m.SPA(self.connID, self.axes[axis], [48, 21], lims, self.steppers[axis])
        self.lock.release()

    def ReInit(self):
        pass 
        
    def MoveTo(self, iChan, fPos, timeout=False):
        self.lock.acquire()
        tgt = fPos
        if (fPos >= self.minTravel[iChan]):
            if (fPos <= self.maxTravel[iChan]):
                tgt = fPos
            else:
                tgt = self.maxTravel[iChan]
        else:
            self.minTravel[iChan]

        self.onTarget = False
        m.MOV(self.connID, self.axes[iChan], [tgt])
        self.last_poss[iChan] = tgt
        self.lock.release()

    def GetPos(self, iChan=0):
        self.lock.acquire()
        ret = m.qPOS(self.connID, self.axes[iChan])[0]
        self.lock.release()
        return ret

    def IsMoving(self, iChan=0):
        self.lock.acquire()
        ret = m.IsMoving(self.connID, self.axes[iChan])[0]
        self.lock.release()
        return ret

    def IsOnTarget(self):
        self.lock.acquire()
        ret = sum(m.qONT(self.connID, ''.join(self.axes))) == len(self.axes)
        self.lock.release()
        return ret

    def RefreshPos(self):
        self.lock.acquire()
        self.last_poss = m.qPOS(self.connID, ''.join(self.axes))
        self.moving = m.IsMoving(self.connID, ''.join(self.axes))
        self.onTarget = sum(m.qONT(self.connID, ''.join(self.axes))) == len(self.axes)
        self.lock.release()

    def GetLastPos(self, iChan=0):
        return self.last_poss[iChan]

    def SetJoystick(self, on = True, chans=[0,1]):
        self.lock.acquire()
        jv = [on for c in chans]
        m.JON(self.connID, [c + 1 for c in chans], jv)
        self.joystickOn = on
        self.lock.release()

    def GetVelocity(self, iChan=0):
        self.lock.acquire()
        ret = m.qVEL(self.connID, self.axes[iChan])[0]
        self.lock.release()
        return ret

    def SetVelocity(self, iChan, velocity):
        self.lock.acquire()
        ret = m.VEL(self.connID, self.axes[iChan], [velocity])
        self.lock.release()
        return ret

    def GetControlReady(self):
        return True
    def GetChannelObject(self):
        return 0
    def GetChannelPhase(self):
        return 1
    def GetMin(self,iChan=0):
        return self.minTravel[iChan]
    def GetMax(self, iChan=0):
        return self.maxTravel[iChan]

    def Cleanup(self):
        self.poll.kill = True
        m.CloseConnection(self.connID)
        

#    def __del__(self):
#        m.CloseConnection(self.connID)
