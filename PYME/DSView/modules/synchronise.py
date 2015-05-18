#!/usr/bin/python
##################
# vis3D.py
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
import os
#import pylab
#from PYME.Acquire import MetaDataHandler
#from PYME.DSView import image, View3D
#from PYME.DSView import dataWrap
from PYME.DSView import dsviewer_npy_nb


class syncer:
    def __init__(self, dsviewer):
        self.dsviewer = dsviewer
        self.do = dsviewer.do

        self.image = dsviewer.image
        
        dsviewer.AddMenuItem('Processing', "Sync Windows", self.OnSynchronise)



    def OnSynchronise(self, event):
        dlg = wx.SingleChoiceDialog(
                self.dsviewer, 'choose the image to composite with', 'Make Composite',
                dsviewer_npy_nb.openViewers.keys(),
                wx.CHOICEDLG_STYLE
                )

        if dlg.ShowModal() == wx.ID_OK:
            other = dsviewer_npy_nb.openViewers[dlg.GetStringSelection()]

            other.do.syncedWith.append(self.do)

        dlg.Destroy()

    

       
    


def Plug(dsviewer):
    dsviewer.compos = syncer(dsviewer)



