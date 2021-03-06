#!/usr/bin/python

##################
# psliders.py
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
#import noclosefr
import sys

class PiezoSliders(wx.Panel):
    def __init__(self, piezos, parent, joystick = None, id=-1):
        # begin wxGlade: MyFrame1.__init__
        #kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Panel.__init__(self, parent, id)

        self.piezos = piezos
        self.joystick = joystick
        #self.panel_1 = wx.Panel(self, -1)
        self.sliders = []
        self.sliderLabels = []
        #self.SetTitle("Piezo Control")
        #sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)

        for p in self.piezos:
            #if sys.platform == 'darwin': #sliders are subtly broken on MacOS, requiring workaround
            sl = wx.Slider(self, -1, 100*p[0].GetPos(p[1]), 100*p[0].GetMin(p[1]), 100*p[0].GetMax(p[1]), size=wx.Size(100,-1), style=wx.SL_HORIZONTAL)#|wx.SL_AUTOTICKS|wx.SL_LABELS)
            #else:
            #    sl = wx.Slider(self.panel_1, -1, 100*p[0].GetPos(p[1]), 100*p[0].GetMin(p[1]), 100*p[0].GetMax(p[1]), size=wx.Size(300,-1), style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
            #sl.SetSize((800,20))
            if 'units' in dir(p[0]):
                unit = p[0].units
            else:
                unit = u'\u03BCm'
            sLab = wx.StaticBox(self, -1, u'%s - %2.4f %s' % (p[2], p[0].GetPos(p[1]), unit))

#            if 'minorTick' in dir(p):
#                sl.SetTickFreq(100, p.minorTick)
#            else:
#                sl.SetTickFreq(100, 1)
            sz = wx.StaticBoxSizer(sLab, wx.HORIZONTAL)
            sz.Add(sl, 1, wx.ALL|wx.EXPAND, 2)
            #sz.Add(sLab, 0, wx.ALL|wx.EXPAND, 2)
            sizer_2.Add(sz,1,wx.EXPAND,0)

            self.sliders.append(sl)
            self.sliderLabels.append(sLab)


        if not joystick is None:
            self.cbJoystick = wx.CheckBox(self, -1, 'Enable Joystick')
            sizer_2.Add(self.cbJoystick,0,wx.TOP|wx.BOTTOM,2)
            self.cbJoystick.Bind(wx.EVT_CHECKBOX, self.OnJoystickEnable)

        #sizer_2.AddSpacer(1)

        wx.EVT_SCROLL(self,self.onSlide)


        #self.SetAutoLayout(1)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        #sizer_2.SetSizeHints(self)

        #self.Layout()
        # end wxGlade

    def OnJoystickEnable(self, event):
        self.joystick.Enable(self.cbJoystick.IsChecked())

    def onSlide(self, event):
        sl = event.GetEventObject()
        ind = self.sliders.index(sl)
        self.sl = sl
        self.ind = ind
        self.piezos[ind][0].MoveTo(self.piezos[ind][1], sl.GetValue()/100.0, False)
        self.sliderLabels[ind].SetLabel(u'%s - %2.2f \u03BCm' % (self.piezos[ind][2],sl.GetValue()/100.0))

    def update(self):
        for ind in range(len(self.piezos)):
            p = self.piezos[ind]
            if 'units' in dir(p[0]):
                unit = p[0].units
            else:
                unit = u'\u03BCm'
                
            if 'lastPos' in dir(self.piezos[ind]):
                self.sliders[ind].SetValue(100*self.piezos[ind][0].lastPos)
                self.sliderLabels[ind].SetLabel(u'%s - %2.4f %s' % (self.piezos[ind][2],self.piezos[ind][0].lastPos, unit))
            elif 'GetLastPos' in dir(self.piezos[ind][0]):
                lp = self.piezos[ind][0].GetLastPos(self.piezos[ind][1])
                self.sliders[ind].SetValue(100*lp)
                self.sliderLabels[ind].SetLabel(u'%s - %2.4f %s' % (self.piezos[ind][2],lp, unit))
            else:
                pos = self.piezos[ind][0].GetPos(self.piezos[ind][1])
                self.sliders[ind].SetValue(100*pos)
                self.sliderLabels[ind].SetLabel(u'%s - %2.4f %s' % (self.piezos[ind][2],pos, unit))
                
            self.sliders[ind].SetMin(100*self.piezos[ind][0].GetMin(self.piezos[ind][1]))
            self.sliders[ind].SetMax(100*self.piezos[ind][0].GetMax(self.piezos[ind][1]))

        if not self.joystick is None:
            self.cbJoystick.SetValue(self.joystick.IsEnabled())

            


