#!/usr/bin/python
# generated by wxGlade 0.3.3 on Mon Jun 14 06:48:07 2004

import wx
import wx.aui

from PYME.misc.auiFloatBook import AuiNotebookWithFloatingPages
import wx.lib.foldpanelbar as fpb
from PYME.misc.fbpIcons import *

import os
import sys

#import viewpanel
import PYME.cSMI as example
#import dCrop
#import logparser
import numpy

#import tables
import wx.py.crust
import pylab
import glob

from myviewpanel_numarray import MyViewPanel
import eventLogViewer

from PYME.Acquire import MetaDataHandler
from PYME.Analysis import MetaData
from PYME.Analysis.DataSources import HDFDataSource
from PYME.Analysis.DataSources import TQDataSource
from PYME.Analysis.LMVis import progGraphC as progGraph
from PYME.Acquire.mytimer import mytimer

from PYME.Analysis import piecewiseMapping

class DSViewFrame(wx.Frame):
    def __init__(self, parent=None, title='', dstack = None, log = None, filename = None, queueURI = None):
        wx.Frame.__init__(self,parent, -1, title,size=wx.Size(800,800))

        self.ds = dstack
        self.log = log

        self.saved = True

        #a timer object to update for us
        self.timer = mytimer()
        self.timer.Start(5000)

        self.numAnalysed = 0
        self.numEvents = 0
        self.fitResults = []

        if (dstack == None):
            if (filename == None):
                fdialog = wx.FileDialog(None, 'Please select Data Stack to open ...',
                    wildcard='*.h5', style=wx.OPEN|wx.HIDE_READONLY)
                succ = fdialog.ShowModal()
                if (succ == wx.ID_OK):
                    #self.ds = example.CDataStack(fdialog.GetPath().encode())
                    #self.ds = 
                    filename = fdialog.GetPath()
                    
                    #fn =
            if not filename == None:
                #self.h5file = tables.openFile(filename)
                #self.ds = self.h5file.root.ImageData
                if filename.startswith('QUEUE://'):
                    import Pyro.core
                    if queueURI == None:
                        self.tq = Pyro.core.getProxyForURI('PYRONAME://taskQueue')
                    else:
                        self.tq = Pyro.core.getProxyForURI(queueURI)

                    self.seriesName = filename[len('QUEUE://'):]

                    self.dataSource = TQDataSource.DataSource(self.seriesName, self.tq)
                    
                    self.mdh = MetaDataHandler.QueueMDHandler(self.tq, self.seriesName)
                    self.timer.WantNotification.append(self.dsRefresh)
                else:
                    self.dataSource = HDFDataSource.DataSource(filename, None)
                    if 'MetaData' in self.dataSource.h5File.root: #should be true the whole time
                        self.mdh = MetaData.TIRFDefault
                        self.mdh.copyEntriesFrom(MetaDataHandler.HDFMDHandler(self.dataSource.h5File))
                    else:
                        self.mdh = None
                        wx.MessageBox("Carrying on with defaults - no gaurantees it'll work well", 'ERROR: No metadata fond in file ...', wx.ERROR|wx.OK)
                        print "ERROR: No metadata fond in file ... Carrying on with defaults - no gaurantees it'll work well"

                    from PYME.ParallelTasks.relativeFiles import getRelFilename
                    self.seriesName = getRelFilename(filename)

                    

                self.ds = self.dataSource
                self.SetTitle(filename)
                self.saved = True
                #self.ds = example.CDataStack(filename)
                #self.SetTitle(fdialog.GetFilename())
                self.saved = True

        self.ID_WINDOW_TOP = 100
        self.ID_WINDOW_LEFT1 = 101
        self.ID_WINDOW_RIGHT1 = 102
        self.ID_WINDOW_BOTTOM = 103

        self._leftWindow1 = wx.SashLayoutWindow(self, 101, wx.DefaultPosition,
                                                wx.Size(250, 1000), wx.NO_BORDER |
                                                wx.SW_3D | wx.CLIP_CHILDREN)

        self._leftWindow1.SetDefaultSize(wx.Size(180, 1000))
        self._leftWindow1.SetOrientation(wx.LAYOUT_VERTICAL)
        self._leftWindow1.SetAlignment(wx.LAYOUT_LEFT)
        self._leftWindow1.SetSashVisible(wx.SASH_RIGHT, True)
        self._leftWindow1.SetExtraBorderSize(10)

        self._pnl = 0
                
        self._leftWindow1.Bind(wx.EVT_SASH_DRAGGED_RANGE, self.OnFoldPanelBarDrag,
                               id=100, id2=103)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        
        self.notebook1 = AuiNotebookWithFloatingPages(id=-1, parent=self, pos=wx.Point(0, 0), size=wx.Size(618,
              450), style=wx.aui.AUI_NB_TAB_SPLIT)

        self.notebook1.update = self.update


        self.vp = MyViewPanel(self.notebook1, self.ds)
        self.sh = wx.py.shell.Shell(id=-1,
              parent=self.notebook1, pos=wx.Point(0, 0), size=wx.Size(618, 451), style=0, locals=self.__dict__, 
              introText='Python SMI bindings - note that help, license etc below is for Python, not PySMI\n\n')
        self.sh.runfile(os.path.join(os.path.dirname(__file__),'fth5.py'))

        self.notebook1.AddPage(page=self.vp, select=True, caption='Data')
        self.notebook1.AddPage(page=self.sh, select=False, caption='Console')

        self.elv = eventLogViewer.eventLogPanel(self.notebook1, self.ds.getEvents(), self.mdh, [0, self.ds.getNumSlices()]);
        self.notebook1.AddPage(self.elv, 'Events')

        if 'ProtocolFocus' in self.elv.evKeyNames:
            pm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.md.Camera.CycleTime*1e-3, self.md.StartTime, self.md.Protocol.PiezoStartPos)
            self.elv.SetCharts([('Focus [um]', pm, 'ProtocolFocus'),])

        
        #self.notebook1.Split(0, wx.TOP)
        

        #self.sizer = wx.BoxSizer(wx.VERTICAL)
        #self.sizer.Add(self.notebook1, 1,wx.EXPAND,0)
        #self.SetAutoLayout(1)
        #self.SetSizer(self.sizer)
        #sizer.Fit(self)
        #sizer.SetSizeHints(self)

        # Menu Bar
        self.menubar = wx.MenuBar()
        self.SetMenuBar(self.menubar)
        tmp_menu = wx.Menu()
        #F_SAVE = wx.NewId()
        #F_CLOSE = wx.NewId()
        #tmp_menu.Append(wx.ID_SAVEAS, "Save As", "", wx.ITEM_NORMAL)
        tmp_menu.Append(wx.ID_CLOSE, "Close", "", wx.ITEM_NORMAL)
        self.menubar.Append(tmp_menu, "File")

        #mEdit = wx.Menu()
        #EDIT_CLEAR_SEL = wx.NewId()
        #EDIT_CROP = wx.NewId()
        #mEdit.Append(EDIT_CLEAR_SEL, "Reset Selection", "", wx.ITEM_NORMAL)
        #mEdit.Append(EDIT_CROP, "Crop", "", wx.ITEM_NORMAL)
        #self.menubar.Append(mEdit, "Edit")

        # Menu Bar end
        wx.EVT_MENU(self, wx.ID_SAVEAS, self.saveStack)
        #wx.EVT_MENU(self, wx.ID_CLOSE, self.menuClose)
        #wx.EVT_MENU(self, EDIT_CLEAR_SEL, self.clearSel)
        #wx.EVT_MENU(self, EDIT_CROP, self.crop)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
		
        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)

        self.CreateFoldPanel()

        self.Layout()
        self.update()


    def OnSize(self, event):
        wx.LayoutAlgorithm().LayoutWindow(self, self.notebook1)
        self.Refresh()
        event.Skip()

    def OnFoldPanelBarDrag(self, event):

        if event.GetDragStatus() == wx.SASH_STATUS_OUT_OF_RANGE:
            return

        if event.GetId() == self.ID_WINDOW_LEFT1:
            self._leftWindow1.SetDefaultSize(wx.Size(event.GetDragRect().width, 1000))


        # Leaves bits of itself behind sometimes
        wx.LayoutAlgorithm().LayoutWindow(self, self.notebook1)
        self.notebook1.Refresh()

        event.Skip()

    def CreateFoldPanel(self):

        # delete earlier panel
        self._leftWindow1.DestroyChildren()

        # recreate the foldpanelbar

        self._pnl = fpb.FoldPanelBar(self._leftWindow1, -1, wx.DefaultPosition,
                                     wx.Size(-1,-1), fpb.FPB_DEFAULT_STYLE,0)

        self.Images = wx.ImageList(16,16)
        self.Images.Add(GetExpandedIconBitmap())
        self.Images.Add(GetCollapsedIconBitmap())

        self.GenPointFindingPanel()
        self.GenAnalysisPanel()
        self.GenFitStatusPanel()


        #item = self._pnl.AddFoldPanel("Filters", False, foldIcons=self.Images)
        #item = self._pnl.AddFoldPanel("Visualisation", False, foldIcons=self.Images)
        wx.LayoutAlgorithm().LayoutWindow(self, self.notebook1)
        self.Refresh()
        self.notebook1.Refresh()

    def GenAnalysisPanel(self):
        item = self._pnl.AddFoldPanel("Analysis", collapsed=False,
                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)
        
        #find out what fit factories we have
        import PYME.Analysis.FitFactories
        fitFactoryList = glob.glob(PYME.Analysis.FitFactories.__path__[0] + '/[a-zA-Z]*.py')
        fitFactoryList = [os.path.split(p)[-1][:-3] for p in fitFactoryList]

        self.fitFactories = []
        for ff in fitFactoryList:
            try:
                fm = __import__('PYME.Analysis.FitFactories.' + ff, fromlist=['PYME', 'Analysis', 'FitFactories'])
                if 'FitResultsDType' in dir(fm):
                    self.fitFactories.append(ff)
            except:
                pass

        #print fitFactoryList
        #print self.fitFactories

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Type:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.cFitType = wx.Choice(pan, -1, choices = self.fitFactories, size=(120, -1))
        self.cFitType.SetSelection(self.fitFactories.index('LatGaussFitFR'))

        hsizer.Add(self.cFitType, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        vsizer.Add(hsizer, 0,wx.ALL, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Start at:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tStartAt = wx.TextCtrl(pan, -1, value='%d' % self.vp.zp, size=(40, -1))
        
        hsizer.Add(self.tStartAt, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        vsizer.Add(hsizer, 0,wx.ALL, 0)
        
        pan.SetSizer(vsizer)
        vsizer.Fit(pan)

        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        self.cbDrift = wx.CheckBox(item, -1, 'Estimate Drift')
        self.cbDrift.SetValue(False)

        self._pnl.AddFoldPanelWindow(item, self.cbDrift, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)
        
        bGo = wx.Button(item, -1, 'Go')
            

        bGo.Bind(wx.EVT_BUTTON, self.OnGo)
        self._pnl.AddFoldPanelWindow(item, bGo, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

    def OnGo(self, event):
        threshold = float(self.tThreshold.GetValue())
        startAt = int(self.tStartAt.GetValue())
        driftEst = self.cbDrift.GetValue()
        fitMod = self.cFitType.GetStringSelection()

        if not driftEst:
            self.sh.run('pushImages(%d, %f, "%s")' % (startAt, threshold, fitMod))
        else:
            self.sh.run('pushImagesD(%d, %f)' % (startAt, threshold))

        from PYME.Analysis.LMVis import gl_render
        self.glCanvas = gl_render.LMGLCanvas(self.notebook1)
        self.glCanvas.cmap = pylab.cm.gist_rainbow

        self.notebook1.AddPage(page=self.glCanvas, select=True, caption='VisLite')

        xsc = self.ds.shape[0]*1.0e3*self.mdh.getEntry('voxelsize.x')/self.glCanvas.Size[0]
        ysc = self.ds.shape[1]*1.0e3*self.mdh.getEntry('voxelsize.y')/ self.glCanvas.Size[1]

        if xsc > ysc:
            self.glCanvas.setView(0, xsc*self.glCanvas.Size[0], 0, xsc*self.glCanvas.Size[1])
        else:
            self.glCanvas.setView(0, ysc*self.glCanvas.Size[0], 0, ysc*self.glCanvas.Size[1])

        self.timer.WantNotification.append(self.analRefresh)
        self.bGo.Enable(False)

    def GenPointFindingPanel(self):
        item = self._pnl.AddFoldPanel("Point Finding", collapsed=False,
                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Threshold:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tThreshold = wx.TextCtrl(pan, -1, value='0.9', size=(40, -1))

        hsizer.Add(self.tThreshold, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        pan.SetSizer(hsizer)
        hsizer.Fit(pan)

        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        bTest = wx.Button(item, -1, 'Test')


        bTest.Bind(wx.EVT_BUTTON, self.OnTest)
        self._pnl.AddFoldPanelWindow(item, bTest, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

    def OnTest(self, event):
        threshold = float(self.tThreshold.GetValue())
        startAt = int(self.tStartAt.GetValue())
        driftEst = self.cbDrift.GetValue()

        #if not driftEst:
        self.sh.run('testFrames(%f)' % (threshold))
        #else:
        #    self.sh.run('pushImagesD(%d, %f)' % (startAt, threshold)

    def GenFitStatusPanel(self):
        item = self._pnl.AddFoldPanel("Fit Status", collapsed=False,
                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1, size = (150, 300))

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.progPan = progGraph.progPanel(pan, self.fitResults, size=(150, 300))

        hsizer.Add(self.progPan, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        pan.SetSizer(hsizer)
        hsizer.Fit(pan)
        
        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)


    def update(self):
        self.vp.imagepanel.Refresh()
        self.statusbar.SetStatusText('Slice No: (%d/%d)    Frames Analysed: %d    Events detected: %d' % (self.vp.zp, self.vp.ds.shape[2], self.numAnalysed, self.numEvents))

    def saveStack(self, event=None):
        fdialog = wx.FileDialog(None, 'Save Data Stack as ...',
            wildcard='*.kdf', style=wx.SAVE|wx.HIDE_READONLY)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            self.ds.SaveToFile(fdialog.GetPath().encode())
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
        pylab.close('all')
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

    def dsRefresh(self):
        zp = self.vp.zp #save z -position
        self.vp.SetDataStack(self.ds)
        self.vp.zp = zp #restore z position
        self.elv.SetEventSource(self.ds.getEvents())
        self.elv.SetRange([0, self.ds.getNumSlices()])
        
        if 'ProtocolFocus' in self.elv.evKeyNames:
            self.zm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.md.Camera.CycleTime, self.md.StartTime, self.md.Protocol.PiezoStartPos)
            self.elv.SetCharts([('Focus [um]', self.zm, 'ProtocolFocus'),])

        self.update()

    def analRefresh(self):
        newNumAnalysed = self.tq.getNumberTasksCompleted(self.seriesName)
        if newNumAnalysed > self.numAnalysed:
            self.numAnalysed = newNumAnalysed
            newResults = self.tq.getQueueData(self.seriesName, 'FitResults', len(self.fitResults))
            if len(newResults) > 0:
                if len(self.fitResults) == 0:
                    self.fitResults = newResults
                else:
                    self.fitResults = numpy.concatenate((self.fitResults, newResults))
                self.progPan.fitResults = self.fitResults

                self.numEvents = len(self.fitResults)
                if 'zm' in dir(self): #we have z info
                    z = self.zm(self.fitResults['tIndex'].astype('f')).astype('f')
                    self.glCanvas.setPoints(self.fitResults['fitResults']['x0'],self.fitResults['fitResults']['y0'],z)
                    self.glCanvas.setCLim((z.min(), z.max()))
                else:
                    self.glCanvas.setPoints(self.fitResults['fitResults']['x0'],self.fitResults['fitResults']['y0'],self.fitResults['tIndex'].astype('f'))
                    self.glCanvas.setCLim((0, self.numAnalysed))

            if (self.tq.getNumberOpenTasks(self.seriesName) + self.tq.getNumberTasksInProgress(self.seriesName)) == 0 and 'SpoolingFinished' in self.mdh.getEntryNames():
                self.statusbar.SetBackgroundColour(wx.GREEN)
                self.statusbar.Refresh()
            self.progPan.draw()
            self.Refresh()
            self.update()




class MyApp(wx.App):
    def OnInit(self):
        #wx.InitAllImageHandlers()
        if (len(sys.argv) == 2):
            vframe = DSViewFrame(None, sys.argv[1], filename=sys.argv[1])
        elif (len(sys.argv) == 3):
            vframe = DSViewFrame(None, sys.argv[1], filename=sys.argv[1], queueURI=sys.argv[2])
        else:
            vframe = DSViewFrame(None, '')           

        self.SetTopWindow(vframe)
        vframe.Show(1)

        #crFrame = wx.py.shell.ShellFrame(parent = vframe, locals = vframe.__dict__)
        #crFrame.Show()
        #print __file__
        #crFrame.shell.runfile(os.path.join(os.path.dirname(__file__),'fth5.py'))
        return 1

# end of class MyApp

def main():
    app = MyApp(0)
    app.MainLoop()


if __name__ == "__main__":
    main()
