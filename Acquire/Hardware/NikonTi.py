#!/usr/bin/python

##################
# NikonTi.py
#
# Copyright David Baddeley, 2011
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

# NB Possibly covered by NDA

#import serial;
#import time
import win32com.client
nik = win32com.client.Dispatch("Nikon.TiScope.NikonTi")
# connect to the real hardware (device 0 is simulated)
nik.Device = nik.Devices(1)

#from math import *
from PYME.Acquire import eventLog

class zDrive:
    def __init__(self, maxtravel = 4500000):
        #nik = win32com.client.Dispatch("Nikon.TiScope.NikonTi")
        # connect to the real hardware (device 0 is simulated)
        #nik.Device = nik.Devices(1)
        
        self.stepsize =  nik.zDrive.Resolution()
        self.hardMin = nik.ZDrive.Position.RangeLowerLimit
        self.hardMax = nik.ZDrive.Position.RangeHigherLimit
        self.max_travel = min(maxtravel, self.hardMax*self.stepsize)
        self.minorTick = self.stepsize*100 #set the slider tick length
        
    def MoveTo(self, iChannel, fPos, bTimeOut=True):
        stepPos = round(fPos/self.stepsize)
        print stepPos
        if (stepPos >= self.hardMin):
            if (fPos < self.max_travel):
                nik.ZDrive.Position = int(stepPos)
            else:
                 nik.ZDrive.Position = int(round(self.max_travel/self.stepsize))
        else:
            nik.ZDrive.Position = self.hardMin
            
        eventLog.logEvent('Focus Change', 'New z-pos = %f' % stepPos)
    def GetPos(self, iChannel=1):
        return nik.ZDrive.Position()*self.stepsize
    def GetControlReady(self):
        return True
    def GetChannelObject(self):
        return 1
    def GetChannelPhase(self):
        return 1
    def GetMin(self,iChan=1):
        return self.hardMin*self.stepsize
        #return 3500
    #return round((self.GetPos() - 50)/50)*50
    
    def GetMax(self, iChan=1):
        return self.max_travel
    #return round((self.GetPos() + 50)/50)*50
 
class FilterChanger:
    def __init__(self):
        self.names = [b.Name for b in nik.FilterBlockCassette1.FilterBlocks]
    
    def GetPosition(self):
        #convert to zero based indices for python consistency
        return int(nik.FilterBlockCassette1.Position) - 1
        
    def GetFilter(self):
        return self.names[self.GetPosition()]
        
    def SetPosition(self, pos):
        nik.FilterBlockCassette1.Position = (pos + 1)
        
    def SetFilter(self, filterName):
        self.SetPosition(self.names.index(filterName))
        
    def ProvideMetadata(self,mdh):
        mdh.setEntry('NikonTi.FilterCube', self.GetFilter())
         
         
class LightPath:
    def __init__(self, names = ['EYE', 'L100', 'R100', 'L80']):
        self.names = names
        
    def SetPosition(self, pos):
        nik.LightPathDrive.Position = (pos + 1)
        
    def GetPosition(self):
        return int(nik.LightPathDrive.Position) - 1
        
    def SetPort(self, port):
        self.SetPositon(self.names.index(port))
        
    def GetPort(self):
        return self.names[self.GetPosition()]
    
    def ProvideMetadata(self,mdh):
        mdh.setEntry('NikonTi.LightPath', self.GetPort())
        


if __name__ == '__main__':
    import Pyro.core
    import Pyro.naming
    import os
    import sys
    
    Pyro.config.PYRO_MULTITHREADED = 0
    
    if sys.platform == 'win32':
        computername = os.environ['COMPUTERNAME']
    else:
        computername = os.uname()[1]

    class RemoteZDrive(zDrive, Pyro.core.ObjBase):
        def __init__(self):
            zDrive.__init__(self)
            Pyro.core.ObjBase.__init__(self)
            
    class RemoteFilterChanger(FilterChanger, Pyro.core.ObjBase):
        def __init__(self):
            FilterChanger.__init__(self)
            Pyro.core.ObjBase.__init__(self)
            
    class RemoteLightPath(LightPath, Pyro.core.ObjBase):
        def __init__(self):
            LightPath.__init__(self)
            Pyro.core.ObjBase.__init__(self)

    Pyro.config.PYRO_MOBILE_CODE = 1
    Pyro.core.initServer()
    ns=Pyro.naming.NameServerLocator().getNS()
    daemon=Pyro.core.Daemon()
    daemon.useNameServer(ns)
    
    print ns.list('')

    if not computername in [n[0] for n in ns.list('')]:    
        ns.createGroup(computername)
    
    #get rid of any previous objects
    for name in [".ZDrive", ".FilterChanger", ".LightPath"]:
        try:
            ns.unregister(computername + name)
        except Pyro.errors.NamingError:
            pass

    zd = RemoteZDrive()
    uri=daemon.connect(zd, computername +".ZDrive")
    
    fc = RemoteFilterChanger()
    uri=daemon.connect(fc, computername +".FilterChanger")
    
    lp = RemoteLightPath()
    uri=daemon.connect(lp, computername +".LightPath")

    try:
        daemon.requestLoop()
    finally:
        daemon.shutdown(True)
        
        
