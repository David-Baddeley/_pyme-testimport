#!/usr/bin/python
# generated by wxGlade 0.3.3 on Mon Jun 14 06:48:07 2004

import wx
import wx.aui

from PYME.misc.auiFloatBook import AuiNotebookWithFloatingPages
import wx.lib.foldpanelbar as fpb
from PYME.misc.fbpIcons import *
from PYME.FileUtils import h5ExFrames

import os
import sys

#import viewpanel
import PYME.cSMI as example
#import dCrop
#import logparser
import numpy

import tables
import wx.py.crust
import pylab
import glob

from myviewpanel_numarray import MyViewPanel
from PYME.Analysis.LMVis import recArrayView
import eventLogViewer

from PYME.Acquire import MetaDataHandler
from PYME.Analysis import MetaData
from PYME.Analysis.DataSources import HDFDataSource
from PYME.Analysis.DataSources import TQDataSource
#from PYME.Analysis.DataSources import TiffDataSource
from PYME.FileUtils import readTiff
from PYME.Analysis.LMVis import progGraph as progGraph
from PYME.Analysis.LMVis import inpFilt
from PYME.Acquire.mytimer import mytimer

from PYME.Analysis import piecewiseMapping

class DSViewFrame(wx.Frame):
    def __init__(self, parent=None, title='', dstack = None, log = None, filename = None, queueURI = None):
        wx.Frame.__init__(self,parent, -1, title,size=wx.Size(800,800), pos=(1100, 300))

        self.ds = dstack
        self.log = log

        self.saved = True

        self.mode = 'LM'
        self.vObjPos = None
        self.vObjFit = None

        #a timer object to update for us
        self.timer = mytimer()
        self.timer.Start(5000)

        #timer for playback
        self.tPlay = mytimer()
        self.tPlay.WantNotification.append(self.OnFrame)

        self.numAnalysed = 0
        self.numEvents = 0
        self.fitResults = []

        if (dstack == None):
            if (filename == None):
                fdialog = wx.FileDialog(None, 'Please select Data Stack to open ...',
                    wildcard='PYME Data|*.h5|TIFF files|*.tif|KDF files|*.kdf', style=wx.OPEN)
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
                elif filename.endswith('.h5'):
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

                    #try and find a previously performed analysis
                    fns = filename.split(os.path.sep)
                    #print fns
                    #print fns[:-2]
                    #print fns[-2:]
                    cand = os.path.sep.join(fns[:-2] + ['analysis',] + fns[-2:]) + 'r'
                    print cand
                    if os.path.exists(cand):
                        #print 'Found Analysis'
                        h5Results = tables.openFile(cand)

                        if 'FitResults' in dir(h5Results.root):
                            self.fitResults = h5Results.root.FitResults[:]
                            self.resultsSource = inpFilt.h5rSource(h5Results)

                       


                elif filename.endswith('.kdf'): #kdf
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
                    
                else: #try tiff
                    #self.dataSource = TiffDataSource.DataSource(filename, None)
                    self.dataSource = readTiff.read3DTiff(filename)
                    self.mdh = MetaData.ConfocDefault

                    from PYME.ParallelTasks.relativeFiles import getRelFilename
                    self.seriesName = getRelFilename(filename)

                    self.mode = 'blob'

                self.PSFLocs = []

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

        if self.mode == 'LM':
            self.sh.runfile(os.path.join(os.path.dirname(__file__),'fth5.py'))

        self.notebook1.AddPage(page=self.vp, select=True, caption='Data')
        self.notebook1.AddPage(page=self.sh, select=False, caption='Console')

        if self.mode == 'LM':
            self.elv = eventLogViewer.eventLogPanel(self.notebook1, self.ds.getEvents(), self.mdh, [0, self.ds.getNumSlices()]);
            self.notebook1.AddPage(self.elv, 'Events')

            if 'ProtocolFocus' in self.elv.evKeyNames:
                self.zm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.md.Camera.CycleTime, self.md.StartTime, self.md.Protocol.PiezoStartPos)
                self.elv.SetCharts([('Focus [um]', self.zm, 'ProtocolFocus'),])

                

        if len(self.fitResults) > 0:
            #print self.fitResults.shape
            #print self.fitResults[0].dtype
            self.vp.pointMode = 'lm'
            
            voxx = 1e3*self.mdh.getEntry('voxelsize.x')
            voxy = 1e3*self.mdh.getEntry('voxelsize.y')
            self.vp.points = numpy.vstack((self.fitResults['fitResults']['x0']/voxx, self.fitResults['fitResults']['y0']/voxy, self.fitResults['tIndex'])).T

            from PYME.Analysis.LMVis import gl_render
            self.glCanvas = gl_render.LMGLCanvas(self.notebook1, False, vp = self.vp, vpVoxSize = voxx)
            self.glCanvas.cmap = pylab.cm.gist_rainbow

            self.notebook1.AddPage(page=self.glCanvas, select=False, caption='VisLite')

            xsc = self.ds.shape[0]*1.0e3*self.mdh.getEntry('voxelsize.x')/self.glCanvas.Size[0]
            ysc = self.ds.shape[1]*1.0e3*self.mdh.getEntry('voxelsize.y')/ self.glCanvas.Size[1]

            if xsc > ysc:
                self.glCanvas.setView(0, xsc*self.glCanvas.Size[0], 0, xsc*self.glCanvas.Size[1])
            else:
                self.glCanvas.setView(0, ysc*self.glCanvas.Size[0], 0, ysc*self.glCanvas.Size[1])

            #self.glCanvas.setPoints(self.fitResults['fitResults']['x0'],self.fitResults['fitResults']['y0'],self.fitResults['tIndex'].astype('f'))
            #self.glCanvas.setCLim((0, self.numAnalysed))
            self.timer.WantNotification.append(self.AddPointsToVis)


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
        F_SAVE_POSITIONS = wx.NewId()
        F_SAVE_FITS = wx.NewId()
        tmp_menu.Append(wx.ID_SAVEAS, "Extract Frames", "", wx.ITEM_NORMAL)
        if self.mode == 'blob':
            tmp_menu.Append(F_SAVE_POSITIONS, "Save &Positions", "", wx.ITEM_NORMAL)
            tmp_menu.Append(F_SAVE_FITS, "Save &Fit Results", "", wx.ITEM_NORMAL)
        tmp_menu.Append(wx.ID_CLOSE, "Close", "", wx.ITEM_NORMAL)
        self.menubar.Append(tmp_menu, "File")

        #mEdit = wx.Menu()
        #EDIT_CLEAR_SEL = wx.NewId()
        #EDIT_CROP = wx.NewId()
        #mEdit.Append(EDIT_CLEAR_SEL, "Reset Selection", "", wx.ITEM_NORMAL)
        #mEdit.Append(EDIT_CROP, "Crop", "", wx.ITEM_NORMAL)
        #self.menubar.Append(mEdit, "Edit")

        # Menu Bar end
        wx.EVT_MENU(self, wx.ID_SAVEAS, self.extractFrames)
        wx.EVT_MENU(self, F_SAVE_POSITIONS, self.savePositions)
        wx.EVT_MENU(self, F_SAVE_FITS, self.saveFits)
        #wx.EVT_MENU(self, wx.ID_CLOSE, self.menuClose)
        #wx.EVT_MENU(self, EDIT_CLEAR_SEL, self.clearSel)
        #wx.EVT_MENU(self, EDIT_CROP, self.crop)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
		
        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)

        self.CreateFoldPanel()

        self.Layout()
        self.update()

    def AddPointsToVis(self):
        self.glCanvas.setPoints(self.fitResults['fitResults']['x0'],self.fitResults['fitResults']['y0'],self.fitResults['tIndex'].astype('f'))
        self.glCanvas.setCLim((0, self.fitResults['tIndex'].max()))

        self.timer.WantNotification.remove(self.AddPointsToVis)


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

        self.GenPlayPanel()
        self.GenProfilePanel()
        if self.mode == 'LM':
            self.GenPointFindingPanel()
            self.GenAnalysisPanel()
            self.GenFitStatusPanel()
        elif self.mode == 'blob':
            self.GenBlobFindingPanel()
            self.GenBlobFitPanel()
            self.GenPSFPanel()
        else:
            self.GenPSFPanel()


        #item = self._pnl.AddFoldPanel("Filters", False, foldIcons=self.Images)
        #item = self._pnl.AddFoldPanel("Visualisation", False, foldIcons=self.Images)
        wx.LayoutAlgorithm().LayoutWindow(self, self.notebook1)
        self.Refresh()
        self.notebook1.Refresh()

    def GenPlayPanel(self):
        item = self._pnl.AddFoldPanel("Playback", collapsed=False,
                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Pos:'), 0,wx.ALIGN_CENTER_VERTICAL|wx.LEFT,0)

        self.slPlayPos = wx.Slider(pan, -1, 0, 0, 100, style=wx.SL_HORIZONTAL)
        self.slPlayPos.Bind(wx.EVT_SCROLL_CHANGED, self.OnPlayPosChanged)
        hsizer.Add(self.slPlayPos, 1,wx.ALIGN_CENTER_VERTICAL)

        vsizer.Add(hsizer, 0,wx.ALL|wx.EXPAND, 0)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        import os

        dirname = os.path.dirname(__file__)

        self.bSeekStart = wx.BitmapButton(pan, -1, wx.Bitmap(os.path.join(dirname, 'icons/media-skip-backward.png')))
        hsizer.Add(self.bSeekStart, 0,wx.ALIGN_CENTER_VERTICAL,0)
        self.bSeekStart.Bind(wx.EVT_BUTTON, self.OnSeekStart)

        self.bmPlay = wx.Bitmap(os.path.join(dirname,'icons/media-playback-start.png'))
        self.bmPause = wx.Bitmap(os.path.join(dirname,'icons/media-playback-pause.png'))
        self.bPlay = wx.BitmapButton(pan, -1, self.bmPlay)
        self.bPlay.Bind(wx.EVT_BUTTON, self.OnPlay)
        hsizer.Add(self.bPlay, 0,wx.ALIGN_CENTER_VERTICAL,0)

#        self.bSeekEnd = wx.BitmapButton(pan, -1, wx.Bitmap('icons/media-skip-forward.png'))
#        hsizer.Add(self.bSeekEnd, 0,wx.ALIGN_CENTER_VERTICAL,0)

        hsizer.Add(wx.StaticText(pan, -1, 'FPS:'), 0,wx.ALIGN_CENTER_VERTICAL|wx.LEFT,4)

        self.slPlaySpeed = wx.Slider(pan, -1, 5, 1, 50, style=wx.SL_HORIZONTAL)
        self.slPlaySpeed.Bind(wx.EVT_SCROLL_CHANGED, self.OnPlaySpeedChanged)
        hsizer.Add(self.slPlaySpeed, 1,wx.ALIGN_CENTER_VERTICAL)

        vsizer.Add(hsizer, 0,wx.TOP|wx.BOTTOM|wx.EXPAND, 4)
        pan.SetSizer(vsizer)
        vsizer.Fit(pan)

        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

    def OnPlay(self, event):
        if not self.tPlay.IsRunning():
            self.tPlay.Start(1000./self.slPlaySpeed.GetValue())
            self.bPlay.SetBitmapLabel(self.bmPause)
        else:
            self.tPlay.Stop()
            self.bPlay.SetBitmapLabel(self.bmPlay)

    def OnFrame(self):
        self.vp.zp +=1
        if self.vp.zp >= self.ds.shape[2]:
            self.vp.zp = 0

        self.update()

    def OnSeekStart(self, event):
        self.vp.zp = 0
        self.update()

    def OnPlaySpeedChanged(self, event):
        if self.tPlay.IsRunning():
            self.tPlay.Stop()
            self.tPlay.Start(1000./self.slPlaySpeed.GetValue())

    def OnPlayPosChanged(self, event):
        self.vp.zp = int((self.ds.shape[2]-1)*self.slPlayPos.GetValue()/100.)
        self.update()


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
        
        self.bGo = wx.Button(item, -1, 'Go')
            

        self.bGo.Bind(wx.EVT_BUTTON, self.OnGo)
        self._pnl.AddFoldPanelWindow(item, self.bGo, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

    def OnGo(self, event):
        threshold = float(self.tThreshold.GetValue())
        startAt = int(self.tStartAt.GetValue())
        driftEst = self.cbDrift.GetValue()
        fitMod = self.cFitType.GetStringSelection()

        if fitMod.startswith('PsfFit') and not 'PSFFile' in self.mdh.getEntryNames():
            fdialog = wx.FileDialog(None, 'Please select PSF to use ...',
                    wildcard='PSF files|*.psf', style=wx.OPEN)
            succ = fdialog.ShowModal()
            if (succ == wx.ID_OK):
                #self.ds = example.CDataStack(fdialog.GetPath().encode())
                #self.ds =
                psfFilename = fdialog.GetPath()
                self.mdh.setEntry('PSFFile', psfFilename)
                self.md.setEntry('PSFFile', psfFilename)
            else:
                return

        if not driftEst:
            self.sh.run('pushImages(%d, %f, "%s")' % (startAt, threshold, fitMod))
        else:
            self.sh.run('pushImagesD(%d, %f)' % (startAt, threshold))

        from PYME.Analysis.LMVis import gl_render
        self.glCanvas = gl_render.LMGLCanvas(self.notebook1, False)
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

    def GenBlobFindingPanel(self):
        item = self._pnl.AddFoldPanel("Object Finding", collapsed=False,
                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(pan, -1, 'Threshold:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tThreshold = wx.TextCtrl(pan, -1, value='50', size=(40, -1))

        hsizer.Add(self.tThreshold, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        pan.SetSizer(hsizer)
        hsizer.Fit(pan)

        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        self.cbSNThreshold = wx.CheckBox(item, -1, 'SNR Threshold')
        self.cbSNThreshold.SetValue(False)

        self._pnl.AddFoldPanelWindow(item, self.cbSNThreshold, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        bFindObjects = wx.Button(item, -1, 'Find')


        bFindObjects.Bind(wx.EVT_BUTTON, self.OnFindObjects)
        self._pnl.AddFoldPanelWindow(item, bFindObjects, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

    def GenPSFPanel(self):
        item = self._pnl.AddFoldPanel("PSF Extraction", collapsed=False,
                                      foldIcons=self.Images)

        pan = wx.Panel(item, -1)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
#
#        hsizer.Add(wx.StaticText(pan, -1, 'Threshold:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
#        self.tThreshold = wx.TextCtrl(pan, -1, value='50', size=(40, -1))
#
        bTagPSF = wx.Button(pan, -1, 'Tag', style=wx.BU_EXACTFIT)
        bTagPSF.Bind(wx.EVT_BUTTON, self.OnTagPSF)
        hsizer.Add(bTagPSF, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        bClearTagged = wx.Button(pan, -1, 'Clear', style=wx.BU_EXACTFIT)
        bClearTagged.Bind(wx.EVT_BUTTON, self.OnClearTags)
        hsizer.Add(bClearTagged, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        vsizer.Add(hsizer, 0,wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'ROI Size:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tPSFROI = wx.TextCtrl(pan, -1, value='30,30,30', size=(40, -1))
        hsizer.Add(self.tPSFROI, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tPSFROI.Bind(wx.EVT_TEXT, self.OnPSFROI)

        vsizer.Add(hsizer, 0,wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(pan, -1, 'Blur:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        self.tPSFBlur = wx.TextCtrl(pan, -1, value='.5,.5,1', size=(40, -1))
        hsizer.Add(self.tPSFBlur, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        vsizer.Add(hsizer, 0,wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0)

        bExtract = wx.Button(pan, -1, 'Extract', style=wx.BU_EXACTFIT)
        bExtract.Bind(wx.EVT_BUTTON, self.OnExtractPSF)
        vsizer.Add(bExtract, 0,wx.ALL|wx.ALIGN_RIGHT, 5)

        pan.SetSizer(vsizer)
        vsizer.Fit(pan)

        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)
#
#        self.cbSNThreshold = wx.CheckBox(item, -1, 'SNR Threshold')
#        self.cbSNThreshold.SetValue(False)
#
#        self._pnl.AddFoldPanelWindow(item, self.cbSNThreshold, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        
    def OnTagPSF(self, event):
        from PYME.PSFEst import extractImages
        rsx, rsy, rsz = [int(s) for s in self.tPSFROI.GetValue().split(',')]
        dx, dy, dz = extractImages.getIntCenter(self.dataSource[(self.vp.xp-rsx):(self.vp.xp+rsx + 1),(self.vp.yp-rsy):(self.vp.yp+rsy+1), :])
        self.PSFLocs.append((self.vp.xp + dx, self.vp.yp + dy, dz))
        self.vp.psfROIs = self.PSFLocs
        self.vp.Refresh()

    def OnClearTags(self, event):
        self.PSFLocs = []
        self.vp.psfROIs = self.PSFLocs
        self.vp.Refresh()

    def OnPSFROI(self, event):
        try:
            psfROISize = [int(s) for s in self.tPSFROI.GetValue().split(',')]
            self.vp.psfROISize = psfROISize
            self.vp.Refresh()
        except:
            pass

    def OnExtractPSF(self, event):
        if (len(self.PSFLocs) > 0):
            from PYME.PSFEst import extractImages

            psfROISize = [int(s) for s in self.tPSFROI.GetValue().split(',')]
            psfBlur = [float(s) for s in self.tPSFBlur.GetValue().split(',')]
            #print psfROISize
            psf = extractImages.getPSF3D(self.dataSource, self.PSFLocs, psfROISize, psfBlur)

            from pylab import *
            import cPickle
            imshow(psf.max(2))

            fdialog = wx.FileDialog(None, 'Save PSF as ...',
                wildcard='PSF file (*.psf)|*.psf', style=wx.SAVE|wx.HIDE_READONLY)
            succ = fdialog.ShowModal()
            if (succ == wx.ID_OK):
                fpath = fdialog.GetPath()
                #save as a pickle containing the data and voxelsize

                fid = open(fpath, 'wb')
                cPickle.dump((psf, self.mdh.voxelsize), fid, 2)
                fid.close()

    def OnFindObjects(self, event):
        threshold = float(self.tThreshold.GetValue())

        from PYME.Analysis.ofind3d import ObjectIdentifier

        if not 'ofd' in dir(self):
            #create an object identifier
            self.ofd = ObjectIdentifier(self.dataSource)

        #and identify objects ...
        if self.cbSNThreshold.GetValue(): #don't detect objects in poisson noise
            fudgeFactor = 1 #to account for the fact that the blurring etc... in ofind doesn't preserve intensities - at the moment completely arbitrary so a threshold setting of 1 results in reasonable detection.
            threshold =  (numpy.sqrt(self.mdh.Camera.ReadNoise**2 + numpy.maximum(self.mdh.Camera.ElectronsPerCount*(self.mdh.Camera.NoiseFactor**2)*(self.dataSource.astype('f') - self.mdh.Camera.ADOffset)*self.mdh.Camera.TrueEMGain, 1))/self.mdh.Camera.ElectronsPerCount)*fudgeFactor*threshold
            self.ofd.FindObjects(threshold, 0)
        else:
            self.ofd.FindObjects(threshold)
        
        self.vp.points = numpy.array([[p.x, p.y, p.z] for p in self.ofd])

        self.objPosRA = numpy.rec.fromrecords(self.vp.points, names='x,y,z')

        if self.vObjPos == None:
            self.vObjPos = recArrayView.recArrayPanel(self.notebook1, self.objPosRA)
            self.notebook1.AddPage(self.vObjPos, 'Object Positions')
        else:
            self.vObjPos.grid.SetData(self.objPosRA)

        self.update()

    def GenBlobFitPanel(self):
        item = self._pnl.AddFoldPanel("Object Fitting", collapsed=False,
                                      foldIcons=self.Images)

        #pan = wx.Panel(item, -1)

#        hsizer = wx.BoxSizer(wx.HORIZONTAL)
#
#        hsizer.Add(wx.StaticText(pan, -1, 'Threshold:'), 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
#        self.tThreshold = wx.TextCtrl(pan, -1, value='50', size=(40, -1))
#
#        hsizer.Add(self.tThreshold, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
#
#        pan.SetSizer(hsizer)
#        hsizer.Fit(pan)
#
#        self._pnl.AddFoldPanelWindow(item, pan, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 5)

        bFitObjects = wx.Button(item, -1, 'Fit')


        bFitObjects.Bind(wx.EVT_BUTTON, self.OnFitObjects)
        self._pnl.AddFoldPanelWindow(item, bFitObjects, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

    def OnFitObjects(self, event):
        import PYME.Analysis.FitFactories.Gauss3DFitR as fitMod

        fitFac = fitMod.FitFactory(self.dataSource, self.mdh)

        self.objFitRes = numpy.empty(len(self.ofd), fitMod.FitResultsDType)
        for i in range(len(self.ofd)):
            p = self.ofd[i]
            try:
                self.objFitRes[i] = fitFac.FromPoint(round(p.x), round(p.y), round(p.z))
            except:
                pass


        if self.vObjFit == None:
            self.vObjFit = recArrayView.recArrayPanel(self.notebook1, self.objFitRes['fitResults'])
            self.notebook1.AddPage(self.vObjFit, 'Fitted Positions')
        else:
            self.vObjFit.grid.SetData(self.objFitRes)

        self.update()

    def OnTest(self, event):
        threshold = float(self.tThreshold.GetValue())
        startAt = int(self.tStartAt.GetValue())
        driftEst = self.cbDrift.GetValue()

        #if not driftEst:
        self.sh.run('testFrames(%f)' % (threshold))
        #else:
        #    self.sh.run('pushImagesD(%d, %f)' % (startAt, threshold)

    def GenProfilePanel(self):
        item = self._pnl.AddFoldPanel("Intensity Profile", collapsed=False,
                                      foldIcons=self.Images)

        bPlotProfile = wx.Button(item, -1, 'Plot')

        bPlotProfile.Bind(wx.EVT_BUTTON, self.OnPlotProfile)
        self._pnl.AddFoldPanelWindow(item, bPlotProfile, fpb.FPB_ALIGN_WIDTH, fpb.FPB_DEFAULT_SPACING, 10)

        
    def OnPlotProfile(self, event):
        x,p,d, pi = self.vp.GetProfile(50, background=[7,7])

        pylab.figure(1)
        pylab.clf()
        pylab.step(x,p)
        pylab.step(x, 10*d - 30)
        pylab.ylim(-35,pylab.ylim()[1])

        pylab.xlim(x.min(), x.max())

        pylab.xlabel('Time [%3.2f ms frames]' % (1e3*self.mdh.getEntry('Camera.CycleTime')))
        pylab.ylabel('Intensity [counts]')

        fr = self.fitResults[pi]

        if not len(fr) == 0:
            pylab.figure(2)
            pylab.clf()
            
            pylab.subplot(211)
            pylab.errorbar(fr['tIndex'], fr['fitResults']['x0'] - self.vp.xp*1e3*self.mdh.getEntry('voxelsize.x'), fr['fitError']['x0'], fmt='xb')
            pylab.xlim(x.min(), x.max())
            pylab.xlabel('Time [%3.2f ms frames]' % (1e3*self.mdh.getEntry('Camera.CycleTime')))
            pylab.ylabel('x offset [nm]')

            pylab.subplot(212)
            pylab.errorbar(fr['tIndex'], fr['fitResults']['y0'] - self.vp.yp*1e3*self.mdh.getEntry('voxelsize.y'), fr['fitError']['y0'], fmt='xg')
            pylab.xlim(x.min(), x.max())
            pylab.xlabel('Time [%3.2f ms frames]' % (1e3*self.mdh.getEntry('Camera.CycleTime')))
            pylab.ylabel('y offset [nm]')

            pylab.figure(3)
            pylab.clf()

            pylab.errorbar(fr['fitResults']['x0'] - self.vp.xp*1e3*self.mdh.getEntry('voxelsize.x'),fr['fitResults']['y0'] - self.vp.yp*1e3*self.mdh.getEntry('voxelsize.y'), fr['fitError']['x0'], fr['fitError']['y0'], fmt='xb')
            #pylab.xlim(x.min(), x.max())
            pylab.xlabel('x offset [nm]')
            pylab.ylabel('y offset [nm]')



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
        self.statusbar.SetStatusText('Slice No: (%d/%d)    x: %d    y: %d    Frames Analysed: %d    Events detected: %d' % (self.vp.zp, self.vp.ds.shape[2], self.vp.xp, self.vp.yp, self.numAnalysed, self.numEvents))
        self.slPlayPos.SetValue((100*self.vp.zp)/(self.vp.ds.shape[2]-1))

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

    def extractFrames(self, event=None):
        dlg = wx.TextEntryDialog(self, 'Enter the range of frames to extract ...',
                'Extract Frames', '0:%d' % self.ds.getNumSlices())

        if dlg.ShowModal() == wx.ID_OK:
            st, fin = dlg.GetValue().split(':')

            start = int(st)
            finish = int(fin)
            
            fdialog = wx.FileDialog(None, 'Save Extracted Frames as ...',
                wildcard='*.h5', style=wx.SAVE|wx.HIDE_READONLY)
            succ = fdialog.ShowModal()
            if (succ == wx.ID_OK):
                h5ExFrames.extractFrames(self.ds, self.mdh, self.seriesName, fdialog.GetPath(), start, finish)

            fdialog.Destroy()
        dlg.Destroy()

    def savePositions(self, event=None):
        fdialog = wx.FileDialog(None, 'Save Positions ...',
            wildcard='Tab formatted text|*.txt', defaultFile=os.path.splitext(self.seriesName)[0] + '_pos.txt', style=wx.SAVE|wx.HIDE_READONLY)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            outFilename = fdialog.GetPath().encode()

            of = open(outFilename, 'w')
            of.write('\t'.join(self.objPosRA.dtype.names) + '\n')

            for obj in self.objPosRA:
                of.write('\t'.join([repr(v) for v in obj]) + '\n')
            of.close()

            npFN = os.path.splitext(outFilename)[0] + '.npy'

            numpy.save(npFN, self.objPosRA)
            
    def saveFits(self, event=None):
        fdialog = wx.FileDialog(None, 'Save Fit Results ...',
            wildcard='Tab formatted text|*.txt', defaultFile=os.path.splitext(self.seriesName)[0] + '_fits.txt', style=wx.SAVE|wx.HIDE_READONLY)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            outFilename = fdialog.GetPath().encode()

            of = open(outFilename, 'w')
            of.write('\t'.join(self.objFitRes['fitResults'].dtype.names) + '\n')

            for obj in self.objFitRes['fitResults']:
                of.write('\t'.join([repr(v) for v in obj]) + '\n')
            of.close()

            npFN = os.path.splitext(outFilename)[0] + '.npy'

            numpy.save(npFN, self.objFitRes)

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

                self.vp.points = numpy.vstack((self.fitResults['fitResults']['x0'], self.fitResults['fitResults']['y0'], self.fitResults['tIndex'])).T

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
        self.progPan.Refresh()
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
