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

import serial
import time

from .base_piezo import PiezoBase

import logging
logger = logging.getLogger(__name__)

#C867 controller for PiLine piezo linear motor stages
#NB units are mm not um as for piezos

class piezo_c867(PiezoBase):
    units_um = 1000
    gui_description = 'Stage %s'
    
    def __init__(self, portname='COM1', maxtravel = 25.00, hasTrigger=False, reference=True):
        self.max_travel = maxtravel
        
        self.ser_port = serial.Serial(portname, 38400, timeout=.1, writeTimeout=.1)
        
        #turn servo mode on
        self.ser_port.write('SVO 1 1\n')
        self.ser_port.write('SVO 2 1\n')
        
        if reference:
            #find reference switch (should be in centre of range)
            self.ser_port.write('FRF\n')
        
        #self.lastPos = self.GetPos()
        #self.lastPos = [self.GetPos(1), self.GetPos(2)]

        #self.driftCompensation = False
        self.hasTrigger = hasTrigger
        
    def SetServo(self, state=1):
        self.ser_port.write('SVO 1 %d\n' % state)
        self.ser_port.write('SVO 2 %d\n' % state)

    def ReInit(self, reference=True):
        #self.ser_port.write('WTO A0\n')
        self.ser_port.write('SVO 1 1\n')
        self.ser_port.write('SVO 2 1\n')
        
        if reference:
            #find reference switch (should be in centre of range)
            self.ser_port.write('FRF\n')
        
        #self.lastPos = [self.GetPos(1), self.GetPos(2)]
        
    def SetVelocity(self, chan, vel):
        self.ser_port.write('VEL %d %3.4f\n' % (chan, vel))
        #self.ser_port.write('VEL 2 %3.4f\n' % vel)
        
    def GetVelocity(self, chan):
        self.ser_port.flushInput()
        self.ser_port.flushOutput()
        self.ser_port.write('VEL?\n')
        self.ser_port.flushOutput()
        #time.sleep(0.005)
        res = self.ser_port.readline()
        #res = self.ser_port.readline()
        print(res)
        return float(res) 
        
        
    def MoveTo(self, iChannel, fPos, bTimeOut=True):
        if (fPos >= 0):
            if (fPos <= self.max_travel):
                self.ser_port.write('MOV %d %3.6f\n' % (iChannel, fPos))
                #self.lastPos[iChannel-1] = fPos
            else:
                self.ser_port.write('MOV %d %3.6f\n' % (iChannel, self.max_travel))
                #self.lastPos[iChannel-1] = self.max_travel
        else:
            self.ser_port.write('MOV %d %3.6f\n' % (iChannel, 0.0))
            #self.lastPos[iChannel-1] = 0.0
            
    def MoveRel(self, iChannel, incr, bTimeOut=True):
            self.ser_port.write('MVR %d %3.6f\n' % (iChannel, incr))
            
            
    def MoveToXY(self, xPos, yPos, bTimeOut=True):
        xPos = min(max(xPos, 0),self.max_travel)
        yPos = min(max(yPos, 0),self.max_travel)
        
        self.ser_port.write('MOV 1 %3.6f 2 %3.6f\n' % (xPos, yPos))
        #self.lastPos = [self.GetPos(1), self.GetPos(2)]
        #self.lastPos = fPos
            

    def GetPos(self, iChannel=0):
        #self.ser_port.flush()
        #time.sleep(0.005)
        #self.ser_port.write('POS? %d\n' % iChannel)
        #self.ser_port.flushOutput()
        #time.sleep(0.005)
        #res = self.ser_port.readline()
        pos = self.GetPosXY()
        
        return pos[iChannel-1]
        
    def GetPosXY(self):
        self.ser_port.flushInput()
        self.ser_port.flushOutput()
        #time.sleep(0.005)
        self.ser_port.write('POS? 1 2\n')
        self.ser_port.flushOutput()
        #time.sleep(0.005)
        res1 = self.ser_port.readline()
        res2 = self.ser_port.readline()
        print((res1, res2))
        return float(res1.split('=')[1]), float(res2.split('=')[1])


    
    def GetControlReady(self):
        return True
    def GetChannelObject(self):
        return 1
    def GetChannelPhase(self):
        return 2
    def GetMin(self,iChan=1):
        return 0
    def GetMax(self, iChan=1):
        return self.max_travel
        
    def GetFirmwareVersion(self):
        import re
        self.ser_port.write('*IDN?\n')
        self.ser_port.flush()
        
        verstring = self.ser_port.readline()
        return float(re.findall(r'V(\d\.\d\d)', verstring)[0])
        
import threading
#import Queue
import numpy as np
        
