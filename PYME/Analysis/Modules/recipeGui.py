# -*- coding: utf-8 -*-
"""
Created on Fri May 29 16:33:47 2015

@author: david
"""

import wx
import numpy as np

from PYME.Analysis.Modules import modules
from PYME.Analysis.Modules import runRecipe

import pylab
from PYME.DSView.image import ImageStack
from PYME.DSView import ViewIm3D

from PYME.misc import wxPlotPanel
from PYME.misc import depGraph

from traitsui.api import Controller

import os
import glob

RECIPE_DIR = os.path.join(os.path.split(modules.__file__)[0], 'Recipes')
CANNED_RECIPES = glob.glob(os.path.join(RECIPE_DIR, '*.yaml'))


class RecipePlotPanel(wxPlotPanel.PlotPanel):
    def __init__(self, parent, recipes, **kwargs):
        self.recipes = recipes
        self.parent = parent

        wxPlotPanel.PlotPanel.__init__( self, parent, **kwargs )
        
        self.figure.canvas.mpl_connect('pick_event', self.parent.OnPick)

    def draw(self):
        if not hasattr( self, 'ax' ):
            self.ax = self.figure.add_axes([0, 0, 1, 1])

        self.ax.cla()

        dg = self.recipes.activeRecipe.dependancyGraph()        
        ips = depGraph.arrangeNodes(dg)
    
    
        cols = {}    
        for k, v in dg.items():
            if not (isinstance(k, str) or isinstance(k, unicode)):
                yv0 = []
                yoff = .1*np.arange(len(v))
                yoff -= yoff.mean()
                
                for e in v:
                    x0, y0 = ips[e]
                    x1, y1 = ips[k]
                    yv0.append(y0 + 0.01*x0*(2.0*(y0>y1) - 1))
                    
                yvi = np.argsort(np.array(yv0))
                #print yv0, yvi
                yos = np.zeros(3)
                yos[yvi] = yoff
                    
                for e, yo in zip(v, yos):
                    x0, y0 = ips[e]
                    x1, y1 = ips[k]
                    
                    if not e in cols.keys():
                        cols[e] = 0.7*np.array(pylab.cm.hsv(pylab.rand()))
                    
                    self.ax.plot([x0,x0+.5, x0+.5, x1], [y0,y0,y1+yo,y1+yo], c=cols[e], lw=2)
                
        for k, v in ips.items():   
            if not (isinstance(k, str) or isinstance(k, unicode)):
                s = k.__class__.__name__
                #pylab.plot(v[0], v[1], 'o', ms=5)
                rect = pylab.Rectangle([v[0], v[1]-.25], 1, .5, ec='k', fc=[.8,.8, 1], picker=True)
                
                rect._data = k
                self.ax.add_patch(rect)
                self.ax.text(v[0]+.05, v[1]+.18 , s, weight='bold')
                #print repr(k)
                
                params = k.get().items()
                s2 = '\n'.join(['%s : %s' %i for i in params[:5]])
                if len(params) > 5:
                    s2 += '\n ... <some hidden>'
                self.ax.text(v[0]+.05, v[1]-.22 , s2, size=8, stretch='ultra-condensed')
            else:
                s = k
                if not k in cols.keys():
                    cols[k] = 0.7*np.array(pylab.cm.hsv(pylab.rand()))
                self.ax.plot(v[0], v[1], 'o', color=cols[k])
                t = self.ax.text(v[0]+.1, v[1] + .02, s, color=cols[k], weight='bold', picker=True)
                t._data = k
                
                
                
        ipsv = np.array(ips.values())
        try:
            xmn, ymn = ipsv.min(0)
            xmx, ymx = ipsv.max(0)
        
            self.ax.set_ylim(ymn-1, ymx+1)
            self.ax.set_xlim(xmn-.5, xmx + .7)
        except ValueError:
            pass
        
        self.ax.axis('off')
        
        self.canvas.draw()




