#!/usr/bin/python

##################
# seqdialog.py
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

#Boa:Dialog:seqDialog

import wx
import wx.lib.agw.aui as aui

#from PYME.Acquire import simplesequenceaquisator
from PYME.Acquire import stackSettings
#from PYME.Acquire import MetaDataHandler

#redefine wxFrame with a version that hides when someone tries to close it

#dirty trick, but lets the Boa gui builder still work with frames we do this to

#NB must come after 'from wx.... import *' !!!

#from noclosefr import * 

MSG_NO_WAVETABLE = '''Piezo does not support wavetable output.
Synchronisation between movement and frames may be poor.
                    
Using a long integration time and/or setting the camera to single shot mode might help.'''

MSG_LONG_WAVETABLE = '''Piezo does not support wavetables longer than %d frames.
Synchronisation between movement and frames may be poor.
                    
Either decreasing the stack size, or using a long integration time and/or setting the camera to single shot mode might help.'''



def create(parent):

    return seqDialog(parent)

[wxID_SEQDIALOG, wxID_SEQDIALOGBENDHERE, wxID_SEQDIALOGBMID_NUM, 

 wxID_SEQDIALOGBSTART, wxID_SEQDIALOGBSTARTHERE, wxID_SEQDIALOGBST_END, 

 wxID_SEQDIALOGCHPIEZO, wxID_SEQDIALOGSTATICBOX1, wxID_SEQDIALOGSTATICBOX2, 

 wxID_SEQDIALOGSTATICBOX3, wxID_SEQDIALOGSTATICBOX4, wxID_SEQDIALOGSTATICBOX5, 

 wxID_SEQDIALOGSTATICBOX6, wxID_SEQDIALOGSTMEMORY, wxID_SEQDIALOGTENDPOS, 

 wxID_SEQDIALOGTNUMSLICES, wxID_SEQDIALOGTSTEPSIZE, wxID_SEQDIALOGTSTPOS, 

] = [wx.NewId() for i in range(18)]



