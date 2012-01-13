#!/usr/bin/python
##################
# photophysics.py
#
# Copyright David Baddeley, 2010
# d.baddeley@auckland.ac.nz
# 
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import wx
import numpy as np

class DecayAnalyser:
    def __init__(self, visFr):
        self.visFr = visFr

        ID_CALC_DECAYS = wx.NewId()
        self.visFr.extras_menu.Append(ID_CALC_DECAYS, "Estimate decay lifetimes")
        self.visFr.Bind(wx.EVT_MENU, self.OnCalcDecays, id=ID_CALC_DECAYS)

        ID_INTENS_STEPS = wx.NewId()
        self.visFr.extras_menu.Append(ID_INTENS_STEPS, "Retrieve Intensity steps")
        self.visFr.Bind(wx.EVT_MENU, self.OnRetrieveIntensitySteps, id=ID_INTENS_STEPS)

    def OnCalcDecays(self, event):
        from PYME.Analysis.BleachProfile import kinModels

        kinModels.fitDecay(self.visFr.colourFilter, self.visFr.mdh)
        kinModels.fitFluorBrightness(self.visFr.colourFilter, self.visFr.mdh)
        kinModels.fitOnTimes(self.visFr.colourFilter, self.visFr.mdh)

    def OnRetrieveIntensitySteps(self, event):
        from PYME.Analysis import piecewiseMapping
        fw = piecewiseMapping.GeneratePMFromProtocolEvents(self.visFr.events, self.visFr.mdh, self.visFr.mdh.getEntry('StartTime'), 10)
        self.visFr.selectedDataSource.fw = fw(self.visFr.selectedDataSource['t'])
        self.visFr.selectedDataSource.setMapping('filter', 'fw')
        self.visFr.selectedDataSource.setMapping('ColourNorm', '0.0*t')

        vals = list(set(self.visFr.selectedDataSource.fw))

        for key in vals:
            self.visFr.mapping.setMapping('p_%d' % key, 'filter == %d' % key)

        #self.visFr.UpdatePointColourChoices()
        self.visFr.colourFilterPane.UpdateColourFilterChoices()
        


def Plug(visFr):
    '''Plugs this module into the gui'''
    DecayAnalyser(visFr)



