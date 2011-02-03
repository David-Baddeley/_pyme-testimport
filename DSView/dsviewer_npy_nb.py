#!/usr/bin/python
##################
# dsviewer_npy_nb.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import wx
import wx.lib.agw.aui as aui

import PYME.misc.autoFoldPanel as afp
from PYME.misc.auiFloatBook import AuiNotebookWithFloatingPages
from PYME.FileUtils import h5ExFrames

import os
import sys

import PYME.cSMI as example
import numpy

import tables
import wx.py.crust
import pylab

from arrayViewPanel import ArraySettingsAndViewPanel
from PYME.Analysis.LMVis import recArrayView
import eventLogViewer

from PYME.Acquire import MetaDataHandler
from PYME.Analysis import MetaData
from PYME.Analysis import MetadataTree
from PYME.Analysis.DataSources import HDFDataSource
from PYME.Analysis.DataSources import TQDataSource
#from PYME.Analysis.DataSources import TiffDataSource
from PYME.FileUtils import readTiff
from PYME.Analysis.LMVis import inpFilt

from PYME.Analysis import piecewiseMapping


class DSViewFrame(wx.Frame):
    def __init__(self, parent=None, title='', dstack = None, log = None, mdh = None, filename = None, queueURI = None, mode='LM'):
        wx.Frame.__init__(self,parent, -1, title,size=wx.Size(800,800), pos=(1100, 300))

        self.ds = dstack
        self.mdh = mdh
        #self.log = log

        self.saved = False

        self.mode = mode

        self.timer = mytimer()
        self.timer.Start(10000)

        self.fitResults = []

        if (dstack == None):
            self.Load(filename)

        self._mgr = aui.AuiManager(agwFlags = aui.AUI_MGR_DEFAULT | aui.AUI_MGR_AUTONB_NO_CAPTION)
        atabstyle = self._mgr.GetAutoNotebookStyle()
        self._mgr.SetAutoNotebookStyle((atabstyle ^ aui.AUI_NB_BOTTOM) | aui.AUI_NB_TOP)
        # tell AuiManager to manage this frame
        self._mgr.SetManagedWindow(self)

                
        self.notebook1 = AuiNotebookWithFloatingPages(id=-1, parent=self, pos=wx.Point(0, 0), size=wx.Size(618,
              450), style=wx.aui.AUI_NB_TAB_SPLIT)
        self.notebook1.update = self.update

        self.vp = ArraySettingsAndViewPanel(self.notebook1, self.ds)

        self.mainWind = self

        self.sh = wx.py.shell.Shell(id=-1,
              parent=self.notebook1, pos=wx.Point(0, 0), size=wx.Size(618, 451), style=0, locals=self.__dict__, 
              introText='Python SMI bindings - note that help, license etc below is for Python, not PySMI\n\n')

        self.notebook1.AddPage(page=self.vp, select=True, caption='Data')
        self.notebook1.AddPage(page=self.sh, select=False, caption='Console')

        self.mdv = MetadataTree.MetadataPanel(self.notebook1, self.mdh)
        self.notebook1.AddPage(page=self.mdv, select=False, caption='Metadata')

        
        # Menu Bar
        self.menubar = wx.MenuBar()
        self.SetMenuBar(self.menubar)
        tmp_menu = wx.Menu()
        tmp_menu.Append(wx.ID_SAVEAS, "Export", "", wx.ITEM_NORMAL)

        #a submenu for modules to hook and install saving functions into
        self.save_menu = wx.Menu()
        tmp_menu.AppendMenu(-1, 'Save &Results', self.save_menu)
        
        tmp_menu.Append(wx.ID_CLOSE, "Close", "", wx.ITEM_NORMAL)
        self.menubar.Append(tmp_menu, "File")

        #'extras' menu for modules to install stuff into
        self.mExtras = wx.Menu()
        self.menubar.Append(self.mExtras, "&Extras")

        # Menu Bar end
        #wx.EVT_MENU(self, wx.ID_SAVEAS, self.extractFrames)
        wx.EVT_MENU(self, wx.ID_SAVEAS, self.OnExport)
        wx.EVT_CLOSE(self, self.OnCloseWindow)

		
        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)

        self.InitEvents()

        if self.mode == 'LM':
            from modules import LMAnalysis
            self.LMAnalyser = LMAnalysis.LMAnalyser(self)

        from modules import deconvolution, tiling
        self.deconvolver = deconvolution.deconvolver(self)
        self.tiler = tiling.tiler(self)

        self._leftWindow1 = wx.Panel(self, -1, size = wx.Size(180, 1000))
        self._pnl = 0
        self.CreateFoldPanel()
        
        self._mgr.AddPane(self._leftWindow1, aui.AuiPaneInfo().
                          Name("sidebar").Left().CloseButton(False).CaptionVisible(False))

        self._mgr.AddPane(self.notebook1, aui.AuiPaneInfo().
                          Name("shell").Centre().CaptionVisible(False).CloseButton(False))

        self._mgr.Update()

        self.Layout()

        if 'Protocol.DataStartsAt' in self.mdh.getEntryNames():
            self.vp.zp = self.mdh.getEntry('Protocol.DataStartsAt')
        else:
            self.vp.zp = self.mdh.getEntry('EstimatedLaserOnFrameNo')

        self.vp.Refresh()
        self.update()

    def LoadQueue(self, filename):
        import Pyro.core
        if queueURI == None:
            if 'PYME_TASKQUEUENAME' in os.environ.keys():
                taskQueueName = os.environ['PYME_TASKQUEUENAME']
            else:
                taskQueueName = 'taskQueue'
            self.tq = Pyro.core.getProxyForURI('PYRONAME://' + taskQueueName)
        else:
            self.tq = Pyro.core.getProxyForURI(queueURI)

        self.seriesName = filename[len('QUEUE://'):]

        self.dataSource = TQDataSource.DataSource(self.seriesName, self.tq)

        self.mdh = MetaDataHandler.QueueMDHandler(self.tq, self.seriesName)
        self.timer.WantNotification.append(self.dsRefresh)

        self.events = self.dataSource.getEvents()

    def Loadh5(self, filename):
        self.dataSource = HDFDataSource.DataSource(filename, None)
        if 'MetaData' in self.dataSource.h5File.root: #should be true the whole time
            self.mdh = MetaData.TIRFDefault
            self.mdh.copyEntriesFrom(MetaDataHandler.HDFMDHandler(self.dataSource.h5File))
        else:
            self.mdh = MetaData.TIRFDefault
            wx.MessageBox("Carrying on with defaults - no gaurantees it'll work well", 'ERROR: No metadata found in file ...', wx.OK)
            print "ERROR: No metadata fond in file ... Carrying on with defaults - no gaurantees it'll work well"

        MetaData.fillInBlanks(self.mdh, self.dataSource)

        from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        #try and find a previously performed analysis
        fns = filename.split(os.path.sep)
        cand = os.path.sep.join(fns[:-2] + ['analysis',] + fns[-2:]) + 'r'
        print cand
        if os.path.exists(cand):
            h5Results = tables.openFile(cand)

            if 'FitResults' in dir(h5Results.root):
                self.fitResults = h5Results.root.FitResults[:]
                self.resultsSource = inpFilt.h5rSource(h5Results)

                self.resultsMdh = MetaData.TIRFDefault
                self.resultsMdh.copyEntriesFrom(MetaDataHandler.HDFMDHandler(h5Results))

        self.events = self.dataSource.getEvents()

    def LoadKdf(self, filename):
        import PYME.cSMI as cSMI
        self.dataSource = cSMI.CDataStack_AsArray(cSMI.CDataStack(filename), 0).squeeze()
        self.mdh = MetaData.TIRFDefault

        try: #try and get metadata from the .log file
            lf = open(os.path.splitext(filename)[0] + '.log')
            from PYME.DSView import logparser
            lp = logparser.logparser()
            log = lp.parse(lf.read())
            lf.close()

            self.mdh.setEntry('voxelsize.z', log['PIEZOS']['Stepsize'])
        except:
            pass

        from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'psf'

    def LoadPSF(self, filename):
        self.dataSource, vox = numpy.load(filename)
        self.mdh = MetaData.ConfocDefault

        self.mdh.setEntry('voxelsize.x', vox.x)
        self.mdh.setEntry('voxelsize.y', vox.y)
        self.mdh.setEntry('voxelsize.z', vox.z)


        from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'psf'

    def LoadTiff(self, filename):
        #self.dataSource = TiffDataSource.DataSource(filename, None)
        self.dataSource = readTiff.read3DTiff(filename)

        xmlfn = os.path.splitext(filename)[0] + '.xml'
        if os.path.exists(xmlfn):
            self.mdh = MetaData.TIRFDefault
            self.mdh.copyEntriesFrom(MetaDataHandler.XMLMDHandler(xmlfn))
        else:
            self.mdh = MetaData.ConfocDefault

            from PYME.DSView.voxSizeDialog import VoxSizeDialog

            dlg = VoxSizeDialog(self)
            dlg.ShowModal()

            self.mdh.setEntry('voxelsize.x', dlg.GetVoxX())
            self.mdh.setEntry('voxelsize.y', dlg.GetVoxY())
            self.mdh.setEntry('voxelsize.z', dlg.GetVoxZ())


        from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'blob'

    def Load(self, filename=None):
        if (filename == None):
            fdialog = wx.FileDialog(None, 'Please select Data Stack to open ...',
                wildcard='PYME Data|*.h5|TIFF files|*.tif|KDF files|*.kdf', style=wx.OPEN)
            succ = fdialog.ShowModal()
            if (succ == wx.ID_OK):
                filename = fdialog.GetPath()

        if not filename == None:
            if filename.startswith('QUEUE://'):
                self.LoadQueue(filename)
            elif filename.endswith('.h5'):
                self.Loadh5(filename)
            elif filename.endswith('.kdf'):
                self.LoadKdf(filename)
            elif filename.endswith('.psf'): #psf
                self.LoadPSF(filename)
            else: #try tiff
                self.LoadTiff(filename)


            self.ds = self.dataSource
            self.SetTitle(filename)
            self.saved = True

    def InitEvents(self):
        if 'events' in dir(self):
            st = self.mdh.getEntry('StartTime')
            if 'EndTime' in self.mdh.getEntryNames():
                et = self.mdh.getEntry('EndTime')
            else:
                et = piecewiseMapping.framesToTime(self.ds.getNumSlices(), self.events, self.mdh)
            self.elv = eventLogViewer.eventLogTPanel(self.notebook1, self.events, self.mdh, [0, et-st]);
            self.notebook1.AddPage(self.elv, 'Events')

            charts = []

            if 'ProtocolFocus' in self.elv.evKeyNames:
                self.zm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), self.mdh.getEntry('Protocol.PiezoStartPos'))
                charts.append(('Focus [um]', self.zm, 'ProtocolFocus'))

            if 'ScannerXPos' in self.elv.evKeyNames:
                x0 = 0
                if 'Positioning.Stage_X' in self.mdh.getEntryNames():
                    x0 = self.mdh.getEntry('Positioning.Stage_X')
                self.xm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), x0, 'ScannerXPos', 0)
                charts.append(('XPos [um]', self.xm, 'ScannerXPos'))

            if 'ScannerYPos' in self.elv.evKeyNames:
                y0 = 0
                if 'Positioning.Stage_Y' in self.mdh.getEntryNames():
                    y0 = self.mdh.getEntry('Positioning.Stage_Y')
                self.ym = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), y0, 'ScannerYPos', 0)
                charts.append(('YPos [um]', self.ym, 'ScannerYPos'))

            if 'ScannerZPos' in self.elv.evKeyNames:
                z0 = 0
                if 'Positioning.PIFoc' in self.mdh.getEntryNames():
                    z0 = self.mdh.getEntry('Positioning.PIFoc')
                self.zm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), z0, 'ScannerZPos', 0)
                charts.append(('ZPos [um]', self.zm, 'ScannerZPos'))

            self.elv.SetCharts(charts)


    def CreateFoldPanel(self):
        from modules import playback
        self.player = playback.player(self)

        # delete earlier panel
        self._leftWindow1.DestroyChildren()

        # recreate the foldpanelbar
        hsizer = wx.BoxSizer(wx.VERTICAL)

        s = self._leftWindow1.GetBestSize()

        self._pnl = afp.foldPanel(self._leftWindow1, -1, wx.DefaultPosition,s)

        self.player.GenPlayPanel(self._pnl)
        #self.GenProfilePanel()
        if self.mode == 'LM':
            self.LMAnalyser.GenPointFindingPanel(self._pnl)
            self.LMAnalyser.GenAnalysisPanel(self._pnl)
            self.LMAnalyser.GenFitStatusPanel(self._pnl)
        else:
            if self.mode == 'blob':
                from modules import blobFinding
                self.blobFinder = blobFinding.blobFinder(self)
                self.blobFinder.GenBlobFindingPanel()
                self.blobFinder.GenBlobFitPanel()

            from modules import psfExtraction
            self.psfExtractor = psfExtraction.psfExtractor(self)
            self.psfExtractor.GenPSFPanel()


        hsizer.Add(self._pnl, 1, wx.EXPAND, 0)
        self._leftWindow1.SetSizerAndFit(hsizer)
        self.Refresh()
        self.notebook1.Refresh()
  

    


    def update(self):
        self.vp.update()
        self.statusbar.SetStatusText('Slice No: (%d/%d)    x: %d    y: %d    Frames Analysed: %d    Events detected: %d' % (self.vp.do.zp, self.vp.do.ds.shape[2], self.vp.do.xp, self.vp.do.yp, self.numAnalysed, self.numEvents))
        self.player.update()

        if 'LMAnalyser' in dir(self):
            self.LMAnalyser.update()

        if 'deconvolver' in dir(self):
            self.deconvolver.update()