class piezo_c867T(PiezoBase):
    units_um = 1000
    gui_description = 'Stage %s'
    
    def __init__(self, portname='COM1', maxtravel = 25.00, hasTrigger=False, reference=True, maxvelocity=200., validRegion = [[4.5, 19], [0, 25]]):
        self.max_travel = maxtravel
        self.maxvelocity = maxvelocity
        self.ser_port = serial.Serial(portname, 38400, timeout=.1, writeTimeout=.1)
        
        self.units = 'mm'
        
        self.validRegion=validRegion
        self.onTarget = False
        self.ptol = 5e-4
        
        #reboot stage
        self.ser_port.write('RBT\n')
        time.sleep(1)
        #try to make motion smooth
        self.ser_port.write('SPA 1 0x4D 2\n')
        self.ser_port.write('SPA 2 0x4D 2\n')
        #turn servo mode on
        self.ser_port.write('SVO 1 1\n')
        self.ser_port.write('SVO 2 1\n')
        
        self.servo = True
        self.onTarget = False
        self.onTargetLast = False
        
        self.errCode = 0
        
        if reference:
            #find reference switch (should be in centre of range)
            self.ser_port.write('FRF\n')
        
            time.sleep(.5)        
        #self.lastPos = self.GetPos()
        #self.lastPos = [self.GetPos(1), self.GetPos(2)]

        #self.driftCompensation = False
        self.hasTrigger = hasTrigger
        self.loopActive = True
        self.stopMove = False
        self.position = np.array([12.5,12.5])
        self.velocity = np.array([self.maxvelocity, self.maxvelocity])
        
        self.targetPosition = np.array([12.5, 12.5])
        self.targetVelocity = self.velocity.copy()
        
        self.lastTargetPosition = self.position.copy()
        
        self.lock = threading.Lock()
        self.tloop = threading.Thread(target=self._Loop)
        self.tloop.start()
        
    def _Loop(self):
        while self.loopActive:
            self.lock.acquire()
            try:
                self.ser_port.flushInput()
                self.ser_port.flushOutput()
            
                #check position
                self.ser_port.write('POS? 1 2\n')
                self.ser_port.flushOutput()
                #time.sleep(0.005)
                res1 = self.ser_port.readline()
                res2 = self.ser_port.readline()
                #print res1, res2
                self.position[0] = float(res1.split('=')[1])
                self.position[1] = float(res2.split('=')[1])
                
                self.ser_port.write('ERR?\n')
                self.ser_port.flushOutput()
                self.errCode = int(self.ser_port.readline())
                
                if not self.errCode == 0:
                    #print(('Stage Error: %d' %self.errCode))
                    logger.error('Stage Error: %d' %self.errCode)
                
                #print self.targetPosition, self.stopMove
                
                if self.stopMove:
                    self.ser_port.write('HLT\n')
                    time.sleep(.1)
                    self.ser_port.write('POS? 1 2\n')
                    self.ser_port.flushOutput()
                    #time.sleep(0.005)
                    res1 = self.ser_port.readline()
                    res2 = self.ser_port.readline()
                    #print res1, res2
                    self.position[0] = float(res1.split('=')[1])
                    self.position[1] = float(res2.split('=')[1])
                    self.targetPosition[:] = self.position[:]
                    self.stopMove = False
                    
                
                if self.servo:
                    if not np.all(self.velocity == self.targetVelocity):
                        for i, vel in enumerate(self.targetVelocity):
                            self.ser_port.write('VEL %d %3.9f\n' % (i+1, vel))
                        self.velocity = self.targetVelocity.copy()
                        #print('v')
                        logger.debug('Setting stage target vel: %s' % self.targetVelocity)
                    
                    #if not np.all(self.targetPosition == self.lastTargetPosition):
                    if not np.allclose(self.position, self.targetPosition, atol=self.ptol):
                        #update our target position
                        pos = np.clip(self.targetPosition, 0,self.max_travel)
            
                        self.ser_port.write('MOV 1 %3.9f 2 %3.9f\n' % (pos[0], pos[1]))
                        self.lastTargetPosition = pos.copy()
                        #print('p')
                        logger.debug('Setting stage target pos: %s' % pos)
                        time.sleep(.01)
                    
                #check to see if we're on target
                self.ser_port.write('ONT?\n')
                self.ser_port.flushOutput()
                time.sleep(0.005)
                res1 = self.ser_port.readline()
                ont1 = int(res1.split('=')[1]) == 1
                res1 = self.ser_port.readline()
                ont2 = int(res1.split('=')[1]) == 1
                
                onT = (ont1 and ont2) or (self.servo == False)
                self.onTarget = onT and self.onTargetLast
                self.onTargetLast = onT
                self.onTarget = np.allclose(self.position, self.targetPosition, atol=self.ptol)
                    
                #time.sleep(.1)
                
            except serial.SerialTimeoutException:
                #print('Serial Timeout')
                logger.debug('Serial Timeout')
                pass
            finally:
                self.stopMove = False
                self.lock.release()
                
        #close port on loop exit
        self.ser_port.close()
        logger.info("Stage serial port closed")
                
    def close(self):
        logger.info("Shutting down XY Stage")
        with self.lock:
            self.loopActive = False
            #time.sleep(.01)
            #self.ser_port.close()            
                
        
    def SetServo(self, state=1):
        self.lock.acquire()
        try:
            self.ser_port.write('SVO 1 %d\n' % state)
            self.ser_port.write('SVO 2 %d\n' % state)
            self.servo = state == 1
        finally:
            self.lock.release()
            
