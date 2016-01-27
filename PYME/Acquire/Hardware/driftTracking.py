# -*- coding: utf-8 -*-
"""
Created on Fri Mar 28 15:02:50 2014

@author: David Baddeley
"""

import numpy as np
from pylab import fftn, ifftn, fftshift, ifftshift
import time
from scipy import ndimage

def correlateFrames(A, B):
    A = A.squeeze()/A.mean() - 1
    B = B.squeeze()/B.mean() - 1
    
    X, Y = np.mgrid[0.0:A.shape[0], 0.0:A.shape[1]]
    
    C = ifftshift(np.abs(ifftn(fftn(A)*ifftn(B))))
    
    Cm = C.max()    
    
    Cp = np.maximum(C - 0.5*Cm, 0)
    Cpsum = Cp.sum()
    
    x0 = (X*Cp).sum()/Cpsum
    y0 = (Y*Cp).sum()/Cpsum
    
    return x0 - A.shape[0]/2, y0 - A.shape[1]/2, Cm, Cpsum
    
    
def correlateAndCompareFrames(A, B):
    A = A.squeeze()/A.mean() - 1
    B = B.squeeze()/B.mean() - 1
    
    X, Y = np.mgrid[0.0:A.shape[0], 0.0:A.shape[1]]
    
    C = ifftshift(np.abs(ifftn(fftn(A)*ifftn(B))))
    
    Cm = C.max()    
    
    Cp = np.maximum(C - 0.5*Cm, 0)
    Cpsum = Cp.sum()
    
    x0 = (X*Cp).sum()/Cpsum
    y0 = (Y*Cp).sum()/Cpsum
    
    dx, dy = x0 - A.shape[0]/2, y0 - A.shape[1]/2
    
    As = ndimage.shift(A, [-dx, -dy])
    
    #print A.shape, As.shape
    
    return (As -B).mean(), dx, dy
    
    
