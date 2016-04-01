#!/usr/bin/python
##################
# prebleachExtraction.py
#
# Copyright David Baddeley, 2011
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

import wx
import numpy as np
#from PYME.Analysis import piecewiseMapping

class PrebleachExtractor:
    def __init__(self, dsviewer):
        self.dsviewer = dsviewer

        self.image = dsviewer.image
        self.split = 'Splitter' in self.image.mdh.getEntry('Analysis.FitModule')
        self.mixmatrix=np.array([[.85, .15],[.11, .89]])

        dsviewer.AddMenuItem('Processing', "&Extract Prebleach Image", self.OnExtract)

    def OnExtract(self, event):
        from PYME.DSView import View3D
        #print 'extracting ...'

        mdh = self.image.mdh

        #dark = deTile.genDark(self.vp.do.ds, self.image.mdh)
        dark = mdh.getEntry('Camera.ADOffset')

        #split = False

        frames = mdh.getEntry('Protocol.PrebleachFrames')
        
        dt = self.image.data[:,:,frames[0]:frames[1]].astype('f').mean(2)- dark

        ROIX1 = mdh.getEntry('Camera.ROIPosX')
        ROIY1 = mdh.getEntry('Camera.ROIPosY')

        ROIX2 = ROIX1 + mdh.getEntry('Camera.ROIWidth')
        ROIY2 = ROIY1 + mdh.getEntry('Camera.ROIHeight')

        if self.split:
            from PYME.Acquire.Hardware import splitter
            unmux = splitter.Unmixer([mdh.getEntry('chroma.dx'),mdh.getEntry('chroma.dy')], 1e3*mdh.getEntry('voxelsize.x'))

            dt = unmux.Unmix(dt, self.mixmatrix, 0, [ROIX1, ROIY1, ROIX2, ROIY2])

            View3D(dt, 'Prebleach Image')
        else:
            View3D(dt, 'Prebleach Image')


def Plug(dsviewer):
    dsviewer.pbe = PrebleachExtractor(dsviewer)


