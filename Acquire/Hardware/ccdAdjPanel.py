from PYME.misc import wxPlotPanel
import numpy as np
import matplotlib
from PYME.Acquire.Hardware import EMCCDTheory
from PYME.Acquire.Hardware import ccdCalibrator

class ccdPlotPanel(wxPlotPanel.PlotPanel):
    def __init__(self, parent, cam, dispPan, empan, **kwargs ):
        self.cam = cam
        self.dp = dispPan
        self.empan = empan

        wxPlotPanel.PlotPanel.__init__( self, parent, **kwargs )

    def draw( self ):
            """Draw data."""
            matplotlib.interactive(False)
            
            if not hasattr( self, 'spEMGain' ):
                self.spEMSNR = self.figure.add_subplot( 211 )
                self.spEMHeadroom = self.spEMSNR.twinx()
                self.spIntSNR = self.figure.add_subplot( 212 )
                self.spIntFrameRate = self.spIntSNR.twinx()

            #a, ed = numpy.histogram(self.fitResults['tIndex'], self.Size[0]/2)
            self.spEMSNR.cla()
            self.spEMHeadroom.cla()
            self.spIntSNR.cla()
            self.spIntFrameRate.cla()

            emGainSettings = np.arange(0, 220, 5)

            emGains = ccdCalibrator.getCalibratedCCDGain(emGainSettings, self.cam.GetTempSetPoint())

            if emGains == None: # can't do anything
                self.figure.show()
                matplotlib.interactive(True)
                return

            currEMGain = ccdCalibrator.getCalibratedCCDGain(self.cam.GetEMGain(), self.cam.GetTempSetPoint())

            Imin = self.dp.min
            Imax = self.dp.max
            Imean = self.dp.mean

            off = self.dp.offset

            snrMin = EMCCDTheory.SNR((Imin - off)*self.cam.ElectronsPerCount, self.cam.ReadNoise, emGains, self.cam.NGainStages)
            snrMean = EMCCDTheory.SNR((Imean - off)*self.cam.ElectronsPerCount, self.cam.ReadNoise, emGains, self.cam.NGainStages)
            snrMin = EMCCDTheory.SNR((Imax - off)*self.cam.ElectronsPerCount, self.cam.ReadNoise, emGains, self.cam.NGainStages)

            
            self.spEMSNR.plot(np.log10(emGains), 10*log10(snrMin), color='b')
            self.spEMSNR.plot(np.log10(emGains), 10*log10(snrMean), color='b', lw=2)
            self.spEMSNR.plot(np.log10(emGains), 10*log10(snrMax), color='b')
            xticks = [1, 10, 100, 1000]
            self.spEMSNR.set_xticks(log10(xticks))
            self.spEMSNR.set_xticklabels([str(t) fot t in xticks])
            self.spEMSNR.set_xlabel('True EM Gain')
            self.spEMSNR.set_ylabel('SNR [dB]', colour = 'b')
            for t in self.spEMSNR.get_yticklabels():
                t.set_colour('b')

            
            self.spEMHeadroom.semilogy(np.log10(emGains), (satThresh - off)/((Imax - off)*emGains/currEMGain), color='r', lw=2)
            self.spEMHeadroom.xaxis.tick_top()
            xticks = [0, 50, 100, 150, 200]
            self.spEMHeadroom.set_xticks(log10(ccdCalibrator.getCalibratedCCDGain(xticks, self.cam.GetTempSetPoint())))
            self.spEMHeadroom.set_xticklabels([str(t) fot t in xticks])
            self.spEMHeadroom.set_xlabel('EM Gain Setting')
            self.spEMHeadroom.set_ylabel('Headroom - Isat/Imax', colour = 'r')
            self.spEMHeadroom.set_ylim(ymin=1)
            for t in self.spEMSNR.get_yticklabels():
                t.set_colour('r')

            #self.subplot1.set_yticks([0, a.max()])
            #self.subplot2.plot(ed[:-1], numpy.cumsum(a), color='g' )
            #self.subplot2.set_xticks([0, ed.max()])
            #self.subplot2.set_yticks([0, a.sum()])

            self.figure.show()

            matplotlib.interactive(True)

