#Boa:Frame:AndorFrame



import wx



def create(parent):

    return AndorFrame(parent)



[wxID_ANDORFRAME, wxID_ANDORFRAMEBSETGAIN, wxID_ANDORFRAMEBSETTEMP, 
 wxID_ANDORFRAMEBUPDATEINT, wxID_ANDORFRAMECBBASELINECLAMP, 
 wxID_ANDORFRAMECBFRAMETRANSFER, wxID_ANDORFRAMECBSHUTTER, 
 wxID_ANDORFRAMECHHORIZCLOCK, wxID_ANDORFRAMECHVERTCLOCK, 
 wxID_ANDORFRAMEPANEL1, wxID_ANDORFRAMERBCONTIN, wxID_ANDORFRAMERBSINGLESHOT, 
 wxID_ANDORFRAMESTATICBOX1, wxID_ANDORFRAMESTATICBOX2, 
 wxID_ANDORFRAMESTATICBOX3, wxID_ANDORFRAMESTATICBOX4, 
 wxID_ANDORFRAMESTATICTEXT1, wxID_ANDORFRAMESTATICTEXT2, 
 wxID_ANDORFRAMESTATICTEXT3, wxID_ANDORFRAMESTATICTEXT4, 
 wxID_ANDORFRAMESTATICTEXT5, wxID_ANDORFRAMESTATICTEXT6, 
 wxID_ANDORFRAMETCCDTEMP, wxID_ANDORFRAMETEMGAIN, 
] = [wx.NewId() for _init_ctrls in range(24)]



