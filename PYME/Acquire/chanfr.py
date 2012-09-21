#!/usr/bin/python

##################
# chanfr.py
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

#!/usr/bin/env python
# generated by wxGlade 0.3.3 on Mon Jun 14 06:48:07 2004

import wx
#import sys
#sys.path.append(".")

#import viewpanel
#import example

from chanpanel import ChannelPan

class ChanFrame(wx.Dialog):
    def __init__(self, parent, chaninfo, title='Edit Shutters/Channels'):
        wx.Dialog.__init__(self,parent, -1, title)

        self.cp = ChannelPan(chaninfo, parent=self)
        self.bOK = wx.Button(self, -1, "OK")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cp, 1,wx.EXPAND,0)
        sizer.Add(self.bOK, 0,wx.TOP, 5)
        self.SetAutoLayout(1)
        self.SetSizer(sizer)
        sizer.Fit(self)
        #sizer.SetSizeHints(self)

        self.Layout()

        wx.EVT_BUTTON(self, self.bOK.GetId(), self.OnOK)
			
    def OnOK(self, event):
        self.EndModal(1)         

        
    

# end of class ViewFrame