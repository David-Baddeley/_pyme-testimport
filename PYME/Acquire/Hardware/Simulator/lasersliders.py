#!/usr/bin/python

##################
# lasersliders.py
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
# generated by wxGlade 0.3.3 on Thu Sep 23 08:22:22 2004


import wx
import sys

#redefine wxFrame with a version that hides when someone tries to close it
#dirty trick, but lets the Boa gui builder still work with frames we do this to
#from noclosefr import * 

class LaserSliders(wx.Panel):
    def __init__(self, parent, lasers, winid=-1):
        # begin wxGlade: MyFrame1.__init__
        #kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Panel.__init__(self, parent, winid)

        #self.cam = cam
        self.lasers = lasers
        self.laserNames=[l.GetName() for l in lasers]
        
        self.sliders = []
        #self.SetTitle("Piezo Control")
        
        sizer_2 = wx.BoxSizer(wx.VERTICAL)

        for c in range(len(self.lasers)):
            #if sys.platform == 'darwin': #sliders are subtly broken on MacOS, requiring workaround
            sl = wx.Slider(self, -1, self.lasers[c].GetPower(), 0, 1000, size=wx.Size(150,-1),style=wx.SL_HORIZONTAL)#|wx.SL_AUTOTICKS|wx.SL_LABELS)
            #else: #sane OS's
            #    sl = wx.Slider(self, -1, self.cam.laserPowers[c], 0, 1000, size=wx.Size(300,-1),style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)

            #sl.SetSize((800,20))
            sl.SetTickFreq(100,1)
            sz = wx.StaticBoxSizer(wx.StaticBox(self, -1, self.laserNames[c] + " [mW]"), wx.HORIZONTAL)
            sz.Add(sl, 1, wx.ALL|wx.EXPAND, 2)
            sizer_2.Add(sz,1,wx.EXPAND,0)

            self.sliders.append(sl)

        #sizer_2.AddSpacer(5)

        wx.EVT_SCROLL(self,self.onSlide)
                
       
        #self.SetAutoLayout(1)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        #sizer_2.SetSizeHints(self)
        
        #self.Layout()
        # end wxGlade

    def onSlide(self, event):
        sl = event.GetEventObject()
        ind = self.sliders.index(sl)
        self.sl = sl
        self.ind = ind
        self.lasers[ind].SetPower(self.lasers[ind].MAX_POWER*sl.GetValue()/1.0e3)

    def update(self):
        for ind, L in enumerate(self.lasers):
            self.sliders[ind].SetValue(L.GetPower()*1e3/L.MAX_POWER)

            


