#!/usr/bin/python
##################
# coloc.py
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
#import numpy
import wx
#import pylab
#from PYME.DSView.image import ImageStack
from enthought.traits.api import HasTraits, Float, Int
from enthought.traits.ui.api import View, Item
from enthought.traits.ui.menu import OKButton

class ZernikeView(wx.Panel):
    def __init__(self, dsviewer):
        from PYME.misc import zernike
        import numpy as np
        
        self.dsviewer = dsviewer
        mag = dsviewer.image.data[:,:,0]
        phase = dsviewer.image.data[:,:,1]
        
        xm = np.where(mag.max(1) > 0)[0]
        ym = np.where(mag.max(0) > 0)[0]
        
        print xm, ym, mag.shape

        mag = mag[xm[0]:(xm[-1]+1), ym[0]:(ym[-1]+1)]        
        phase = phase[xm[0]:(xm[-1]+1), ym[0]:(ym[-1]+1)]
        
        #im = mag*np.exp(1j*phase)
        
        coeffs, res, im = zernike.calcCoeffs(phase, 25, mag)
        
        s = ''
        
        for i, c, r, in zip(xrange(25), coeffs, res):
            s += '%d\t%s%3.3f\tresidual=%3.2f\n' % (i, zernike.NameByNumber[i].ljust(30), c, r)
        
        wx.Panel.__init__(self, dsviewer)
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        vsizer.Add(wx.StaticText(self, -1, s), 1, wx.EXPAND)
        
        self.SetSizerAndFit(vsizer)
        
        

class PupilTools(HasTraits):
    wavelength = Float(700)
    #NA = Float(1.49)
    sizeX = Int(61)
    sizeZ = Int(61)
    zSpacing = Float(50)    
    
    view = View(Item('wavelength'),
                #Item('NA'),
                Item('zSpacing'),
                Item('sizeZ'),
                Item('sizeX'),buttons=[OKButton])

    def __init__(self, dsviewer):
        self.dsviewer = dsviewer
        self.do = dsviewer.do

        self.image = dsviewer.image
        
        PROC_PUPIL_TO_PSF = wx.NewId()
        #PROC_APPLY_THRESHOLD = wx.NewId()
        #PROC_LABEL = wx.NewId()
        
        dsviewer.mProcessing.Append(PROC_PUPIL_TO_PSF, "Generate PSF from pupil", "", wx.ITEM_NORMAL)
        #dsviewer.mProcessing.Append(PROC_APPLY_THRESHOLD, "Generate &Mask", "", wx.ITEM_NORMAL)
        #dsviewer.mProcessing.Append(PROC_LABEL, "&Label", "", wx.ITEM_NORMAL)
    
        wx.EVT_MENU(dsviewer, PROC_PUPIL_TO_PSF, self.OnPSFFromPupil)
        #wx.EVT_MENU(dsviewer, PROC_APPLY_THRESHOLD, self.OnApplyThreshold)
        #wx.EVT_MENU(dsviewer, PROC_LABEL, self.OnLabel)

    def OnPSFFromPupil(self, event):
        import numpy as np
        #import pylab
        from PYME.PSFGen import fourierHNA
        
        from PYME.DSView.image import ImageStack
        from PYME.DSView import ViewIm3D
        
        self.configure_traits(kind='modal')

        z_ = np.arange(self.sizeZ)*float(self.zSpacing)
        z_ -= z_.mean()        
        
        ps = fourierHNA.PsfFromPupil(self.image.data[:,:,0]*np.exp(1j*self.image.data[:,:,1]), z_, self.image.mdh['voxelsize.x']*1e3, self.wavelength)#, shape = [self.sizeX, self.sizeX])
        
        im = ImageStack(ps, titleStub = 'Generated PSF')
        im.mdh.copyEntriesFrom(self.image.mdh)
        im.mdh['Parent'] = self.image.filename
        #im.mdh['Processing.CropROI'] = roi
        mode = 'psf'

        dv = ViewIm3D(im, mode=mode, glCanvas=self.dsviewer.glCanvas, parent=wx.GetTopLevelParent(self.dsviewer))

        

    



def Plug(dsviewer):
    dsviewer.PupilTools = PupilTools(dsviewer)
    dsviewer.zern = ZernikeView(dsviewer)
    dsviewer.AddPage(dsviewer.zern, False, 'Zernike Moments')