#    def saveStack(self, event=None):
#        fdialog = wx.FileDialog(None, 'Save Data Stack as ...',
#            wildcard='*.kdf', style=wx.SAVE|wx.HIDE_READONLY)
#        succ = fdialog.ShowModal()
#        if (succ == wx.ID_OK):
#            self.ds.SaveToFile(fdialog.GetPath().encode())
#            if not (self.log == None):
#                lw = logparser.logwriter()
#                s = lw.write(self.log)
#                log_f = file('%s.log' % fdialog.GetPath().split('.')[0], 'w')
#                log_f.write(s)
#                log_f.close()
#
#            self.SetTitle(fdialog.GetFilename())
#            self.saved = True

#    def extractFrames(self, event=None):
#        dlg = wx.TextEntryDialog(self, 'Enter the range of frames to extract ...',
#                'Extract Frames', '0:%d' % self.ds.getNumSlices())
#
#        if dlg.ShowModal() == wx.ID_OK:
#            ret = dlg.GetValue().split(':')
#
#            start = int(ret[0])
#            finish = int(ret[1])
#
#            if len(ret) == 3:
#                subsamp = int(ret[2])
#            else:
#                subsamp = 1
#
#            fdialog = wx.FileDialog(None, 'Save Extracted Frames as ...',
#                wildcard='*.h5', style=wx.SAVE|wx.HIDE_READONLY)
#            succ = fdialog.ShowModal()
#            if (succ == wx.ID_OK):
#                h5ExFrames.extractFrames(self.ds, self.mdh, self.seriesName, fdialog.GetPath(), start, finish, subsamp)
#
#            fdialog.Destroy()
#        dlg.Destroy()

    def OnExport(self, event=None):
        import dataExporter

        if 'getEvents' in dir(self.ds):
            evts = self.ds.getEvents()
        else:
            evts = []

        dataExporter.CropExportData(self.vp.view, self.mdh, evts, self.seriesName)