class RecipeView(wx.Panel):
    def __init__(self, parent, recipes):
        wx.Panel.__init__(self, parent, size=(400, 100))
        
        self.recipes = recipes
        recipes.recipeView = self
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        self.recipePlot = RecipePlotPanel(self, recipes, size=(-1, 400))
        vsizer.Add(self.recipePlot, 1, wx.ALL|wx.EXPAND, 5)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.bNewRecipe = wx.Button(self, -1, 'New Recipe')
        hsizer.Add(self.bNewRecipe, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.bNewRecipe.Bind(wx.EVT_BUTTON, self.OnNewRecipe)

        self.bLoadRecipe = wx.Button(self, -1, 'Load Recipe')
        hsizer.Add(self.bLoadRecipe, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.bLoadRecipe.Bind(wx.EVT_BUTTON, self.recipes.OnLoadRecipe)
        
        self.bAddModule = wx.Button(self, -1, 'Add Module')
        hsizer.Add(self.bAddModule, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.bAddModule.Bind(wx.EVT_BUTTON, self.OnAddModule)
        
        #self.bRefresh = wx.Button(self, -1, 'Refresh')
        #hsizer.Add(self.bRefresh, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.bSaveRecipe = wx.Button(self, -1, 'Save Recipe')
        hsizer.Add(self.bSaveRecipe, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.bSaveRecipe.Bind(wx.EVT_BUTTON, self.recipes.OnSaveRecipe)
        
        vsizer.Add(hsizer, 0, wx.EXPAND, 0)
        hsizer1.Add(vsizer, 1, wx.EXPAND|wx.ALL, 2)
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        self.tRecipeText = wx.TextCtrl(self, -1, '', size=(250, -1),
                                       style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
                                       
        vsizer.Add(self.tRecipeText, 1, wx.ALL, 2)
        
        self.bApply = wx.Button(self, -1, 'Apply')
        vsizer.Add(self.bApply, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.bApply.Bind(wx.EVT_BUTTON, self.OnApplyText)
                                       
        hsizer1.Add(vsizer, 0, wx.EXPAND|wx.ALL, 2)

                
        
        self.SetSizerAndFit(hsizer1)
        
    def update(self):
        self.recipePlot.draw()
        self.tRecipeText.SetValue(self.recipes.activeRecipe.toYAML())
        
    def OnApplyText(self, event):
        self.recipes.LoadRecipeText(self.tRecipeText.GetValue())
        
    def OnNewRecipe(self, event):
        self.recipes.LoadRecipeText('')
        
    def OnAddModule(self, event):
        #mods = 
        mods = modules.base.all_modules
        modNames = mods.keys()
        modNames.sort()        
        
        dlg = wx.SingleChoiceDialog(
                self, 'Select module to add', 'Add a module',
                modNames, 
                wx.CHOICEDLG_STYLE
                )

        if dlg.ShowModal() == wx.ID_OK:
            modName = dlg.GetStringSelection()
            
            c = mods[modName]()
            self.recipes.activeRecipe.modules.append(c)
        dlg.Destroy()
        
        self.configureModule(c)
        
    def OnPick(self, event):
        k = event.artist._data
        if not (isinstance(k, str) or isinstance(k, unicode)):
            self.configureModule(k)
        else:
            outp = self.recipes.activeRecipe.namespace[k]
            if isinstance(outp, ImageStack):
                if not 'dsviewer' in dir(self.recipes):
                    dv = ViewIm3D(outp, mode='lite')
                else:
                    if self.recipes.dsviewer.mode == 'visGUI':
                        mode = 'visGUI'
                    else:
                        mode = 'lite'
                                   
                    dv = ViewIm3D(outp, mode=mode, glCanvas=self.recipes.dsviewer.glCanvas)
    
    
    def configureModule(self, k):
        p = self
        class MControl(Controller):
            def closed(self, info, is_ok):
                wx.CallLater(10, p.update)
        
        k.edit_traits(handler=MControl())
        
        
class RecipeManager(object):
    def __init__(self):
        self.activeRecipe = None
        self.LoadRecipeText('')
        
    def OnLoadRecipe(self, event):
        filename = wx.FileSelector("Choose a recipe to open",  
                                   default_extension='yaml', 
                                   wildcard='PYME Recipes (*.yaml)|*.yaml')

        #print filename
        if not filename == '':
            self.LoadRecipe(filename)
            
    def OnSaveRecipe(self, event):
        filename = wx.FileSelector("Save Recipe as ... ",  
                                   default_extension='yaml', 
                                   wildcard='PYME Recipes (*.yaml)|*.yaml', flags=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        #print filename
        if not filename == '':
            s = self.activeRecipe.toYAML()
            with open(filename, 'w') as f:
                f.write(s)
            

    def LoadRecipe(self, filename):
        #self.currentFilename  = filename
        with open(filename) as f:
            s = f.read()
        
        self.LoadRecipeText(s, filename) 
            
    def LoadRecipeText(self, s, filename=''):
        self.currentFilename  = filename
        self.activeRecipe = modules.ModuleCollection.fromYAML(s)
        #self.mICurrent.SetItemLabel('Run %s\tF5' % os.path.split(filename)[1])

        try:        
            self.recipeView.update()
        except AttributeError:
            pass


class dt(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window
        
    def OnDropFiles(self, x, y, filenames):
        self.window.UpdateFileList(filenames)
    

class BatchFrame(wx.Frame, wx.FileDropTarget):
    def __init__(self, parent=None):                
        wx.Frame.__init__(self, parent, wx.ID_ANY, 'The PYME Bakery')
        
        self.dropFiles = dt(self)      
        self.rm = RecipeManager()
        self.inputFiles = []
        
        vsizer1=wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Recipe:"), wx.HORIZONTAL)
        self.recipeView = RecipeView(self, self.rm)
        
        hsizer.Add(self.recipeView, 1, wx.ALL|wx.EXPAND, 2)
        vsizer1.Add(hsizer, 1, wx.ALL|wx.EXPAND, 2)
        
        vsizer2 = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Input files:'), wx.VERTICAL)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        hsizer.Add(wx.StaticText(self, -1, 'Filename pattern:'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.tGlob = wx.TextCtrl(self, -1, '')
        hsizer.Add(self.tGlob, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.bLoadFromGlob = wx.Button(self, -1, 'Get Matches')
        self.bLoadFromGlob.Bind(wx.EVT_BUTTON, self.OnGetMatches)
        hsizer.Add(self.bLoadFromGlob, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        
        vsizer2.Add(hsizer, 0, wx.EXPAND, 0)
        
        self.lFiles = wx.ListCtrl(self, -1, style=wx.LC_REPORT|wx.LC_HRULES)
        self.lFiles.InsertColumn(0, 'Filename')
        self.lFiles.Append(['Either drag files here, or enter a pattern (e.g. /Path/to/data/*.tif ) above and click "Get Matches"',])
        self.lFiles.SetColumnWidth(0, -1)
        
        vsizer2.Add(self.lFiles, .5, wx.EXPAND, 0)        
        
        vsizer1.Add(vsizer2, 0, wx.EXPAND|wx.TOP, 10)
        
        hsizer2 = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Output Directory:'), wx.HORIZONTAL)
        
        self.dcOutput = wx.DirPickerCtrl(self, -1, style=wx.DIRP_DIR_MUST_EXIST|wx.DIRP_USE_TEXTCTRL)
        hsizer2.Add(self.dcOutput, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 2)
        
        vsizer1.Add(hsizer2, 0, wx.EXPAND|wx.TOP, 10)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.AddStretchSpacer()

        self.bBake = wx.Button(self, -1, 'Bake') 
        hsizer.Add(self.bBake, 0, wx.ALL, 5)
        
        vsizer1.Add(hsizer, 0, wx.EXPAND|wx.TOP, 10)
                
        self.SetSizerAndFit(vsizer1)
        
        #self.SetDropTarget(self.drop)
        self.lFiles.SetDropTarget(self.dropFiles)
        
    def UpdateFileList(self, filenames):
        self.inputFiles = filenames        
        
        self.lFiles.DeleteAllItems()
        
        for f in filenames:
            self.lFiles.Append([f,])
        
    def OnGetMatches(self, event=None):
        import glob
        
        files = glob.glob(self.tGlob.GetValue())
        self.UpdateFileList(files)
        
    def OnBake(self, event=None):
        out_dir = self.dcOutput.GetPath()
        
        #validate our choices:
        if (self.rm.activeRecipe == None) or (len(self.rm.activeRecipe.modules) == 0):
            wx.MessageBox('No Recipe: Please open (or build) a recipe', 'Error', wx.OK|wx.ICON_ERROR)
            return
            
        if not len(self.inputFiles) > 0:
            wx.MessageBox('No input files', 'Error', wx.OK|wx.ICON_ERROR)
            return
            
        if (out_dir == '') or not os.path.exists(out_dir):
            wx.MessageBox('Ouput directory does not exist', 'Error', wx.OK|wx.ICON_ERROR)
            return
            
        runRecipe.Bake(self.rm.activeRecipe, {'input':self.inputFiles}, out_dir)
        
            
   