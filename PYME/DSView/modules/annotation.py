from traits.api import HasTraits, Float, CStr
import numpy as np

import matplotlib.pyplot as plt

import wx
import wx.lib.agw.aui as aui

class _Snake_Settings(HasTraits):
    length_weight = Float(0) #alpha
    smoothness = Float(0.1) #beta
    line_weight = Float(-1) #w_line - -ve values seek dark pixels
    edge_weight = Float(0)
    boundaries = CStr('fixed')
    prefilter_sigma = Float(2)


import wx.lib.mixins.listctrl as listmix

class myListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):#, listmix.TextEditMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        #listmix.TextEditMixin.__init__(self)
        #self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnLabelActivate)
    
    def OnBeginLabelEdit(self, event):
        if event.m_col == 0:
            event.Veto()
        else:
            event.Skip()
    
    def OnLabelActivate(self, event):
        newLabel = wx.GetTextFromUser("Enter new category name", "Rename")
        if not newLabel == '':
            self.SetStringItem(event.m_itemIndex, 1, newLabel)


class LabelPanel(wx.Panel):
    def __init__(self, parent, labeler, **kwargs):
        kwargs['style'] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, parent, **kwargs)
        
        #self.parent = parent
        self.labeler = labeler
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        sbsizer = wx.StaticBoxSizer(wx.StaticBox(self, label='Lock curves to ...'), wx.HORIZONTAL)
        self.cSelectBehaviour = wx.Choice(self, choices=['None', 'ridges', 'valleys', 'edges', 'custom'])
        self.cSelectBehaviour.Bind(wx.EVT_CHOICE, self.on_change_lock_mode)
        
        sbsizer.Add(self.cSelectBehaviour, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.bAdjustSnake = wx.Button(self, label='Adj', style=wx.BU_EXACTFIT)
        self.bAdjustSnake.Bind(wx.EVT_BUTTON, self.on_adjust_snake)
        self.bAdjustSnake.SetToolTipString('Adjust the parameters of fo the "snake" (active contour) used for curve locking')
        
        sbsizer.Add(self.bAdjustSnake, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 2)
        
        vsizer.Add(sbsizer, 0, wx.ALL|wx.EXPAND, 5)
        
        self.lLabels = myListCtrl(self, -1, style=wx.LC_REPORT)
        self.lLabels.InsertColumn(0, 'Label')
        self.lLabels.InsertColumn(1, 'Structure')
        
        for i in range(10):
            self.lLabels.InsertStringItem(i, '%d' % i)
            self.lLabels.SetStringItem(i, 1, 'Structure %d' % i)
        
        self.lLabels.SetStringItem(0, 1, 'No label')
        
        self.lLabels.SetItemState(1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        self.lLabels.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.lLabels.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        
        self.lLabels.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnChangeStructure)
        
        vsizer.Add(self.lLabels, 1, wx.ALL | wx.EXPAND, 5)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(self, -1, 'Line width:'), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.tLineWidth = wx.TextCtrl(self, -1, '1')
        self.tLineWidth.Bind(wx.EVT_TEXT, self.OnChangeLineWidth)
        hsizer.Add(self.tLineWidth, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.bAddLine = wx.Button(self, label='Add', style=wx.BU_EXACTFIT)
        hsizer.Add(self.bAddLine, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        self.bAddLine.Bind(wx.EVT_BUTTON, self.labeler.add_curved_line)
        self.bAddLine.SetToolTipString('Add a curve annotation (ctrl-L / cmd-L)')
        vsizer.Add(hsizer, 0, wx.ALL | wx.EXPAND, 5)
        
        self.SetSizer(vsizer)
    
    def OnChangeStructure(self, event):
        self.labeler.cur_label_index = event.m_itemIndex
    
    def OnChangeLineWidth(self, event):
        self.labeler.line_width = float(self.tLineWidth.GetValue())
        
    def on_change_lock_mode(self, event=None):
        self.labeler.set_lock_mode(self.cSelectBehaviour.GetStringSelection())
        
    def on_adjust_snake(self, event):
        self.cSelectBehaviour.SetStringSelection('custom')
        self.on_change_lock_mode()
        self.labeler._snake_settings.edit_traits(kind='modal')
        
    def get_labels(self):
        return {n : self.lLabels.GetItemText(n, 1) for n in range(10)}

class Annotater(object):
    def __init__(self, dsviewer):
        self.do = dsviewer.do
        self.dsviewer = dsviewer

        self.cur_label_index = 1
        self.line_width = 1
        self.lock_mode = 'None'
    
        self._annotations = []
        self.show_annotations = True
        self._snake_settings = _Snake_Settings()
        
        self.selected_annotations = []

        self.penColsA = [wx.Colour(*plt.cm.hsv(v, alpha=0.5, bytes=True)) for v in np.linspace(0, 1, 16)]
        #self.trackPens = [wx.Pen(c, 4) for c in self.penColsA]

        dsviewer.AddMenuItem('Annotation', "Refine selection\tCtrl-R", self.snake_refine_trace)
        dsviewer.AddMenuItem('Annotation', "Draw line\tCtrl-L", self.add_curved_line)
        
        self.do.on_selection_end.connect(self.snake_refine_trace)
        self.do.overlays.append(self.DrawOverlays)

        self.labelPanel = LabelPanel(dsviewer, self)
        self.labelPanel.SetSize(self.labelPanel.GetBestSize())

        pinfo2 = aui.AuiPaneInfo().Name("labelPanel").Right().Caption('Annotation').CloseButton(False).MinimizeButton(
            True).MinimizeMode(aui.AUI_MINIMIZE_CAPT_SMART | aui.AUI_MINIMIZE_POS_RIGHT)#.CaptionVisible(False)
        dsviewer._mgr.AddPane(self.labelPanel, pinfo2)
        
        
    
    def add_curved_line(self, event=None):
        if self.do.selectionMode == self.do.SELECTION_SQUIGLE:
            self._annotations.append({'type' : 'curve', 'points' : self.do.selection_trace,
                                      'labelID' : self.cur_label_index, 'z' : self.do.zp,
                                      'width' : self.line_width})
            self.do.selection_trace = []
            
        elif self.do.selectionMode == self.do.SELECTION_LNE:
            x0, y0, x1, y1 = self.do.GetSliceSelection()
            self._annotations.append({'type' : 'line', 'points' : [(x0, y0), (x1, y1)],
                                      'labelID' : self.cur_label_index, 'z':self.do.zp,
                                      'width' : self.line_width})
            
        self.dsviewer.Refresh()
        self.dsviewer.Update()
        
    def get_json_annotations(self):
        import ujson as json
        
        annotations = {'annotations' : self._annotations,
                       'structures' : self.labelPanel.get_labels()}
        
        return json.dumps(annotations)
            
    def set_lock_mode(self, mode):
        self.lock_mode = mode
        
        if mode in ['ridges', 'valleys']:
            self._snake_settings.edge_weight = 0
            
            if mode == 'ridges':
                self._snake_settings.line_weight = 1.0
            else:
                self._snake_settings.line_weight = -1.0
        elif mode == 'edges':
            self._snake_settings.edge_weight = 1.0
        
            
    def snake_refine_trace(self, event=None, sender=None, **kwargs):
        print('Refining selection')
        if self.lock_mode == 'None' or not self.do.selectionMode == self.do.SELECTION_SQUIGLE:
            return
        else:
            try:
                from skimage.segmentation import active_contour
                from scipy import ndimage
                
                im = ndimage.gaussian_filter(self.do.ds[:,:,self.do.zp].squeeze(), float(self._snake_settings.prefilter_sigma)).T
                
                pts = np.array(self.do.selection_trace)
                
                self.do.selection_trace = active_contour(im, pts,
                                                         alpha=self._snake_settings.length_weight,
                                                         beta=self._snake_settings.smoothness,
                                                         w_line=self._snake_settings.line_weight,
                                                         w_edge=self._snake_settings.edge_weight,
                                                         bc=self._snake_settings.boundaries)
                
                self.dsviewer.Refresh()
                self.dsviewer.Update()
            except ImportError:
                pass

    def DrawOverlays(self, view, dc):
        if self.show_annotations and (len(self._annotations) > 0):
            bounds = view._calcVisibleBounds()
            #vx, vy, vz = self.image.voxelsize
            visible_annotations = [c for c in self._annotations if self._visibletest(c, bounds)]
        
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
        
            for c in visible_annotations:
                pts = np.array(c['points'])
                x, y = pts.T
                z = int(c['z'])
                pFoc = np.vstack(view._PixelToScreenCoordinates3D(x, y, z)).T
            
                dc.SetPen(wx.Pen(self.penColsA[c['labelID'] % 16], max(2, c['width']*2.0**(self.do.scale))))
                dc.DrawLines(pFoc)
            
    

    def _visibletest(self, clump, bounds):
    
        xb, yb, zb = bounds
        
        x, y = np.array(clump['points']).T
        t = clump['z']
    
        return np.any((x >= xb[0]) * (y >= yb[0]) * (t >= (zb[0] - 1)) * (x < xb[1]) * (y < yb[1]) * (t < (zb[1] + 1)))

    def _hittest(self, clump, pos):
        xp, yp, zp = pos
    
        bounds = [(xp - 2, xp + 2), (yp - 2, yp + 2), (zp, zp + 1)]
    
        return self._visibletest(clump, bounds)
    
    def _calc_spline_gradients(self, pts):
        from scipy import sparse
        from scipy.sparse import linalg
        N = len(pts)
        OD = np.ones(N-1)
        Dg = 4*np.ones(N)
        Dg[0] = 2
        Dg[-1] = 2
        
        Yvs = np.array(pts)[:,1]
        
        b = np.zeros(N)
        b[1:-1] = Yvs[2:] - Yvs[:-2]
        b[0] = Yvs[1] - Yvs[0]
        b[-1] = Yvs[-1] - Yvs[-2]
        
        A = sparse.diags([OD, Dg, OD], [-1, 0, 1])
        
        D = linalg.spsolve(A, b)
        
        return D
        
    
    def _draw_line_segment(self, P0, P1, width, label, output, X, Y):
        x1, y1 = P0
        x2, y2 = P1
        
        hwidth = width/2.0
        pad_width = int(np.ceil(hwidth + 1))
        
        xb_0 = max(min(x1, x2) - pad_width, 0)
        xb_1 = min(max(x1, x2) + pad_width, output.shape[0])
        yb_0 = max(min(y1, y2) - pad_width, 0)
        yb_1 = min(max(y1, y2) + pad_width, output.shape[1])
        
        X_ = X[xb_0:xb_1, yb_0:yb_1]
        Y_ = Y[xb_0:xb_1, yb_0:yb_1]
        
        #im = output[xb_0:xb_1, yb_0:yb_1]
        
        dx = x2 - x1
        dy = y2 - y1
        dist = np.abs(dy*X_ - dx*Y_ + (x2*y1 - y2*x1))/np.sqrt(dx*dx + dy*dy)
        mask = dist <= hwidth
        output[xb_0:xb_1, yb_0:yb_1][mask] = label
        
    
    def rasterize(self, z):
        output = np.zeros(self.do.ds.shape[:2], 'uint8')
        X, Y = np.mgrid[:output.shape[0], :output.shape[1]]
        
        for a in self._annotations:
            if a['z'] == z:
                pts = a['points']
                
                label = int(a['labelID'])
                
                
                for i in range(1, len(pts)):
                    sp = pts[i-1]
                    ep = pts[i]
                    
                    self._draw_line_segment(sp, ep, a['width'], label, output, X, Y)
                    
        return output
                    

def Plug(dsviewer):
    dsviewer.annotation = Annotater(dsviewer)