#    def menuClose(self, event):
#        self.Close()

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
			
#    def clearSel(self, event):
#        self.vp.ResetSelection()
#        self.vp.Refresh()
#
#    def crop(self, event):
#        cd = dCrop.dCrop(self, self.vp)
#        if cd.ShowModal():
#            ds2 = example.CDataStack(self.ds, cd.x1, cd.y1, cd.z1, cd.x2, cd.y2, cd.z2, cd.chs)
#            dvf = DSViewFrame(self.GetParent(), '--cropped--', ds2)
#            dvf.Show()

    def dsRefresh(self):
        #zp = self.vp.do.zp #save z -position
        self.vp.do.SetDataStack(self.ds)
        #self.vp.do.zp = zp #restore z position
        self.elv.SetEventSource(self.ds.getEvents())
        self.elv.SetRange([0, self.ds.getNumSlices()])
        
        if 'ProtocolFocus' in self.elv.evKeyNames:
            self.zm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh.getEntry('Camera.CycleTime'), self.mdh.getEntry('StartTime'), self.mdh.getEntry('Protocol.PiezoStartPos'))
            self.elv.SetCharts([('Focus [um]', self.zm, 'ProtocolFocus'),])

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

        return 1

# end of class MyApp

def main():
    app = MyApp(0)
    app.MainLoop()


if __name__ == "__main__":
    main()
