import wx
import wx.lib.agw.aui as aui
import PYME.ui.autoFoldPanel as afp

class AUIFrame(wx.Frame):
    """A class which encapsulated the common frame layout code used by
    dsviewer, VisGUI, and PYMEAcquire.
    
    """
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        
        self.SetAutoLayout(True)
        
        self._mgr = aui.AuiManager(agwFlags = aui.AUI_MGR_DEFAULT | aui.AUI_MGR_AUTONB_NO_CAPTION)
        atabstyle = self._mgr.GetAutoNotebookStyle()
        self._mgr.SetAutoNotebookStyle((atabstyle ^ aui.AUI_NB_BOTTOM) | aui.AUI_NB_TOP)
        # tell AuiManager to manage this frame
        self._mgr.SetManagedWindow(self)
        
        #wx.EVT_SIZE(self, self.OnSize)
        
        self.paneHooks = []
        self.pane0 = None

        self._menus = {}
        # Menu Bar
        self.menubar = wx.MenuBar()
        self.SetMenuBar(self.menubar)

        
    def AddPage(self, page=None, select=True,caption='Dummy', update=True):
        """Add a page to the auto-notebook
        

        Parameters
        ----------
        page : wx.Window instance  
            The page to add, usually a wx.Panel. The window should have been
            created with this window as the parent.
        select : bool 
            Should the page be displayed above previous pages?
        caption : string 
            The caption to appear in the notebook tab 
        
        """
        #if update:
        #    self._mgr.Update()
            
        if self.pane0 is None:
            name = caption.replace(' ', '')
            self._mgr.AddPane(page, aui.AuiPaneInfo().
                          Name(name).Caption(caption).Centre().CloseButton(False).CaptionVisible(False))
            self.pane0 = name
        else:
            self._mgr.Update()
            pn = self._mgr.GetPaneByName(self.pane0)
            if pn.IsNotebookPage():
                print((pn.notebook_id))
                nbs = self._mgr.GetNotebooks()
                if len(nbs) > pn.notebook_id:
                    currPage = nbs[pn.notebook_id].GetSelection()
                self._mgr.AddPane(page, aui.AuiPaneInfo().
                              Name(caption.replace(' ', '')).Caption(caption).CloseButton(False).CaptionVisible(False).NotebookPage(pn.notebook_id))
                if (not select) and len(nbs) > pn.notebook_id:
                    self._mgr.Update()
                    nbs[pn.notebook_id].SetSelection(currPage)
            else:
                self._mgr.AddPane(page, aui.AuiPaneInfo().
                              Name(caption.replace(' ', '')).Caption(caption).CloseButton(False).CaptionVisible(False), target=pn)
                
                
                if not select:
                    self._mgr.Update()
                    nb = self._mgr.GetNotebooks()[0]
                    nb.SetSelection(0)
        if update:
            self._mgr.Update()
               
        #wx.CallAfter(self._mgr.Update)
        #self.Layout() 
        #self.OnSize(None)
        #self.OnSize(None)
        
    def OnSize(self, event):
        #self.Layout()
        self._mgr.Update()
        #self.Refresh()
        #self.Update()
        
    def CreateFoldPanel(self):
        """Create a panel of folding 'drawers' on the left side of the frame.
        loops over all the functions defined in self.paneHooks and calls them
        to generate the drawers.
        """
        pinfo = self._mgr.GetPaneByName('sidePanel')
        if pinfo.IsOk(): #we already have a sidepanel, clear
            self.sidePanel.Clear()
        else:
            self.sidePanel = afp.foldPanel(self, -1, wx.DefaultPosition,size = wx.Size(180, 1000))
            pinfo = aui.AuiPaneInfo().Name("sidePanel").Left().CloseButton(False).CaptionVisible(False)

            self._mgr.AddPane(self.sidePanel, pinfo)
            
        if len(self.paneHooks) > 0:
            pinfo.Show()

            for genFcn in self.paneHooks:
                genFcn(self.sidePanel)
        else:
            pinfo.Hide()
            

        self._mgr.Update()
        self.Refresh()
        self.Update()
        self._mgr.Update()

    def AddMenuItem(self, menuName, itemName='', itemCallback = None, itemType='normal', helpText = '', id = wx.ID_ANY):   
        """
        Add a menu item to dh5view, VisGUI, or PYMEAcquire.

        Parameters
        ----------
        menuName : basestring
            The name of the menu to add an item to. Submenus are optionally designated by using ``>`` characters as a separator, e.g. ``"File>Recent"``.
            If a menu or submenu does not already exist it is created.

        itemName : basestring
            The name of the item to add. Required if itemType is 'normal' or 'check'. wxpython accelerator specification is supported.

        itemCallback : function
            A function to call when the menu item is selected. Should accept a wx.Event as the first and only argument.

        itemType : basestring
            One of 'normal', 'check', or 'separator'.
        helpText : basestring
        id : int
            wx ID for the menu item. Should normally be ignored, and only set if there is a standard ID for the menu item, and facilitates
            using platform standard icons and shortcuts for open, save, quit, etc ....

        Returns
        -------

        """
        mItem = None
        if not menuName in self._menus.keys():
            menuParts = menuName.split('>')
            top_level = menuParts[0]
            for i, part in enumerate(menuParts):
                mn = '>'.join(menuParts[:(i+1)])
                if not mn in self._menus.keys():
                    menu = wx.Menu()

                    if i == 0: #top level menu
                        #put new menus to the left of help or modules menus
                        lp = 0
                        if 'Help' in self._menus.keys():
                            lp +=1

                        if '&Modules' in self._menus.keys():
                            lp += 1

                        self.menubar.Insert(self.menubar.GetMenuCount()-lp, menu, part)
                    else:
                        parent = self._menus['>'.join(menuParts[:i])]
                        parent.AppendSubMenu(menu, part)

                    self._menus[mn] = menu
        else:
            menu = self._menus[menuName]
        
        if itemType == 'normal':        
            mItem = menu.Append(id, itemName, helpText, wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, itemCallback, mItem)
        elif itemType == 'check':
            mItem = menu.Append(id, itemName, helpText, wx.ITEM_CHECK)
            self.Bind(wx.EVT_MENU, itemCallback, mItem)
        elif itemType == 'separator':
            menu.AppendSeparator()
            
        return mItem
        
    def _cleanup(self):
        #self.timer.Stop()
        #for some reason AUI doesn't clean itself up properly and stops the
        #window from being garbage collected - fix this here
        self._mgr.UnInit()
        self._mgr._frame = None
        #if self.glCanvas:
        #    self.glCanvas.wantViewChangeNotification.remove(self)
        self.Destroy()