class AndorPanel(wx.Panel):

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Panel.__init__(self, id=wxID_ANDORFRAME,
              parent=prnt, size=wx.Size(-1, -1))
        #self.SetClientSize(wx.Size(244, 327))

        vsizer=wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sbCooling = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Cooling [\N{DEGREE SIGN}C]'), wx.VERTICAL)
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.tCCDTemp = wx.TextCtrl(self, -1, '0', size=(30, -1))
        hsizer2.Add(self.tCCDTemp, 1, wx.wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        sbCooling.Add(hsizer2, 0, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.bSetTemp = wx.Button(self, -1, 'Set', style=wx.BU_EXACTFIT)
        self.bSetTemp.Bind(wx.EVT_BUTTON, self.OnBSetTempButton)
        hsizer2.Add(self.bSetTemp, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer.Add(sbCooling, 1, wx.EXPAND|wx.RIGHT, 5)


        sbEMGain = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'EM Gain', size=(30, -1)), wx.VERTICAL)
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.tEMGain = wx.TextCtrl(self, -1, '')
        hsizer2.Add(self.tEMGain, 1, wx.EXPAND|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        self.bSetGain = wx.Button(self, -1, 'Set', style=wx.BU_EXACTFIT)
        self.bSetGain.Bind(wx.EVT_BUTTON, self.OnBSetGainButton)
        hsizer2.Add(self.bSetGain, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 0)

        sbEMGain.Add(hsizer2, 0, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.stTrueEMGain = wx.StaticText(self, -1, '????')
        self.stTrueEMGain.SetForegroundColour(wx.RED)
        sbEMGain.Add(self.stTrueEMGain, 0, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 0)

        hsizer.Add(sbEMGain, 1, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 0)
        vsizer.Add(hsizer, 0, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 0)


        sbAqMode = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Acquisition Mode'), wx.HORIZONTAL)

        self.rbSingleShot = wx.RadioButton(self, -1, 'Single Shot')
        self.rbSingleShot.SetValue(False)
        self.rbSingleShot.SetToolTipString('Allows multiple channels with different integration times and good shutter synchronisation')
        self.rbSingleShot.Bind(wx.EVT_RADIOBUTTON,self.OnRbSingleShotRadiobutton)
        sbAqMode.Add(self.rbSingleShot, 1, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 0)

        self.rbContin = wx.RadioButton(self, -1, 'Continuous')
        self.rbContin.SetValue(True)
        self.rbContin.SetToolTipString('Allows fastest speeds, albeit without good syncronisation (fixable) or integration time flexibility')
        self.rbContin.Bind(wx.EVT_RADIOBUTTON, self.OnRbContinRadiobutton)
        sbAqMode.Add(self.rbContin, 1, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 0)

        vsizer.Add(sbAqMode, 0, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.TOP, 5)

        #self.bUpdateInt = wx.Button(id=wxID_ANDORFRAMEBUPDATEINT,
        #      label='Update Integration Time', name='bUpdateInt',
        #      parent=self, pos=wx.Point(104, 147), size=wx.Size(128, 23),
        #      style=0)
        #self.bUpdateInt.Enable(False)
        #self.bUpdateInt.Bind(wx.EVT_BUTTON, self.OnBUpdateIntButton,
        #      id=wxID_ANDORFRAMEBUPDATEINT)

        sbReadout = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Readout Settings'), wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, 'Horizontal Clock:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        self.chHorizClock = wx.Choice(self, -1, choices=[])
        self.chHorizClock.Bind(wx.EVT_CHOICE, self.OnChHorizClockChoice)
        hsizer.Add(self.chHorizClock, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        hsizer.Add(wx.StaticText(self, -1, 'MHz'), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sbReadout.Add(hsizer, 0, 0, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, 'Vertical Clock:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        self.chVertClock = wx.Choice(self, -1, choices=[])
        self.chVertClock.Bind(wx.EVT_CHOICE, self.OnChVertClockChoice)
        hsizer.Add(self.chVertClock, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        hsizer.Add(wx.StaticText(self, -1, u'\u03BCs'), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sbReadout.Add(hsizer, 0, 0, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.cbFrameTransfer = wx.CheckBox(self, -1, u'Frame Transfer')
        self.cbFrameTransfer.SetValue(True)
        self.cbFrameTransfer.Bind(wx.EVT_CHECKBOX, self.OnCbFrameTransferCheckbox)
        hsizer.Add(self.cbFrameTransfer, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.cbBaselineClamp = wx.CheckBox(self, -1, u'Baseline Clamp')
        self.cbBaselineClamp.SetValue(False)
        self.cbBaselineClamp.Bind(wx.EVT_CHECKBOX, self.OnCbBaselineClampCheckbox)
        hsizer.Add(self.cbBaselineClamp, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sbReadout.Add(hsizer, 0, 0, 0)
        vsizer.Add(sbReadout, 0, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.TOP, 5)

        self.cbShutter = wx.CheckBox(self, -1, u'Camera Shutter Open')
        self.cbShutter.SetValue(True)
        self.cbShutter.Bind(wx.EVT_CHECKBOX, self.OnCbShutterCheckbox)
        vsizer.Add(self.cbShutter, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP, 5)

        self.SetSizerAndFit(vsizer)

        

    def __init__(self, parent, cam, scope):
        self._init_ctrls(parent)

        self.cam = cam
        self.scope = scope

        self.tCCDTemp.ChangeValue(repr(self.cam.GetCCDTempSetPoint()))
        self.tEMGain.ChangeValue(repr(self.cam.GetEMGain()))

        self._PopulateSpeeds()

    def OnBSetTempButton(self, event):
        self.scope.pa.stop()
        self.cam.SetCCDTemp(int(self.tCCDTemp.GetValue()))
        self.scope.pa.start()

    def OnBSetGainButton(self, event):
        self.scope.pa.stop()
        self.cam.SetEMGain(int(self.tEMGain.GetValue()))
        self.scope.pa.start()

    def OnBStartSpoolingButton(self, event):
        #event.Skip()
        fname = wx.FileSelector('Save Images as ... (image # and .dat will be appended to filename)')
    
        if not fname == None:
            self.scope.pa.stop()
            self.cam.SpoolOn(fname)

            wx.MessageBox('Click cancel to stop spooling', 'Spooling to disk', wx.CANCEL)
            self.cam.SpoolOff()
            self.scope.pa.start()

    def OnBUpdateIntButton(self, event):
        #event.Skip()
        self.scope.pa.stop()
        self.scope.pa.start()

    def OnRbSingleShotRadiobutton(self, event):
        #event.Skip()
        if self.cam.contMode:
            self.scope.pa.stop()
            self.cam.SetAcquisitionMode(self.cam.MODE_SINGLE_SHOT)
            #self.bUpdateInt.Enable(False)
            self.scope.pa.start()

    def OnRbContinRadiobutton(self, event):
        #event.Skip()
        if not self.cam.contMode:
            self.scope.pa.stop()
            self.cam.SetAcquisitionMode(self.cam.MODE_CONTINUOUS)
            #self.bUpdateInt.Enable(True)
            self.scope.pa.start()

    def OnChHorizClockChoice(self, event):
        #event.Skip()
        self.scope.pa.stop()
        self.cam.SetHorizShiftSpeed(self.chHorizClock.GetSelection())
        self.scope.pa.start()

    def OnChVertClockChoice(self, event):
        #event.Skip()
        self.scope.pa.stop()
        self.cam.SetVerticalShiftSpeed(self.chVertClock.GetSelection())
        self.scope.pa.start()

    def OnCbFrameTransferCheckbox(self, event):
        #event.Skip()
        self.scope.pa.stop()
        self.cam.SetFrameTransfer(self.cbFrameTransfer.GetValue())
        self.scope.pa.start()

    def _PopulateSpeeds(self):
        for hs in self.cam.HorizShiftSpeeds[0][0]:
            self.chHorizClock.Append('%3.0f' % hs)

        self.chHorizClock.SetSelection(self.cam.HSSpeed)            

        for i in range(len(self.cam.vertShiftSpeeds)):
            if i < self.cam.fastestRecVSInd:
                self.chVertClock.Append('[%2.2f]' % self.cam.vertShiftSpeeds[i])
            else:
                self.chVertClock.Append('%2.2f' % self.cam.vertShiftSpeeds[i])            

        self.chVertClock.SetSelection(self.cam.VSSpeed)
        self.cbFrameTransfer.SetValue(self.cam.frameTransferMode)

    def OnCbShutterCheckbox(self, event):
        self.scope.pa.stop()
        self.cam.SetShutter(self.cbShutter.GetValue())
        self.scope.pa.start       
        #event.Skip()

    def OnCbBaselineClampCheckbox(self, event):
        #event.Skip()
        self.scope.pa.stop()
        self.cam.SetBaselineClamp(self.cbBaselineClamp.GetValue())
        self.scope.pa.start()

            
