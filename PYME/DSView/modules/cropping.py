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

class cropper:
    def __init__(self, dsviewer):
        self.dsviewer = dsviewer
        self.do = dsviewer.do

        self.image = dsviewer.image
        
        dsviewer.AddMenuItem("Processing", "&Crop\tCtrl-Shift-D", self.OnCrop)
        dsviewer.AddMenuItem("Processing", "Diagonal Composite", self.OnDiagSplit)

    def OnCrop(self, event):
        import numpy as np
        #from scipy.ndimage import gaussian_filter
        from PYME.DSView.image import ImageStack
        from PYME.DSView import ViewIm3D

        #dlg = wx.TextEntryDialog(self.dsviewer, 'Blur size [pixels]:', 'Gaussian Blur', '[1,1,1]')

        #if dlg.ShowModal() == wx.ID_OK:
            #sigmas = eval(dlg.GetValue())
            #print sigmas
            #print self.images[0].img.shape

        roi = [[self.do.selection_begin_x, self.do.selection_end_x + 1],[self.do.selection_begin_y, self.do.selection_end_y +1], [0, self.image.data.shape[2]]]

        filt_ims = [np.atleast_3d(self.image.data[roi[0][0]:roi[0][1],roi[1][0]:roi[1][1],:,chanNum].squeeze()) for chanNum in range(self.image.data.shape[3])]

        im = ImageStack(filt_ims, titleStub = 'Cropped Image')
        im.mdh.copyEntriesFrom(self.image.mdh)
        im.mdh['Parent'] = self.image.filename
        im.mdh['Processing.CropROI'] = roi

        vx, vy, vz = self.image.voxelsize
        ox, oy, oz = self.image.origin
        
        im.mdh['Origin.x'] = ox + roi[0][0]*vx
        im.mdh['Origin.y'] = oy + roi[1][0]*vy
        im.mdh['Origin.z'] = oz

        if self.dsviewer.mode == 'visGUI':
            mode = 'visGUI'
        else:
            mode = 'lite'

        dv = ViewIm3D(im, mode=mode, glCanvas=self.dsviewer.glCanvas, parent=wx.GetTopLevelParent(self.dsviewer))

        #set scaling to (0,1)
        for i in range(im.data.shape[3]):
            dv.do.Gains[i] = 1.0

            #imfc = MultiChannelImageViewFrame(self.parent, self.parent.glCanvas, filt_ims, self.image.names, title='Filtered Image - %3.1fnm bins' % self.image.pixelSize)

            #self.parent.generatedImages.append(imfc)
            #imfc.Show()

        #dlg.Destroy()

    def OnDiagSplit(self, event):
        import numpy as np
        #from scipy.ndimage import gaussian_filter
        from PYME.DSView.image import ImageStack
        from PYME.DSView import ViewIm3D

        #dlg = wx.TextEntryDialog(self.dsviewer, 'Blur size [pixels]:', 'Gaussian Blur', '[1,1,1]')

        #if dlg.ShowModal() == wx.ID_OK:
            #sigmas = eval(dlg.GetValue())
            #print sigmas
            #print self.images[0].img.shape

        x0, x1, y0, y1 = [self.do.selection_begin_x, self.do.selection_end_x, self.do.selection_begin_y, self.do.selection_end_y]
        
        dx = x1 - x0
        dy = y1 - y0
        
        m = dy/dx
        c = y0 - m*x0
        
        d = self.image.data
        
        X, Y = np.ogrid[:d.shape[0], :d.shape[1]]
        
        msk = Y > (m*X + c)

        #filt_ims = [np.atleast_3d(self.image.data[roi[0][0]:roi[0][1],roi[1][0]:roi[1][1],:,chanNum].squeeze()) for chanNum in range(self.image.data.shape[3])]
        imn = (d[:,:,:, 0] - self.do.Offs[0])*self.do.Gains[0]*msk[:,:, None] + (d[:,:,:,1]- self.do.Offs[1])*self.do.Gains[1]*(1-msk)[:,:,None]

        im = ImageStack(imn, titleStub = 'Cropped Image')
        im.mdh.copyEntriesFrom(self.image.mdh)
        im.mdh['Parent'] = self.image.filename
        #im.mdh['Processing.CropROI'] = roi

          

        if self.dsviewer.mode == 'visGUI':
            mode = 'visGUI'
        else:
            mode = 'lite'

        dv = ViewIm3D(im, mode=mode, glCanvas=self.dsviewer.glCanvas, parent=wx.GetTopLevelParent(self.dsviewer))

        #set scaling to (0,1)
        for i in range(im.data.shape[3]):
            dv.do.Gains[i] = 1.0

            #imfc = MultiChannelImageViewFrame(self.parent, self.parent.glCanvas, filt_ims, self.image.names, title='Filtered Image - %3.1fnm bins' % self.image.pixelSize)

            #self.parent.generatedImages.append(imfc)
            #imfc.Show()

        #dlg.Destroy()



def Plug(dsviewer):
    dsviewer.cropper = cropper(dsviewer)