class correlator(object):
    def __init__(self, scope, piezo=None):
        self.scope = scope
        self.piezo = piezo
        
        self.focusTolerance = .05 #how far focus can drift before we correct
        self.deltaZ = 0.2 #z increment used for calibration
        self.stackHalfSize = 10
        self.NCalibStates = 2*self.stackHalfSize + 1
        #self.initialise()
        
    def initialise(self):
        d = 1.0*self.scope.pa.dsa.squeeze()        
        
        self.X, self.Y = np.mgrid[0.0:d.shape[0], 0.0:d.shape[1]]
        self.X -= d.shape[0]/2
        self.Y -= d.shape[1]/2
        
        #we want to discard edges after accounting for x-y drift
        self.mask = np.ones_like(d)
        self.mask[:10, :] = 0
        self.mask[-10:, :] = 0
        self.mask[:, :10] = 0
        self.mask[:,-10:] = 0
        
        self.calibState = 0 #completely uncalibrated
        
        self.corrRef = 0

        
        self.lockFocus = False
        self.logShifts = True
        self.lastAdjustment = 5 
        self.homePos = self.piezo.GetPos(0)
        
        
        self.history = []
        
        self.historyCorrections = []

        
    def setRefA(self):
        d = 1.0*self.scope.pa.dsa.squeeze()
        self.refA = d/d.mean() - 1        
        self.FA = ifftn(self.refA)
        self.refA *= self.mask
        
    def setRefB(self):
        d = 1.0*self.scope.pa.dsa.squeeze()
        self.refB = d/d.mean() - 1
        self.refB *= self.mask        
        
    def setRefC(self):
        d = 1.0*self.scope.pa.dsa.squeeze()
        self.refC = d/d.mean() - 1
        self.refC *= self.mask
        
        self.dz = (self.refC - self.refB).ravel()
        self.dzn = 2./np.dot(self.dz, self.dz)
        
    def setRefN(self, N):
        d = 1.0*self.scope.pa.dsa.squeeze()
        ref = d/d.mean() - 1        
        self.calFTs[:,:,N] = ifftn(ref)
        self.calImages[:,:,N] = ref*self.mask
    #def setRefD(self):
    #    self.refD = (1.0*self.d).squeeze()/self.d.mean() - 1 
    #    self.refD *= self.mask
        
        #self.dz = (self.refC - self.refA).ravel()
        
        
    def compare(self):
        d = 1.0*self.scope.pa.dsa.squeeze()
        dm = d/d.mean() - 1
        
        #where is the piezo suppposed to be
        nomPos = self.piezo.GetPos(0)
        
        #find closest calibration position
        posInd = np.argmin(np.abs(nomPos - self.calPositions))
        
        #retrieve calibration information at this location        
        calPos = self.calPositions[posInd]
        FA = self.calFTs[:,:,posInd]
        refA = self.calImages[:,:,posInd] 

        ddz = self.dz[:,posInd]
        dzn = self.dzn[posInd]
        
        #what is the offset between our target position and the calibration position         
        posDelta = nomPos - calPos
        
        print nomPos, posInd, calPos, posDelta
        
        #find x-y drift
        C = ifftshift(np.abs(ifftn(fftn(dm)*FA)))
        
        Cm = C.max()    
        
        Cp = np.maximum(C - 0.5*Cm, 0)
        Cpsum = Cp.sum()
        
        dx = (self.X*Cp).sum()/Cpsum
        dy = (self.Y*Cp).sum()/Cpsum
        
        ds = ndimage.shift(dm, [-dx, -dy])*self.mask
        
        #print A.shape, As.shape
        
        self.ds_A = (ds - refA)
        
        #calculate z offset between actual position and calibration position
        dz = self.deltaZ*np.dot(self.ds_A.ravel(), ddz)*dzn
        
        #add the offset back to determine how far we are from the target position
        dz = dz + posDelta
        
        return dx, dy, dz, Cm
        
    
    def tick(self, caller=None):
        if not 'mask' in dir(self) or not self.scope.pa.dsa.shape[:2] == self.mask.shape[:2]:
            self.initialise()
            
        #called on a new frame becoming available
        if self.calibState == 0:
            #redefine our positions for the calibration
            self.homePos = self.piezo.GetPos(0)
            self.calPositions = self.homePos + self.deltaZ*np.arange(-float(self.stackHalfSize), float(self.stackHalfSize + 1))
            self.NCalibStates = len(self.calPositions)
            
            self.calImages = np.zeros(self.mask.shape[:2] + (self.NCalibStates,))
            self.calFTs = np.zeros(self.mask.shape[:2] + (self.NCalibStates,), dtype='complex64')
            
            self.piezo.MoveTo(0, self.calPositions[0])
            
            #self.piezo.SetOffset(0)
            self.calibState += .5
        elif self.calibState < self.NCalibStates:
            if (self.calibState % 1) == 0:
                #full step - record current image and move on to next position
                self.setRefN(self.calibState - 1)
                self.piezo.MoveTo(0, self.calPositions[self.calibState])
            
            #increment our calibration state
            self.calibState += 0.5
            
        elif (self.calibState == self.NCalibStates):
            self.setRefN(self.calibState - 1)
            
            #perform final bit of calibration - calcuate gradient between steps
            #self.dz = (self.refC - self.refB).ravel()
            #self.dzn = 2./np.dot(self.dz, self.dz)
            self.dz = np.gradient(self.calImages)[2].reshape(-1, self.NCalibStates)
            self.dzn = np.hstack([1./np.dot(self.dz[:,i], self.dz[:,i]) for i in range(self.NCalibStates)])
            
            self.piezo.MoveTo(0, self.homePos)
            
            self.calibState += 1
            
        elif self.calibState > self.NCalibStates:
            #fully calibrated
            dx, dy, dz, cCoeff = self.compare()
            
            self.corrRef = max(self.corrRef, cCoeff)
            
            #print dx, dy, dz
            
            self.history.append((time.time(), dx, dy, dz, cCoeff))
            if self.logShifts:
                self.piezo.LogShifts(dx, dy, dz)
            
            if self.lockFocus and (cCoeff > .5*self.corrRef):
                if abs(dz) > self.focusTolerance and self.lastAdjustment >= 2:
                    self.piezo.SetOffset(self.piezo.GetOffset() - dz)
                    self.historyCorrections.append((time.time(), dz))
                    self.lastAdjustment = 0
                else:
                    self.lastAdjustment += 1
                    
            
    def reCalibrate(self):
        self.calibState = 0
        self.corrRef = 0
        
    def register(self):
        self.scope.pa.WantFrameGroupNotification.append(self.tick)
        
    def deregister(self):
        self.scope.pa.WantFrameGroupNotification.remove(self.tick)
    
    def setRefs(self, piezo):
        time.sleep(0.5)
        p = piezo.GetPos()
        self.setRefA()
        piezo.MoveTo(0, p -.2)
        time.sleep(0.5)
        self.setRefB()
        piezo.MoveTo(0,p +.2)
        time.sleep(0.5)
        self.setRefC()
        piezo.MoveTo(0, p)
    
    
    