from PYME.DSView import View3D
from PYME import cSMI
import numpy as np
#from PYME.Acquire import eventLog
from math import floor

class zScanner:
    def __init__(self, scope):
        self.scope = scope
        self.sa = scope.sa
        self.off = 0
        self.sc = 100
        self.sqrt = False
        
        self.ds = scope.pa.dsa
        
        self.running = False
 
        self.WantFrameNotification = []
        
    def _endSingle(self):
        self.Stop()
        self.WantFrameNotification.remove(self._endSingle)
        self.sa.piezoGoHome()
        
    def Single(self):
        self.sa.SetPrevPos(self.sa._CurPos())
        self.WantFrameNotification.append(self._endSingle)
        self.Start()
        
    def Start(self):
        self.image = np.zeros((self.ds.shape[0], self.ds.shape[1], 2), 'uint16')

        self.view = View3D(self.image, 'Live Stack')
        self.running = True
        
        self.zPoss = np.arange(self.sa.GetStartPos(), self.sa.GetEndPos()+.95*self.sa.GetStepSize(),self.sa.GetStepSize())
        piezo = self.sa.piezos[self.sa.GetScanChannel()]
        self.piezo = piezo[0]
        self.piezoChan = piezo[1]
        self.startPos = self.piezo.GetPos(self.piezoChan)
        
        self.scope.pa.stop()
        self.scope.pa.WantFrameNotification.append(self.tick)
        self.scope.pa.WantStartNotification.append(self.OnAqStart)
        self.scope.pa.WantStopNotification.append(self.OnAqStop)
        self.scope.pa.start()
        
    def Stop(self):
        self.scope.pa.stop()
        self.scope.pa.WantFrameNotification.remove(self.tick)
        self.scope.pa.WantStartNotification.remove(self.OnAqStart)
        self.scope.pa.WantStopNotification.remove(self.OnAqStop)
        self.scope.pa.start()
        
        self.running = False
        
        
    def OnAqStart(self, caller=None):
        
        self.pos = 0

        self.callNum = 0

        self.nz = len(self.zPoss)

        self.image = np.zeros((self.ds.shape[0], self.ds.shape[1], self.nz), 'uint16')

        self.view.do.SetDataStack(self.image)
        #self.view_xz = View3D(self.image)
        #self.view_xz.do.slice = 1
        #self.view_xz.do.yp = self.ds.shape[1]/2
        #self.view_xz.do.xp = self.ds.shape[0]/2
        #self.view_yz = View3D(self.image)
        #self.view_yz.do.slice = 2
        #self.view_yz.do.yp = self.ds.shape[1]/2
        #self.view_yz.do.xp = self.ds.shape[0]/2

        self.piezo.MoveTo(self.piezoChan, self.zPoss[self.pos])


    def tick(self, caller=None):
        fn = floor(self.callNum) % len(self.zPoss)
        if self.sqrt:
            self.image[:, :,fn] = (self.sc*np.sqrt(self.ds[:,:,0] - self.off)).astype('uint16')
        else:
            self.image[:, :,fn] = self.ds[:,:,0]

        #if not fn == self.pos:

        self.callNum += 1
        fn = floor(self.callNum) % len(self.zPoss)

        #self.piezo.MoveTo(self.piezoChan, self.zPoss[fn])
        self._movePiezo(fn)
        
        self.view.Refresh()
        
        if fn == 0: #we've wrapped around
            for cb in self.WantFrameNotification:
                cb()
        #self.view_xz.Refresh()
        #self.view_yz.Refresh()

    def _movePiezo(self, fn):
        self.piezo.MoveTo(self.piezoChan, self.zPoss[fn])
        
    def OnAqStop(self, caller=None):
        pass

    def destroy(self):
        self.Stop()
        
    def getCentroid(self):
        mx = self.image.max()
        mn = self.image.min()
        
        im2 = np.maximum(self.image.astype('f') - (mn + (mx - mn)/2), 0)
        im2s = im2.sum()
        
        z0 = (im2*self.zPoss[None,None,:]).sum()/im2s
        x_1, x_2 = self.scope.cam.ROIx
        y_1, y_2 = self.scope.cam.ROIy
        x = np.arange(float(x_1), x_2+1)
        y = np.arange(float(y_1), y_2+1)
        x0 = (im2*x[:,None,None]).sum()/im2s
        y0 = (im2*y[None,:,None]).sum()/im2s
        
        print x0, y0, z0
        print x0 - x.mean(), y0 - y.mean(), z0 - self.zPoss.mean()
        
        return x0 - x.mean(), y0 - y.mean(), z0 - self.zPoss.mean()
        
    def center(self):
        dx, dy, dz = self.getCentroid()
        
        self.scope.pa.stop()
        
        self.zPoss -= dz
        
        x1, x2 = self.scope.cam.ROIx
        y1, y2 = self.scope.cam.ROIy
        
        dx = int(dx)
        dy = int(dy)
        
        self.scope.cam.SetROI(x1 - dx,y1-dy,x2-dx,y2-dy)

        #self.view.Destroy()
        #self.view_xz.Destroy()
        #self.view_yz.Destroy()

class wavetableZScanner(zScanner):
    def __init__(self, scope, triggered=False):
        zScanner.__init__(self, scope)
        
        self.triggered = triggered
        
    def OnAqStart(self, caller=None):
        zScanner.OnAqStart(self, caller)

        self.piezo.PopulateWaveTable(self.piezoChan, self.zPoss)

        #self.scope.pa.stop()

        if self.triggered:
            #if we've got a hardware trigger rigged up, use it
            self.piezo.StartWaveOutput(self.piezoChan)
        else:
            #otherwise fudge so that step time is nominally the same as exposure time
            self.piezo.StartWaveOutput(self.piezoChan, self.scope.cam.tKin*1e3)

        #self.scope.pa.start()
        
    def OnAqStop(self, caller=None):
        self.piezo.StopWaveOutput()

    #def destroy(self):
        #self.piezo.StopWaveOutput()
    #    zScanner.destroy(self)

    def _movePiezo(self, fn):
        pass

def getBestScanner(scope):
    piezo = scope.sa.piezos[scope.sa.GetScanChannel()][0]
    
    if 'StartWaveOutput' in dir(piezo) and not scope.sa.GetSeqLength() > piezo.MAXWAVEPOINTS: #piezo supports wavetable output
        return wavetableZScanner(scope, piezo.hasTrigger)
    else: #no wavetable - possibly poorly synchronised
        return zScanner(scope)



