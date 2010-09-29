#!/usr/bin/python

##################
# protocol.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

from math import floor
import numpy as np
from PYME.Acquire import eventLog

from sys import maxint

#minimal protocol which does nothing
class Protocol:
    def __init__(self):
        pass

    def Init(self, spooler):
        pass
    
    def OnFrame(self, frameNum):
        pass

    def OnFinish(self):
        pass

NullProtocol = Protocol()

class TaskListTask:
    def __init__(self, when, what, *withParams):
        self.when = when
        self.what = what
        self.params = withParams

T = TaskListTask #to save typing in protocols

def Ex(str):
    exec(str)

def SetEMGain(emGain):
    scope.pa.stop()
    scope.cam.SetEMGain(emGain)
    scope.pa.start()

def SetCameraShutter(open):
    scope.pa.stop()
    scope.cam.SetShutter(open)
    scope.pa.start()

class TaskListProtocol(Protocol):
    def __init__(self, taskList, metadataEntries = []):
        self.taskList = taskList
        Protocol.__init__(self)
        self.listPos = 0

        self.metadataEntries = metadataEntries

    def Init(self, spooler):
        self.listPos = 0

        self.OnFrame(-1) #do everything which needs to be done before acquisition starts

        spooler.md.setEntry('Protocol.Filename', self.filename)
        for e in self.metadataEntries:
            spooler.md.setEntry(*e)

    def OnFrame(self, frameNum):
        while not self.listPos >= len(self.taskList) and frameNum >= self.taskList[self.listPos].when:
            t = self.taskList[self.listPos]
            t.what(*t.params)
            eventLog.logEvent('ProtocolTask', '%d, %s, ' % (frameNum, t.what.func_name) + ', '.join(['%s' % p for p in t.params]))
            self.listPos += 1

    def OnFinish(self):
        while not  self.listPos >= len(self.taskList):
            t = self.taskList[self.listPos]
            t.what(*t.params)
            eventLog.logEvent('ProtocolTask', '%s, ' % ( t.what.func_name,) + ', '.join(['%s' % p for p in t.params]))
            self.listPos += 1





class ZStackTaskListProtocol(TaskListProtocol):
    def __init__(self, taskList, startFrame, dwellTime, metadataEntries = [], randomise = False):
        TaskListProtocol.__init__(self, taskList, metadataEntries)
        
        self.startFrame = startFrame
        self.dwellTime = dwellTime
        self.randomise = randomise

    def Init(self, spooler):
        self.zPoss = np.arange(scope.sa.GetStartPos(), scope.sa.GetEndPos()+.95*scope.sa.GetStepSize(),scope.sa.GetStepSize())

        if self.randomise:
            self.zPoss = self.zPoss[np.argsort(np.random.rand(len(self.zPoss)))]

        piezo = scope.sa.piezos[scope.sa.GetScanChannel()]
        self.piezo = piezo[0]
        self.piezoChan = piezo[1]
        self.startPos = self.piezo.GetPos(self.piezoChan)
        self.pos = 0

        spooler.md.setEntry('Protocol.PiezoStartPos', self.piezo.GetPos(self.piezoChan))
        spooler.md.setEntry('Protocol.ZStack', True)

        TaskListProtocol.Init(self,spooler)

    def OnFrame(self, frameNum):
        if frameNum > self.startFrame:
            fn = floor((frameNum - self.startFrame)/self.dwellTime) % len(self.zPoss)
            if not fn == self.pos:
                self.pos = fn
                self.piezo.MoveTo(self.piezoChan, self.zPoss[self.pos])
                eventLog.logEvent('ProtocolFocus', '%d, %3.3f' % (frameNum, self.zPoss[self.pos]))
                
        TaskListProtocol.OnFrame(self, frameNum)

    def OnFinish(self):
        #return piezo to start position
        self.piezo.MoveTo(self.piezoChan, self.startPos)

        TaskListProtocol.OnFinish(self)

NullZProtocol = ZStackTaskListProtocol([], 0, 100)
NullZProtocol.filename = '<none>'