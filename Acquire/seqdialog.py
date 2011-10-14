#!/usr/bin/python

##################
# seqdialog.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

#Boa:Dialog:seqDialog

import wx

import simplesequenceaquisator

#redefine wxFrame with a version that hides when someone tries to close it

#dirty trick, but lets the Boa gui builder still work with frames we do this to

#NB must come after 'from wx.... import *' !!!

from noclosefr import * 

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

] = map(lambda _init_ctrls: wx.NewId(), range(18))



class seqPanel(wx.Panel):

    def _init_ctrls(self, prnt):

        # generated method, don't edit

        wx.Panel.__init__(self, id=wxID_SEQDIALOG, parent=prnt)

        #self.SetClientSize(wx.Size(348, 167))

        #self.SetBackgroundColour(wx.Colour(209, 208, 203))



        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)



        sPiezo = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Piezo Channel'), wx.HORIZONTAL)



        self.chPiezo = wx.Choice(self, -1, choices=[], size=(-1,-1))

        self.chPiezo.Bind(wx.EVT_CHOICE, self.OnChPiezoChoice)



        sPiezo.Add(self.chPiezo, 1,wx.ALIGN_CENTER_VERTICAL,0)

        hsizer.Add(sPiezo, 1, wx.EXPAND|wx.RIGHT, 5)





        sType = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Type'), wx.VERTICAL)



        self.bSt_end = wx.RadioButton(self, -1,'Start and End', size=(-1,-1))

        self.bSt_end.SetValue(True)

        self.bSt_end.Bind(wx.EVT_RADIOBUTTON, self.OnBSt_endRadiobutton)



        sType.Add(self.bSt_end, 1,0,0)



        self.bMid_num = wx.RadioButton(self, -1, 'Middle and #', size=(-1,-1))

        self.bMid_num.SetValue(False)

        self.bMid_num.Bind(wx.EVT_RADIOBUTTON, self.OnBMid_numRadiobutton)



        sType.Add(self.bMid_num, 1,0,0)

        hsizer.Add(sType, 1, wx.EXPAND, 0)



        vsizer.Add(hsizer, 1, wx.EXPAND, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)



        sStart = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Start Pos [\u03BCm]'), wx.HORIZONTAL)



        self.tStPos = wx.TextCtrl(self, -1, value='40', size=(40,-1))

        self.tStPos.Bind(wx.EVT_KILL_FOCUS, self.OnTStPosKillFocus)

        sStart.Add(self.tStPos, 2, wx.RIGHT, 5)



        self.bStartHere = wx.Button(self, -1,'Here', size=(10,10))

        self.bStartHere.Bind(wx.EVT_BUTTON, self.OnBStartHereButton)

        sStart.Add(self.bStartHere, 1, wx.EXPAND, 0)



        hsizer.Add(sStart, 1, wx.RIGHT, 5)





        sEnd = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'End Pos [\u03BCm]'), wx.HORIZONTAL)



        self.tEndPos = wx.TextCtrl(self, -1, value='40', size=(40,-1))

        self.tEndPos.Bind(wx.EVT_KILL_FOCUS, self.OnTEndPosKillFocus)

        sEnd.Add(self.tEndPos, 2, wx.RIGHT, 5)



        self.bEndHere = wx.Button(self, -1,'Here', size=(10,10))

        self.bEndHere.Bind(wx.EVT_BUTTON, self.OnBEndHereButton)

        sEnd.Add(self.bEndHere, 1, wx.EXPAND, 0)



        hsizer.Add(sEnd, 1, 0, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)





        sStep = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Step Size [\u03BCm]'), wx.HORIZONTAL)



        self.tStepSize = wx.TextCtrl(self, -1, value='0.2', size=(40,-1))

        self.tStepSize.Bind(wx.EVT_KILL_FOCUS, self.OnTStepSizeKillFocus)

        sStep.Add(self.tStepSize, 1, 0, 0)



        hsizer.Add(sStep, 1, wx.RIGHT, 5)





        sNSlices = wx.StaticBoxSizer(wx.StaticBox(self, -1, '# Slices'), wx.HORIZONTAL)



        self.tNumSlices = wx.TextCtrl(self, -1, value='100', size=(40,-1))

        self.tNumSlices.Bind(wx.EVT_KILL_FOCUS, self.OnTNumSlicesKillFocus)

        sNSlices.Add(self.tNumSlices, 1, 0, 0)



        hsizer.Add(sNSlices, 1, 0, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND, 0)

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

        

        if not ('sa' in self.scope.__dict__):

            self.scope.sa = simplesequenceaquisator.SimpleSequenceAquisitor(self.scope.chaninfo, self.scope.cam, self.scope.shutters, self.scope.piezos)

            

        for pz in self.scope.piezos:

            self.chPiezo.Append(pz[2])

        self.UpdateDisp()   

        

    def OnBEndHereButton(self, event):

        self.scope.sa.SetEndPos(self.scope.piezos[self.scope.sa.GetScanChannel()][0].GetPos(self.scope.piezos[self.scope.sa.GetScanChannel()][1]))

        self.UpdateDisp()

        #event.Skip()

    def OnBStartHereButton(self, event):

        self.scope.sa.SetStartPos(self.scope.piezos[self.scope.sa.GetScanChannel()][0].GetPos(self.scope.piezos[self.scope.sa.GetScanChannel()][1]))

        self.UpdateDisp()

        #event.Skip()

    def OnBStartButton(self, event):

        res = self.scope.sa.Verify()

        if res[0]:

            self.scope.pa.stop()

            #try:

            self.scope.sa.Prepare()

            #except:

            #    dialog = wxMessageDialog(None, 'The most likely reason is a lack of memory \nTry the following: Close any open aquisitions, Chose a ROI, Delete unnecessary channels, or decrease the # of slices', "Could not start aquisition", wx.OK)

            #    dialog.ShowModal()

            #    self.scope.sa.ds=[]

            #    self.scope.pa.Prepare(True)

            #    self.scope.pa.start()

            self.scope.sa.WantFrameNotification=[]

            self.scope.sa.WantFrameNotification.append(self.scope.aq_refr)

            self.scope.sa.WantStopNotification=[]

            self.scope.sa.WantStopNotification.append(self.scope.aq_end)

            self.scope.sa.start()

            self.scope.pb = wx.ProgressDialog('Aquisition in progress ...', 'Slice 1 of %d' % self.scope.sa.ds.getDepth(), self.scope.sa.ds.getDepth(), style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|wx.PD_REMAINING_TIME|wx.PD_CAN_ABORT)

                

            

                

                

            

        else:

            dialog = wx.MessageDialog(None, res[2] + ' (%2.3f)'% res[3], "Parameter Error", wx.OK)

            dialog.ShowModal()

            

            if res[1] == 'StepSize':

                self.tStepSize.SetFocus()

            elif (self.scope.sa.GetStartMode() == self.scope.sa.CENTRE_AND_LENGTH):

                self.tNumSlices.SetFocus()

            elif (res[1] == 'StartPos'):

                self.tStPos.SetFocus()

            else:

                self.tEndPos.SetFocus() 

                 

        

        #event.Skip()
    def OnBSingle(self, event):
        self.OnBLive(event, True)
        
    def OnSingleEnd(self):
        wx.MessageBox('Acquisition Finished')
        self.scope.zs.WantFrameNotification.remove(self.OnSingleEnd)
        self.bStart.Enable(True)
        self.bLive.SetLabel('Live')
        
    def OnBLive(self, event, single=False):
        import zScanner
        
        if 'zs' in dir(self.scope) and self.scope.zs.running: #stop
            self.scope.zs.Stop()
            self.bLive.SetLabel('Live')
            self.bStart.Enable(True)
            
        else:
            res = self.scope.sa.Verify()
            
            if res[0]:                
                
                self.scope.zs = zScanner.getBestScanner(self.scope)
                
                if not isinstance(self.scope.zs, zScanner.wavetableZScanner):
                    pz = self.scope.sa.piezos[self.scope.sa.GetScanChannel()][0]
                    if 'MAXWAVEPOINTS' in dir(pz):
                        msg = MSG_LONG_WAVETABLE % pz.MAXWAVEPOINTS
                    else:
                        msg = MSG_NO_WAVETABLE
                        
                    dialog = wx.MessageDialog(None, msg, "Warning", wx.OK)
                    dialog.ShowModal()
                
                if single:
                    self.scope.zs.WantFrameNotification.append(self.OnSingleEnd)
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
    
                elif (self.scope.sa.GetStartMode() == self.scope.sa.CENTRE_AND_LENGTH):
                    self.tNumSlices.SetFocus()
    
                elif (res[1] == 'StartPos'):
                    self.tStPos.SetFocus()
    
                else:
                    self.tEndPos.SetFocus() 
        
            
    

    def OnChPiezoChoice(self, event):

        self.scope.sa.SetScanChannel(self.chPiezo.GetSelection())

        self.UpdateDisp()

        #event.Skip()

    def OnBSt_endRadiobutton(self, event):

        self.scope.sa.SetStartMode(1)

        self.UpdateDisp()

        #event.Skip()

    def OnBMid_numRadiobutton(self, event):

        self.scope.sa.SetStartMode(0)

        self.UpdateDisp()

        #event.Skip()

    def OnTEndPosKillFocus(self, event):

        self.scope.sa.SetEndPos(float(self.tEndPos.GetValue()))

        self.UpdateDisp()

        #event.Skip()

    def OnTStPosKillFocus(self, event):

        self.scope.sa.SetStartPos(float(self.tStPos.GetValue()))

        self.UpdateDisp()

        #event.Skip()

    def OnTNumSlicesKillFocus(self, event):

        self.scope.sa.SetSeqLength(int(self.tNumSlices.GetValue()))

        self.UpdateDisp()

        #event.Skip()

    def OnTStepSizeKillFocus(self, event):

        self.scope.sa.SetStepSize(float(self.tStepSize.GetValue()))

        self.UpdateDisp()

        #event.Skip()

        

    def UpdateDisp(self):

        self.chPiezo.SetSelection(self.scope.sa.GetScanChannel())

            

        if self.scope.sa.GetStartMode() == self.scope.sa.START_AND_END:

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

        

        self.tStPos.SetValue('%2.3f' % self.scope.sa.GetStartPos())

        self.tEndPos.SetValue('%2.3f' % self.scope.sa.GetEndPos())

        self.tStepSize.SetValue('%2.3f' % self.scope.sa.GetStepSize())

        self.tNumSlices.SetValue('%d' % self.scope.sa.GetSeqLength())

        self.stMemory.SetLabel('Mem: %2.1f MB' % (self.scope.cam.GetPicWidth()*self.scope.cam.GetPicHeight()*self.scope.sa.GetSeqLength()*2*self.scope.sa.getReqMemChans(self.scope.sa.chans.cols)/(1024.0*1024.0)))

