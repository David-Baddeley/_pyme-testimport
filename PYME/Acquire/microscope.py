#!/usr/bin/python

##################
# funcs.py
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

#!/usr/bin/python
#import sys
#sys.path.append(".")

import wx
#from PYME.Acquire import previewaquisator as previewaquisator
from PYME.Acquire.frameWrangler import FrameWrangler

import PYME.Acquire.protocol as protocol

from PYME.io import MetaDataHandler
from PYME.Acquire.Hardware import ccdCalibrator

import sqlite3

import os
import datetime

import warnings

#register handlers for ndarrays
from PYME.misc import sqlitendarray

#class DummyJoystick(object):
#    def enable(*args, **kwargs):
#        pass

class microscope(object):
    def __init__(self):
        #list of tuples  of form (class, chan, name) describing the instaled piezo channels
        self.piezos = []
        self.hardwareChecks = []
        
        #entries should be of the form: "x" : (piezo, channel, multiplier)
        # where multiplyier is what to multiply by to get the usints to um
        self.positioning = {}
        self.joystick = None

        self.cameras = {}
        self.camControls = {}

        self.stackNum = 0

        #self.WantEventNotification = []
 
        self.StatusCallbacks = [] #list of functions which provide status information
        self.CleanupFunctions = [] #list of functions to be called at exit
        self.PACallbacks = [] #list of functions to be called when a new aquisator is created
        #preview
        self.saturationThreshold = 16383 #14 bit
        self.lastFrameSaturated = False
        #self.cam.saturationIntervened = False
        self.saturatedMessage = ''

        protocol.scope = self
        ccdCalibrator.setScope(self)
        self.initDone = False

        self._OpenSettingsDB()

        MetaDataHandler.provideStartMetadata.append(self.GenStartMetadata)
        
        #provision to set global metadata values in startup script
        self.mdh = MetaDataHandler.NestedClassMDHandler()
        
    def EnableJoystick(self, enable=True):
        if not self.joystick is None:
            self.joystick.Enable(enable)
        
    def GetPos(self):
        res = {}
        for k in self.positioning.keys():
            p, c, m = self.positioning[k]
            res[k] = p.GetPos(c)*m
            
        return res
        
    def SetPos(self, **kwargs):
        for k, v in kwargs.items():
            p, c, m = self.positioning[k]
            p.MoveTo(c, v/m)
            
    def GetPosRange(self):
        res = {}
        for k in self.positioning.keys():
            p, c, m = self.positioning[k]
            if m > 0: 
                res[k] = (p.GetMin(c)*m,p.GetMax(c)*m)
            else:
                res[k] = (p.GetMax(c)*m,p.GetMin(c)*m)

        return res
        

    def _OpenSettingsDB(self):
        #create =  not os.path.exists('PYMESettings.db')
        fstub = os.path.split(__file__)[0]
        dbfname = os.path.join(fstub, 'PYMESettings.db')

        self.settingsDB = sqlite3.connect(dbfname, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.settingsDB.isolation_level = None

        tableNames = [a[0] for a in self.settingsDB.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()]

        if not 'CCDCalibration2' in tableNames:
            self.settingsDB.execute("CREATE TABLE CCDCalibration2 (time timestamp, temperature integer, serial integer, nominalGains ndarray, trueGains ndarray)")
        if not 'VoxelSizes' in tableNames:
            self.settingsDB.execute("CREATE TABLE VoxelSizes (ID INTEGER PRIMARY KEY, x REAL, y REAL, name TEXT)")
        if not 'VoxelSizeHistory2' in tableNames:
            self.settingsDB.execute("CREATE TABLE VoxelSizeHistory2 (time timestamp, sizeID INTEGER, camSerial INTEGER)")
        if not 'StartupTimes' in tableNames:
            self.settingsDB.execute("CREATE TABLE StartupTimes (component TEXT, time REAL)")
            self.settingsDB.execute("INSERT INTO StartupTimes VALUES ('total', 5)")
            
        self.settingsDB.commit()

    def GetPixelSize(self):
        currVoxelSizeID = self.settingsDB.execute("SELECT sizeID FROM VoxelSizeHistory2 WHERE camSerial=? ORDER BY time DESC", (self.cam.GetSerialNumber(),)).fetchone()
        if not currVoxelSizeID == None:
            return self.settingsDB.execute("SELECT x,y FROM VoxelSizes WHERE ID=?", currVoxelSizeID).fetchone()

    def GenStartMetadata(self, mdh):
        try:
            voxx, voxy = self.GetPixelSize()
            mdh.setEntry('voxelsize.x', voxx)
            mdh.setEntry('voxelsize.y', voxy)
            mdh.setEntry('voxelsize.units', 'um')
        except TypeError:
            pass

        for p in self.piezos:
            mdh.setEntry('Positioning.%s' % p[2].replace(' ', '_').replace('-', '_'), p[0].GetPos(p[1]))
            
        for k, v in self.GetPos().items():
            mdh.setEntry('Positioning.%s' % k.replace(' ', '_').replace('-', '_'), v)
        
        try:
            mdh['CameraOrientation.Rotate'] = self.cam.orientation['rotate']
            mdh['CameraOrientation.FlipX'] = self.cam.orientation['flipx']
            mdh['CameraOrientation.FlipY'] = self.cam.orientation['flipy']
        except AttributeError:
            pass
            
        mdh.copyEntriesFrom(self.mdh)

    def AddVoxelSizeSetting(self, name, x, y):
        self.settingsDB.execute("INSERT INTO VoxelSizes (name, x, y) VALUES (?, ?, ?)", (name, x, y))
        self.settingsDB.commit()
        

    def SetVoxelSize(self, voxelsizename, camName=None):
        if camName == None:
            cam = self.cam
        else:
            cam = self.cameras[camName]
            
        voxelSizeID = self.settingsDB.execute("SELECT ID FROM VoxelSizes WHERE name=?", (voxelsizename,)).fetchone()[0]
        self.settingsDB.execute("INSERT INTO VoxelSizeHistory2 VALUES (?, ?, ?)", (datetime.datetime.now(), voxelSizeID, cam.GetSerialNumber()))
        self.settingsDB.commit()


    def satCheck(self, source): # check for saturation
        if not 'shutterOpen' in dir(self.cam):
            return
        im = source.dsa
        IMax = im.max()

        if not self.cam.shutterOpen:
            self.cam.ADOffset = im.mean()
        elif (IMax >= self.cam.SaturationThreshold): #is saturated

            source.cam.StopAq()

            if self.lastFrameSaturated: #last frame was also saturated - our intervention obviously didn't work - close the shutter
                if 'SetShutter' in dir(source.cam):
                    source.cam.SetShutter(False)
                source.cam.StartExposure()
                self.saturatedMessage = 'Camera shutter has been closed'
                self.lastFrameSaturated = True
                self.cam.saturationIntervened = True
                wx.MessageBox(self.saturatedMessage, "Saturation detected", wx.OK|wx.ICON_HAND)
                return

            #fracPixelsSat = (im > self.saturationThreshold).sum().astype('f')/im.size

            #try turning the e.m. gain off
            if 'SetEMGain' in dir(source.cam) and not source.cam.GetEMGain() == 0:
                self.oldEMGain = source.cam.GetEMGain()
                source.cam.SetEMGain(0)
                if self.oldEMGain  < 50: #poor chance of resolving by turning EMGain down alone
                    if 'SetShutter' in dir(source.cam):
                        source.cam.SetShutter(False)
                        self.saturatedMessage = 'Camera shutter closed'
                else:
                    self.saturatedMessage = 'EM Gain turned down'
                    
                source.cam.StartExposure()

                self.lastFrameSaturated = True
                self.cam.saturationIntervened = True
                wx.MessageBox(self.saturatedMessage, "Saturation detected", wx.OK|wx.ICON_HAND)
                return
            else:
                if 'SetShutter' in dir(source.cam):
                    source.cam.SetShutter(False)
                source.cam.StartExposure()
                self.saturatedMessage = 'Camera shutter closed'
                self.lastFrameSaturated = True
                self.cam.saturationIntervened = True
                wx.MessageBox(self.saturatedMessage, "Saturation detected", wx.OK|wx.ICON_HAND)
                return

            self.lastFrameSaturated = True

        else:
            self.lastFrameSaturated = False


    def genStatus(self):
        stext = ''
        if self.cam.CamReady():
            self.cam.GetStatus()
            stext = 'CCD Temp: %d' % self.cam.GetCCDTemp()
        else:
            stext = '<Camera ERROR>'
        if 'saturationIntervened' in dir(self.cam):
            if self.lastFrameSaturated:
                stext = stext + '    Camera Saturated!!'
            if self.cam.saturationIntervened:
                stext = stext + '    ' + self.saturatedMessage
        if 'step' in dir(self):
            stext = stext + '   Stepper: (XPos: %1.2f  YPos: %1.2f  ZPos: %1.2f)' % (self.step.GetPosX(), self.step.GetPosY(), self.step.GetPosZ())
        if self.frameWrangler.isRunning():
            if 'GetFPS' in dir(self.cam):
                stext = stext + '    FPS = (%2.2f/%2.2f)' % (self.cam.GetFPS(),self.frameWrangler.getFPS())
            else:
                stext = stext + '    FPS = %2.2f' % self.frameWrangler.getFPS()

            if 'GetNumImsBuffered' in dir(self.cam):
				stext = stext + '    Buffer Level: %d of %d' % (self.cam.GetNumImsBuffered(), self.cam.GetBufferSize())
        
        for sic in self.StatusCallbacks:
                stext = stext + '    ' + sic()       
        return stext

    @property
    def pa(self):
        '''property to catch access of what was previously called the scope.frameWrangler (the PreviewAcquisator)'''
        warnings.warn(".pa is deprecated, please use .frameWrangler instead", DeprecationWarning)
        return self.frameWrangler
    
    def startAquisistion(self):
        #stop an old acquisition
        try:
            self.frameWrangler.stop()
        except AttributeError:
            pass
        
        #self.pa = previewaquisator.PreviewAquisator(self.chaninfo,self.cam, self.shutters)
        self.frameWrangler = FrameWrangler(self.cam)
        self.frameWrangler.HardwareChecks.extend(self.hardwareChecks)
        self.frameWrangler.Prepare()

        if 'shutterOpen' in dir(self.cam):
            #self.pa.WantFrameGroupNotification.append(self.satCheck)
            self.frameWrangler.onFrameGroup.connect(self.satCheck)
            
        self.frameWrangler.start()
        
        for cb in self.PACallbacks:
            cb()

    def SetCamera(self, camName):
        try:
            self.frameWrangler.stop()
        except AttributeError:
            pass

        #deactivate cameras
        for c in self.cameras.values():
            c.SetActive(False)
            c.SetShutter(False)
            
        for k in self.cameras.keys():
            self.camControls[k].GetParent().Hide()#GetParent().UnPin()
        
        self.cam = self.cameras[camName]
        if 'lightpath' in dir(self):
            self.lightpath.SetPort(self.cam.port)
        
        self.cam.SetActive(True)
        try:
            self.cam.SetShutter(self.camControls[camName].cbShutter.GetValue())
        except AttributeError:
            pass #for cameras which don't have a shutter
        
        self.camControls[camName].GetParent().Show()#GetParent().PinOpen()
        self.camControls[camName].GetParent().GetParent().Layout()

        try:
            self.frameWrangler.cam = self.cam
            self.frameWrangler.Prepare()
            
            self.frameWrangler.start()
        except AttributeError:
            pass
            
            
        
            
    def centreView(self, dx, dy):
        vx, vy = self.GetPixelSize()
        
        p = self.GetPos()
        
        ox = p['x']
        oy = p['y']
        
        if 'orientation' in dir(self.cam):
            if self.cam.orientation['rotate']:
                dx, dy = dy, dx
                
            if self.cam.orientation['flipx']:
                dx *= -1
                
            if self.cam.orientation['flipy']:
                dy *= -1
        
        self.SetPos(x=(ox + dx*vx), y=(oy + dy*vy))


    def turnAllLasersOff(self):
        for l in self.lasers:
            l.TurnOff()

    def __del__(self):
        self.settingsDB.close()
