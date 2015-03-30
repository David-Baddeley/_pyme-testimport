#!/usr/bin/python

##################
# LaserControlFrame.py
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
#redefine wxFrame with a version that hides when someone tries to close it
#dirty trick, but lets the Boa gui builder still work with frames we do this to
#from noclosefr import * 
class LaserPanel(wx.Panel):
    def __init__(self, parent,laser):
        wx.Panel.__init__(self, parent)
        self.laser = laser
        
        self.bs1 = wx.StaticBoxSizer(wx.StaticBox(self,label=self.laser.GetName()),wx.HORIZONTAL)
        
        self.cbOn = wx.CheckBox(self,wx.ID_ANY, 'On')
        self.bs1.Add(self.cbOn, 0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.bs1.AddStretchSpacer()
        self.bs1.Add(wx.StaticLine(self, style=wx.LI_VERTICAL, size=(2,25)), 0,wx.LEFT | wx.RIGHT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.bs1.Add(wx.StaticText(self, wx.ID_ANY, 'Power:'), 0,wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.tcPower= wx.TextCtrl(self, wx.ID_ANY, '1', size=(40,-1))
        self.bs1.Add(self.tcPower, 0,wx.ALL | wx.ALIGN_CENTRE | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.tcPower.Enable(self.laser.IsPowerControlable())
        
        self.bSetPower = wx.Button(self, wx.ID_ANY, 'Set', style=wx.BU_EXACTFIT)
        self.bs1.Add(self.bSetPower, 0,wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.bSetPower.Enable(self.laser.IsPowerControlable())
        
        self.bs1.AddStretchSpacer()
        self.bs1.Add(wx.StaticLine(self, style=wx.LI_VERTICAL, size=(2,25)), 0,wx.LEFT | wx.RIGHT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.tcPulse= wx.TextCtrl(self, wx.ID_ANY, '0', size=(40,-1))
        self.bs1.Add(self.tcPulse, 0,wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.tcPulse.Enable(not self.laser.IsOn())
        
        self.bPulse = wx.Button(self, wx.ID_ANY, 'Pulse', style=wx.BU_EXACTFIT)
        self.bs1.Add(self.bPulse, 0,wx.ALL | wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        self.bPulse.Enable(not self.laser.IsOn())
        
        self.cbOn.Bind(wx.EVT_CHECKBOX, self.OnCbOn)
        self.bSetPower.Bind(wx.EVT_BUTTON, self.OnBSetPower)
        self.bPulse.Bind(wx.EVT_BUTTON, self.OnBPulse)
        
        self.SetAutoLayout(1)
        self.SetSizer(self.bs1)
        self.Fit()
        self.Layout()
        
    def OnCbOn(self, event):
        if self.cbOn.GetValue():
            self.laser.TurnOn()
        else:
            self.laser.TurnOff()
            
        self.tcPulse.Enable(not self.laser.IsOn())
        self.bPulse.Enable(not self.laser.IsOn())
        
    def OnBSetPower(self, event):
        self.laser.SetPower(float(self.tcPower.GetValue()))
        
    def OnBPulse(self, event):
        self.laser.PulseBG(float(self.tcPulse.GetValue()))
        
class LaserControl(wx.Panel):
    def __init__(self, parent, lasers = None, winid=-1):
        # begin wxGlade: MyFrame1.__init__
        #kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Panel.__init__(self, parent, winid)
        self.lasers = lasers
        
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        for l in lasers:
            sizer_1.Add(LaserPanel(self, l),1, wx.EXPAND, 2)
                
       
        self.SetAutoLayout(1)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        sizer_1.SetSizeHints(self)
        self.Layout()
        
    def refresh(self):
        pass
        #for l, cb in zip(self.lasers, self.cBoxes):
        #    cb.SetValue(l.IsOn())
        # end wxGlade


class LaserControlLight(wx.Panel):
    def __init__(self, parent, lasers = None, winid=-1):
        # begin wxGlade: MyFrame1.__init__
        #kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Panel.__init__(self, parent, winid)
        self.lasers = lasers

        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        n = 0

        self.cBoxes = []

        for l in lasers:
            cb = wx.CheckBox(self, -1, l.GetName())
            cb.SetValue(l.IsOn())
            cb.Bind(wx.EVT_CHECKBOX, self.OnCbOn)
            self.cBoxes.append(cb)
            hsizer.Add(cb,1, wx.EXPAND, 0)
            n += 1
            if (n % 3) == 0:
                sizer_1.Add(hsizer,0, wx.EXPAND, 0)
                hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer_1.Add(hsizer,0, wx.EXPAND, 0)


        self.SetAutoLayout(1)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        sizer_1.SetSizeHints(self)
        self.Layout()
        # end wxGlade

    def OnCbOn(self, event):
        cb = event.GetEventObject()
        ind = self.cBoxes.index(cb)

        if cb.GetValue():
            self.lasers[ind].TurnOn()
        else:
            self.lasers[ind].TurnOff()

    def refresh(self):
        for l, cb in zip(self.lasers, self.cBoxes):
            cb.SetValue(l.IsOn())