class seqPanel(wx.Panel):
    def _init_ctrls(self, prnt):
        # generated method, don't edit

        wx.Panel.__init__(self, id=wxID_SEQDIALOG, parent=prnt)
        #self.SetClientSize(wx.Size(348, 167))
        #self.SetBackgroundColour(wx.Colour(209, 208, 203))

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        hsizer.Add(wx.StaticText(self, -1, u'Piezo Channel:'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)

        #sPiezo = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Piezo Channel'), wx.HORIZONTAL)

        self.chPiezo = wx.Choice(self, -1, choices=[], size=(-1,-1))
        self.chPiezo.Bind(wx.EVT_CHOICE, self.OnChPiezoChoice)

        hsizer.Add(self.chPiezo, 1,wx.ALIGN_CENTER_VERTICAL|wx.LEFT,2)
        #hsizer.Add(sPiezo, 1, wx.EXPAND|wx.RIGHT, 5)
        vsizer.Add(hsizer, 0, wx.EXPAND|wx.BOTTOM, 5)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        #hsizer.Add(wx.StaticText(self, -1, u'Type:'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 1)

        #sType = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Type'), wx.VERTICAL)

        self.bSt_end = wx.RadioButton(self, -1,'Start and End', size=(-1,-1))
        self.bSt_end.SetValue(True)
        self.bSt_end.Bind(wx.EVT_RADIOBUTTON, self.OnBSt_endRadiobutton)

        hsizer.Add(self.bSt_end, 1,wx.ALIGN_CENTER_VERTICAL,0)

        self.bMid_num = wx.RadioButton(self, -1, 'Middle and #', size=(-1,-1))
        self.bMid_num.SetValue(False)
        self.bMid_num.Bind(wx.EVT_RADIOBUTTON, self.OnBMid_numRadiobutton)

        hsizer.Add(self.bMid_num, 1,wx.ALIGN_CENTER_VERTICAL,0)
        #hsizer.Add(sType, 1, wx.EXPAND, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        #hsizer.Add(wx.StaticText(self, -1, u'Start [\u03BCm]:'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.bStartHere = wx.Button(self, -1,'Start', size=(30,-1), style=wx.BU_EXACTFIT)
        self.bStartHere.Bind(wx.EVT_BUTTON, self.OnBStartHereButton)
        hsizer.Add(self.bStartHere, 1, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.RIGHT, 2)

        #sStart = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Start Pos [\u03BCm]'), wx.HORIZONTAL)

        self.tStPos = wx.TextCtrl(self, -1, value='40', size=(10,-1))
        self.tStPos.Bind(wx.EVT_KILL_FOCUS, self.OnTStPosKillFocus)
        hsizer.Add(self.tStPos, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        

        #hsizer.Add(sStart, 1, wx.RIGHT, 5)
        #vsizer.Add(hsizer, 0, wx.EXPAND, 0)
        #hsizer = wx.BoxSizer(wx.HORIZONTAL)

        #hsizer.Add(wx.StaticText(self, -1, u'End [\u03BCm]:  '), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)        
        #sEnd = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'End Pos [\u03BCm]'), wx.HORIZONTAL)
        
        self.bEndHere = wx.Button(self, -1,'End', size=(30,-1), style=wx.BU_EXACTFIT)
        self.bEndHere.Bind(wx.EVT_BUTTON, self.OnBEndHereButton)
        hsizer.Add(self.bEndHere, 1, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.LEFT, 5)

        self.tEndPos = wx.TextCtrl(self, -1, value='40', size=(10,-1))
        self.tEndPos.Bind(wx.EVT_KILL_FOCUS, self.OnTEndPosKillFocus)
        hsizer.Add(self.tEndPos, 1, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)

        

        #hsizer.Add(sEnd, 1, 0, 0)
        vsizer.Add(hsizer, 0, wx.EXPAND|wx.BOTTOM, 2)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, u'Step [\u03BCm]: '), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        #sStep = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Step Size [\u03BCm]'), wx.HORIZONTAL)

        self.tStepSize = wx.TextCtrl(self, -1, value='0.2', size=(40,-1))
        self.tStepSize.Bind(wx.EVT_KILL_FOCUS, self.OnTStepSizeKillFocus)
        hsizer.Add(self.tStepSize, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        #hsizer.Add(sStep, 1, wx.RIGHT, 5)
        #vsizer.Add(hsizer, 0, wx.EXPAND, 0)
        #hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, u' # Slices:'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)        
        #sNSlices = wx.StaticBoxSizer(wx.StaticBox(self, -1, '# Slices'), wx.HORIZONTAL)

        self.tNumSlices = wx.TextCtrl(self, -1, value='100', size=(40,-1))
        self.tNumSlices.Bind(wx.EVT_KILL_FOCUS, self.OnTNumSlicesKillFocus)
        hsizer.Add(self.tNumSlices, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        #hsizer.Add(sNSlices, 1, 0, 0)
        vsizer.Add(hsizer, 0, wx.EXPAND|wx.BOTTOM, 5)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.stMemory = wx.StaticText(self, -1, '')
        hsizer.Add(self.stMemory, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.bStart = wx.Button(self, -1, 'Single Stack', style=wx.BU_EXACTFIT)
        self.bStart.Bind(wx.EVT_BUTTON, self.OnBSingle)
        hsizer.Add(self.bStart, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5, 0)
        
        self.bLive = wx.Button(self, -1, 'Live', style=wx.BU_EXACTFIT)
        self.bLive.Bind(wx.EVT_BUTTON, self.OnBLive)
        hsizer.Add(self.bLive, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND, 0)

        self.SetSizerAndFit(vsizer)

    def __init__(self, parent, scope):
        self.scope = scope
        self._init_ctrls(parent)

        #if not ('sa' in self.scope.__dict__):
        #    self.stackSettings = simplesequenceaquisator.SimpleSequenceAquisitor(self.scope.chaninfo, self.scope.cam, self.scope.shutters, self.scope.piezos)
        if not 'stackSettings' in dir(self.scope):
            #inject stack settings into the scope object
            self.scope.stackSettings = stackSettings.StackSettings(scope)
        #for pz in self.scope.piezos:
        #    self.chPiezo.Append(pz[2])
            
        self.stackSettings = self.scope.stackSettings
        
        self.scanDirs = self.scope.positioning.keys()

        self.chPiezo.SetItems(self.scanDirs)

        self.UpdateDisp()   

        
    def OnBEndHereButton(self, event):
        self.stackSettings.SetEndPos(self.scope.GetPos()[self.stackSettings.GetScanChannel()])
        self.UpdateDisp()


    def OnBStartHereButton(self, event):
        self.stackSettings.SetStartPos(self.scope.GetPos()[self.stackSettings.GetScanChannel()])
        self.UpdateDisp()


#    def OnBStartButton(self, event):
#        res = self.stackSettings.Verify()
#
#        if res[0]:
#            self.scope.pa.stop()
#            
#            self.stackSettings.Prepare()
#            self.stackSettings.WantFrameNotification=[]
#            self.stackSettings.WantFrameNotification.append(self.scope.aq_refr)
#            self.stackSettings.WantStopNotification=[]
#            self.stackSettings.WantStopNotification.append(self.scope.aq_end)
#            self.stackSettings.start()
#            self.scope.pb = wx.ProgressDialog('Aquisition in progress ...', 'Slice 1 of %d' % self.stackSettings.ds.getDepth(), self.stackSettings.ds.getDepth(), style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|wx.PD_REMAINING_TIME|wx.PD_CAN_ABORT)
#
#        else:
#            dialog = wx.MessageDialog(None, res[2] + ' (%2.3f)'% res[3], "Parameter Error", wx.OK)
#            dialog.ShowModal()
#
#            if res[1] == 'StepSize':
#                self.tStepSize.SetFocus()
#
#            elif (self.stackSettings.GetStartMode() == self.stackSettings.CENTRE_AND_LENGTH):
#                self.tNumSlices.SetFocus()
#
#            elif (res[1] == 'StartPos'):
#                self.tStPos.SetFocus()
#                
#            else:
#                self.tEndPos.SetFocus() 

                 

    def OnBSingle(self, event):
        self.OnBLive(event, True)
        
        #monkey patch in a progress panel        
        self.dlgAqProg = SeqProgressPanel(self.scope.zs)

        self.pinfo1 = aui.AuiPaneInfo().Name("deconvPanel").Top().Caption('Acquisition Progress').DestroyOnClose(True).CloseButton(False)#.MinimizeButton(True).MinimizeMode(aui.AUI_MINIMIZE_CAPT_SMART|aui.AUI_MINIMIZE_POS_RIGHT)#.CaptionVisible(False)
        self.scope.zs.view._mgr.AddPane(self.dlgAqProg, self.pinfo1)
        self.scope.zs.view._mgr.Update()
        
        #self.scope.zs.WantTickNotification.append(self.dlgAqProg.Tick)
        self.scope.zs.onSingleFrame.connect(self.dlgAqProg.Tick)
        
    def OnSingleEnd(self, **kwargs):
        #wx.MessageBox('Acquisition Finished')
        #self.scope.zs.WantFrameNotification.remove(self.OnSingleEnd)
        #self.scope.zs.WantTickNotification.remove(self.dlgAqProg.Tick)
        
        self.scope.zs.onStack.disconnect(self.OnSingleEnd)
        self.scope.zs.onSingleFrame.disconnect(self.dlgAqProg.Tick)
        
        self.bStart.Enable(True)
        self.bLive.SetLabel('Live')
        
        self.scope.zs.view._mgr.ClosePane(self.pinfo1)
        self.scope.zs.view._mgr.Update()
        print('se')
        
        
        
    def OnBLive(self, event, single=False):
        from PYME.Acquire import zScanner
        
        if 'zs' in dir(self.scope) and self.scope.zs.running: #stop
            self.scope.zs.Stop()
            self.bLive.SetLabel('Live')
            self.bStart.Enable(True)
            
        else:
            res = self.stackSettings.Verify()
            
            if res[0]:                
                
                self.scope.zs = zScanner.getBestScanner(self.scope)
                
                if not isinstance(self.scope.zs, zScanner.wavetableZScanner):
                    pz = self.scope.positioning[self.stackSettings.GetScanChannel()][0]
                    if 'MAXWAVEPOINTS' in dir(pz):
                        msg = MSG_LONG_WAVETABLE % pz.MAXWAVEPOINTS
                    else:
                        msg = MSG_NO_WAVETABLE
                        
                    dialog = wx.MessageDialog(None, msg, "Warning", wx.OK)
                    dialog.ShowModal()
                
                if single:
                    #self.scope.zs.WantFrameNotification.append(self.OnSingleEnd)
                    self.scope.zs.onStack.connect(self.OnSingleEnd)
                    self.scope.zs.Single()
                else:
                    self.scope.zs.Start()
                self.bLive.SetLabel('Stop')
                self.bStart.Enable(False)
    
            else:
                dialog = wx.MessageDialog(None, res[2] + ' (%2.3f)'% res[3], "Parameter Error", wx.OK)
                dialog.ShowModal()
    
                if res[1] == 'StepSize':
                    self.tStepSize.SetFocus()
    
                elif (self.stackSettings.GetStartMode() == self.stackSettings.CENTRE_AND_LENGTH):
                    self.tNumSlices.SetFocus()
    
                elif (res[1] == 'StartPos'):
                    self.tStPos.SetFocus()
    
                else:
                    self.tEndPos.SetFocus() 
        
            
    

    def OnChPiezoChoice(self, event):
        self.stackSettings.SetScanChannel(self.chPiezo.GetStringSelection())
        self.UpdateDisp()

        event.Skip()

    def OnBSt_endRadiobutton(self, event):
        self.stackSettings.SetStartMode(1)
        self.UpdateDisp()

        event.Skip()

    def OnBMid_numRadiobutton(self, event):
        self.stackSettings.SetStartMode(0)
        self.UpdateDisp()

        event.Skip()

    def OnTEndPosKillFocus(self, event):
        self.stackSettings.SetEndPos(float(self.tEndPos.GetValue()))
        self.UpdateDisp()

        event.Skip()

    def OnTStPosKillFocus(self, event):
        self.stackSettings.SetStartPos(float(self.tStPos.GetValue()))
        self.UpdateDisp()

        event.Skip()

    def OnTNumSlicesKillFocus(self, event):
        self.stackSettings.SetSeqLength(int(self.tNumSlices.GetValue()))
        self.UpdateDisp()

        event.Skip()

    def OnTStepSizeKillFocus(self, event):
        self.stackSettings.SetStepSize(float(self.tStepSize.GetValue()))
        self.UpdateDisp()

        event.Skip()

        

    def UpdateDisp(self):
        print 'seqd: update display'
        self.chPiezo.SetSelection(self.scanDirs.index(self.stackSettings.GetScanChannel()))

        if self.stackSettings.GetStartMode() == self.stackSettings.START_AND_END:
            self.bSt_end.SetValue(True)
            self.bMid_num.SetValue(False)
            
            self.tNumSlices.Enable(False)
            self.tStPos.Enable(True)
            self.tEndPos.Enable(True)
            self.bStartHere.Enable(True)
            self.bEndHere.Enable(True)

        else:
            self.bSt_end.SetValue(False)
            self.bMid_num.SetValue(True)

            self.tNumSlices.Enable(True)
            self.tStPos.Enable(False)
            self.tEndPos.Enable(False)
            self.bStartHere.Enable(False)
            self.bEndHere.Enable(False)

        self.tStPos.SetValue('%2.3f' % self.stackSettings.GetStartPos())
        self.tEndPos.SetValue('%2.3f' % self.stackSettings.GetEndPos())
        self.tStepSize.SetValue('%2.3f' % self.stackSettings.GetStepSize())
        self.tNumSlices.SetValue('%d' % self.stackSettings.GetSeqLength())
        self.stMemory.SetLabel('Mem: %2.1f MB' % (self.scope.cam.GetPicWidth()*self.scope.cam.GetPicHeight()*self.stackSettings.GetSeqLength()*2*1/(1024.0*1024.0)))


class SeqProgressPanel(wx.Panel):
    def __init__(self, zscanner):
        wx.Panel.__init__(self, zscanner.view)
        self.cancelled = False
        
        self.zs = zscanner
        

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)

        self.gProgress = wx.Gauge(self, -1, self.zs.nz)

        sizer1.Add(self.gProgress, 5, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        #btSizer = wx.StdDialogButtonSizer()

        #btn = wx.Button(self, wx.ID_CANCEL)
        #btn.Bind(wx.EVT_BUTTON, self.OnCancel)

        #btSizer.AddButton(btn)

        #btSizer.Realize()

        #sizer1.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer1)
        sizer1.Fit(self)

    #def OnCancel(self, event):
    #    self.cancelled = True
        #self.EndModal(wx.ID_CANCEL)

    def Tick(self, **kwargs):
        if not self.cancelled:
            self.gProgress.SetValue(self.zs.frameNum)
            return True
        else:
            return False