#    def SetParameter(self, paramID, state):
#        self.lock.acquire()
#        try:
#            self.ser_port.write('SVO 1 %d\n' % state)
#            self.ser_port.write('SVO 2 %d\n' % state)
#            self.servo = state == 1
#        finally:
#            self.lock.release()

    def ReInit(self, reference=True):
        #self.ser_port.write('WTO A0\n')
        self.lock.acquire()
        try:
            self.ser_port.write('RBT\n')
            time.sleep(1)
            self.ser_port.write('SVO 1 1\n')
            self.ser_port.write('SVO 2 1\n')
            self.servo = True
        
            if reference:
            #find reference switch (should be in centre of range)
               self.ser_port.write('FRF\n')
             
            time.sleep(1)
            self.stopMove = True
        finally:
            self.lock.release()
        
        #self.lastPos = [self.GetPos(1), self.GetPos(2)]
        
    def SetVelocity(self, chan, vel):
        #self.ser_port.write('VEL %d %3.4f\n' % (chan, vel))
        #self.ser_port.write('VEL 2 %3.4f\n' % vel)
        self.targetVelocity[chan-1] = vel
        
    def GetVelocity(self, chan):
        return self.velocity[chan-1]
        
    def MoveTo(self, iChannel, fPos, bTimeOut=True, vel=None):
        chan = iChannel - 1
        if vel is None:
            vel = self.maxvelocity
        self.targetVelocity[chan] = vel
        self.targetPosition[chan] = min(max(fPos, self.validRegion[chan][0]),self.validRegion[chan][1]) 
        self.onTarget = False
            
    #def MoveRel(self, iChannel, incr, bTimeOut=True):
    #        self.ser_port.write('MVR %d %3.6f\n' % (iChannel, incr))
            
            
    def MoveToXY(self, xPos, yPos, bTimeOut=True, vel=None):
        if vel is None:
            vel = self.maxvelocity
        self.targetPosition[0] = min(max(xPos, self.validRegion[0][0]),self.validRegion[0][1])
        self.targetPosition[1] = min(max(yPos, self.validRegion[1][0]),self.validRegion[1][1])
        self.targetVelocity[:] = vel
        self.onTarget = False
            

    def GetPos(self, iChannel=0):
        #self.ser_port.flush()
        #time.sleep(0.005)
        #self.ser_port.write('POS? %d\n' % iChannel)
        #self.ser_port.flushOutput()
        #time.sleep(0.005)
        #res = self.ser_port.readline()
        pos = self.GetPosXY()
        
        return pos[iChannel-1]
        
    def GetPosXY(self):
        return self.position

    def MoveInDir(self, dx, dy, th=.0000):
        self.targetVelocity[0] = abs(dx)*self.maxvelocity
        self.targetVelocity[1] = abs(dy)*self.maxvelocity
        
        logger.debug('md %f,%f' % (dx, dy))
        
        if dx > th:
            self.targetPosition[0] = min(max(np.round(self.position[0]+1), self.validRegion[0][0]),self.validRegion[0][1])
        elif dx < -th:
            self.targetPosition[0] = min(max(np.round(self.position[0]-1), self.validRegion[0][0]),self.validRegion[0][1])
        else:
            self.targetPosition[0] = min(max(self.position[0], self.validRegion[0][0]),self.validRegion[0][1])
            
        if dy > th:
            self.targetPosition[1] = min(max(np.round(self.position[1]+1), self.validRegion[1][0]),self.validRegion[1][1])
        elif dy < -th:
            self.targetPosition[1] = min(max(np.round(self.position[1]-1), self.validRegion[1][0]),self.validRegion[1][1])
        else:
            self.targetPosition[1] = min(max(self.position[1], self.validRegion[1][0]),self.validRegion[1][1])
            
        self.onTarget = False
            
    def StopMove(self):
        self.stopMove = True
    
    def GetControlReady(self):
        return True
    def GetChannelObject(self):
        return 1
    def GetChannelPhase(self):
        return 2
    def GetMin(self,iChan=1):
        return 0
    def GetMax(self, iChan=1):
        return self.max_travel
        
    def OnTarget(self):
        return self.onTarget
        
    def GetFirmwareVersion(self):
        import re
        self.ser_port.write('*IDN?\n')
        self.ser_port.flush()
        
        verstring = self.ser_port.readline()
        return float(re.findall(r'V(\d\.\d\d)', verstring)[0])

        
class c867Joystick:
    def __init__(self, stepper):
        self.stepper = stepper

    def Enable(self, enabled = True):
        if not self.IsEnabled() == enabled:
            self.stepper.SetServo(enabled)

    def IsEnabled(self):
        return self.stepper.servo
     
        
