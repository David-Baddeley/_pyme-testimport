#!/usr/bin/python

##################
# dsviewer.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################


raise RuntimeError('dsviewer is deprecated - please do not use!')

# generated by wxGlade 0.3.3 on Mon Jun 14 06:48:07 2004
import wx
import sys
sys.path.append(".")
#import viewpanel
import PYME.cSMI as example
import dCrop
import logparser
from PYME.FileUtils import saveTiffStack
from myviewpanel import MyViewPanel
import os

from PYME import cSMI
import Image

class DSViewFrame(wx.Frame):
    def __init__(self, parent=None, title='', dstack = None, log = None, filename = None, filedir=""):
        wx.Frame.__init__(self,parent, -1, title)
        self.ds = dstack
        self.log = log
        self.saved = False
        self.filedir = filedir
        if (dstack == None):
            if (filename == None):
                fdialog = wx.FileDialog(None, 'Please select Data Stack to open ...',
                    wildcard='*.kdf', style=wx.OPEN|wx.HIDE_READONLY)
                succ = fdialog.ShowModal()
                if (succ == wx.ID_OK):
                    self.ds = example.CDataStack(fdialog.GetPath().encode())
                    self.SetTitle(fdialog.GetFilename())
                    self.saved = True
                    #fn =
            else:
                self.ds = example.CDataStack(filename)
                self.SetTitle(filename)
                self.saved = True
        self.vp = MyViewPanel(self, self.ds)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.vp, 1,wx.EXPAND,0)
        self.SetAutoLayout(1)
        self.SetSizer(sizer)
        sizer.Fit(self)
        #sizer.SetSizeHints(self)
        # Menu Bar
        self.menubar = wx.MenuBar()
        self.SetMenuBar(self.menubar)
        tmp_menu = wx.Menu()
        #F_SAVE = wx.NewId()
        #F_CLOSE = wx.NewId()
        tmp_menu.Append(wx.ID_SAVEAS, "Save As", "", wx.ITEM_NORMAL)
        tmp_menu.Append(wx.ID_CLOSE, "Close", "", wx.ITEM_NORMAL)
        self.menubar.Append(tmp_menu, "File")
        mEdit = wx.Menu()
        EDIT_CLEAR_SEL = wx.NewId()
        EDIT_CROP = wx.NewId()
        mEdit.Append(EDIT_CLEAR_SEL, "Reset Selection", "", wx.ITEM_NORMAL)
        mEdit.Append(EDIT_CROP, "Crop", "", wx.ITEM_NORMAL)
        self.menubar.Append(mEdit, "Edit")
        # Menu Bar end
        wx.EVT_MENU(self, wx.ID_SAVEAS, self.saveStack)
        wx.EVT_MENU(self, wx.ID_CLOSE, self.menuClose)
        wx.EVT_MENU(self, EDIT_CLEAR_SEL, self.clearSel)
        wx.EVT_MENU(self, EDIT_CROP, self.crop)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
		
        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)
        self.Layout()
        self.update()
    def update(self):
        self.vp.imagepanel.Refresh()
        self.statusbar.SetStatusText('Slice No: (%d/%d)    x: %d  y: %d' % (self.ds.getZPos(), self.ds.getDepth(), self.ds.getXPos(), self.ds.getYPos()))
    def saveStack(self, event=None):
        fdialog = wx.FileDialog(None, 'Save Data Stack as ...', defaultDir=self.filedir,
            wildcard='KDF (*.kdf)|*.kdf|TIFF (*.tif)|*.tif', style=wx.SAVE|wx.HIDE_READONLY)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            fpath = fdialog.GetPath()
            if os.path.splitext(fpath)[1] == '.kdf':
                self.ds.SaveToFile(fdialog.GetPath().encode())
            else:
                #save using PIL
                if self.ds.getNumChannels() == 1:
                    #im = Image.fromarray(cSMI.CDataStack_AsArray(self.ds, 0), 'I;16')
                    #im.save(fpath)
                    im = cSMI.CDataStack_AsArray(self.ds, 0).squeeze()
                    saveTiffStack.writeTiff(im, fpath)
                else:
                    fst, ext = os.path.splitext(fpath)
                    for i in range(self.ds.getNumChannels()):
                        #im = Image.fromarray(cSMI.CDataStack_AsArray(self.ds, i), 'I;16')
                        #im.save(fst + '_%d'%i + ext)

                        im = cSMI.CDataStack_AsArray(self.ds, i).squeeze()
                        saveTiffStack.writeTiff(im, fst + '_%d'%i + ext)


            if not (self.log == None):
                lw = logparser.logwriter()
                s = lw.write(self.log)
                log_f = file('%s.log' % fdialog.GetPath().split('.')[0], 'w')
                log_f.write(s)
                log_f.close()
                
            self.SetTitle(fdialog.GetFilename())
            self.saved = True
    def menuClose(self, event):
        self.Close()
    def OnCloseWindow(self, event):
        if (not self.saved):
            dialog = wx.MessageDialog(self, "Save data stack?", "pySMI", wx.YES_NO|wx.CANCEL)
            ans = dialog.ShowModal()
            if(ans == wx.ID_YES):
                self.saveStack()
                self.Destroy()
            elif (ans == wx.ID_NO):
                self.Destroy()
            else: #wxID_CANCEL:   
                if (not event.CanVeto()): 
                    self.Destroy()
                else:
                    event.Veto()
        else:
            self.Destroy()
			
    def clearSel(self, event):
        self.vp.ResetSelection()
        self.vp.Refresh()
        
    def crop(self, event):
        cd = dCrop.dCrop(self, self.vp)
        if cd.ShowModal():
            ds2 = example.CDataStack(self.ds, cd.x1, cd.y1, cd.z1, cd.x2, cd.y2, cd.z2, cd.chs)
            dvf = DSViewFrame(self.GetParent(), '--cropped--', ds2)
            dvf.Show()

class MyApp(wx.App):
    def OnInit(self):
        #wx.InitAllImageHandlers()
        print sys.argv
        if (len(sys.argv) > 1):
            vframe = DSViewFrame(None, sys.argv[1], filename=sys.argv[1])
        else:
            vframe = DSViewFrame(None, '')           
        self.SetTopWindow(vframe)
        vframe.Show(1)
        return 1
# end of class MyApp
if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()

