#!/usr/bin/python

##################
# <filename>.py
#
# Copyright David Baddeley, 2012
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

class MDParam(object):
    def __init__(self):
        pass
        #, mdToUpdate=None):
        #self.mdToUpdate = mdToUpdate

    #def OnChange(self, event=None):
    #    if not self.mdToUpdate is None:
    #        self.retrieveValue(self.mdToUpdate)


class FloatParam(MDParam):
    def __init__(self, paramName, guiName, default=0, helpText='', **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, self.guiName), 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tValue = wx.TextCtrl(parent, -1, value='0', size=(50, -1))

        hsizer.Add(self.tValue, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.tValue.Bind(wx.EVT_TEXT, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = float(self.tValue.GetValue())

    def updateValue(self, mdh, **kwargs):
        self.tValue.SetValue('%3.2f' % mdh.getOrDefault(self.paramName, self.default))
        

class IntParam(MDParam):
    def __init__(self, paramName, guiName, default=0, helpText='', **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, self.guiName), 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tValue = wx.TextCtrl(parent, -1, value='0', size=(50, -1))
        hsizer.Add(self.tValue, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.tValue.Bind(wx.EVT_TEXT, lambda e : self.retrieveValue(mdh))
        
        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = int(self.tValue.GetValue())

    def updateValue(self, mdh, **kwargs):
        self.tValue.SetValue('%d' % mdh.getOrDefault(self.paramName, self.default))

class RangeParam(MDParam):
    def __init__(self, paramName, guiName, default=[0, 0], helpText='', **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, self.guiName), 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tValue = wx.TextCtrl(parent, -1, value='', size=(50, -1))

        hsizer.Add(self.tValue, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.tValue.Bind(wx.EVT_TEXT, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = tuple([int(v) for v in self.tValue.GetValue().split(':')])

    def updateValue(self, mdh, **kwargs):
        val = ':'.join(['%d' % v for v in mdh.getOrDefault(self.paramName, self.default)])
        self.tValue.SetValue(val)
        
        
class StringParam(MDParam):
    def __init__(self, paramName, guiName, default='', helpText='', **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, self.guiName), 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tValue = wx.TextCtrl(parent, -1, value='0', size=(50, -1))
        
        hsizer.Add(self.tValue, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.tValue.Bind(wx.EVT_TEXT, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = self.tValue.GetValue()

    def updateValue(self, mdh, **kwargs):
        self.tValue.SetValue(mdh.getOrDefault(self.paramName, self.default))

        
class FloatListParam(MDParam):
    def __init__(self, paramName, guiName, default='', helpText='', **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default

        MDParam.__init__(self, **kwargs)
        
    def _valToString(self, values):
        return ''.join(['%3.2f' % v for v in values])
        
    def _strToVal(self, s):
        sl = s.split(',')
        return [float(si) for si in sl]
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, self.guiName), 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.tValue = wx.TextCtrl(parent, -1, value='0', size=(50, -1))

        hsizer.Add(self.tValue, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.tValue.Bind(wx.EVT_TEXT, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = self._strToVal(self.tValue.GetValue())

    def updateValue(self, mdh, **kwargs):
        self.tValue.SetValue(self._valToString(mdh.getOrDefault(self.paramName, self.default)))
        

class ChoiceParam(MDParam):
    def __init__(self, paramName, guiName, default='', helpText='', choices = [], choiceNames = [], **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default
        self.choices = choices
        self.choiceNames = choiceNames
        if choiceNames == []:
            self.choiceNames = choices

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, self.guiName), 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.cValue = wx.Choice(parent, -1, choices = self.choiceNames, size=(100, -1))

        hsizer.Add(self.cValue, 1,wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.cValue.Bind(wx.EVT_CHOICE, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = self.choices[self.cValue.GetSelection()]

    def updateValue(self, mdh, **kwargs):
        self.cValue.SetSelection(self.choices.index(mdh.getOrDefault(self.paramName, self.default)))
        
        
        
class FilenameParam(MDParam):
    def __init__(self, paramName, guiName, default='<none>', helpText='', 
                    prompt='Please select file', wildcard='All files|*.*', filename = None, **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default
        self.filename = default
        if not filename == None:
            self.filename = filename
        self.prompt = prompt
        self.wildcard = wildcard

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx, os
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        FieldText = '%s %s' %(self.guiName, self.default)

        self.stFilename = wx.StaticText(parent, -1, FieldText)
        hsizer.Add(self.stFilename, 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        bSetFile = wx.Button(parent, -1, 'Set', style=wx.BU_EXACTFIT)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            bSetFile.Bind(wx.EVT_BUTTON, self._setFile)
        hsizer.Add(bSetFile, 0,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 0)

        return hsizer
        
    def _setFile(self, event=None):
        import wx,os
        fdialog = wx.FileDialog(None, self.prompt,
                    #defaultDir=os.path.split(self.image.filename)[0],
                    wildcard=self.wildcard, style=wx.OPEN)
        succ = fdialog.ShowModal()
        if (succ == wx.ID_OK):
            #self.ds = example.CDataStack(fdialog.GetPath().encode())
            #self.ds =
            #psfFilename = fdialog.GetPath()
            #self.image.mdh.setEntry('PSFFile', getRelFilename(psfFilename))
            self.filename = fdialog.GetPath()
            #self.md.setEntry('PSFFile', psfFilename)
            self.stFilename.SetLabel('%s %s' % (self.guiName, os.path.split(self.filename)[1]))
            self.stFilename.SetForegroundColour(wx.Colour(0, 128, 0))

            if self.mdToUpdate and not (self.filename == self.default):
                self.OnChange()

            return True
        else:
            return False
        
    def retrieveValue(self, mdh):
        if not self.filename == self.default:
            mdh[self.paramName] = self.filename
        elif self._setFile():
            #try to call this manually
            mdh[self.paramName] = self.filename
        else:
            raise RuntimeError('Required fit filename %s not defined' % self.paramName)

    def updateValue(self, mdh, **kwargs):
        import os, wx
        haveFile = False

        if self.paramName in mdh.getEntryNames():
            self.filename = mdh[self.paramName]
            FieldText = '%s ' % self.guiName + os.path.split(mdh[self.paramName])[1]
            haveFile = True
            #print(FieldText)

            self.stFilename.SetLabel(FieldText)
            #self.stFilename.SetForegroundColour(wx.Colour(0, 128, 0))
        else:
            FieldText = '%s %s' %(self.guiName, self.default)
            self.stFilename.SetLabel(FieldText)
            #self.stFilename.SetForegroundColour(wx.Colour(0, 0, 0))

        #print self.filename, self.default
        if (self.filename == self.default) or (self.filename == ''):
            self.stFilename.SetForegroundColour(wx.Colour(0, 0, 0))
        else:
            self.stFilename.SetForegroundColour(wx.Colour(0, 128, 0))
       

class ShiftFieldParam(FilenameParam):    
    def retrieveValue(self, mdh):
        import numpy as np
        
        oldfn = mdh.getOrDefault(self.paramName, None)
        if 'chroma.dx' in mdh.getEntryNames():
            if self.filename == self.default:
                self.filename = 'legacy'
                oldfn = 'legacy'
        FilenameParam.retrieveValue(self, mdh)
        
        if not self.filename == oldfn:
            dx, dy = np.load(self.filename)
            mdh.setEntry('chroma.dx', dx)
            mdh.setEntry('chroma.dy', dy)
        

class BoolParam(MDParam):
    def __init__(self, paramName, guiName, default=False, helpText='', **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.cbValue = wx.CheckBox(parent, -1, self.guiName)
        #self.cbValue.SetValue(self.default)
        
        hsizer.Add(self.cbValue, 1,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)
            self.retrieveValue(mdh)
            self.cbValue.Bind(wx.EVT_CHECKBOX, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        mdh[self.paramName] = self.cbValue.GetValue()  

    def updateValue(self, mdh, **kwargs):
        self.cbValue.SetValue(mdh.getOrDefault(self.paramName, self.default))
 

class BoolFloatParam(MDParam):
    def __init__(self, paramName, guiName, default=False, helpText='', ondefault=0, offvalue=0, **kwargs):
        self.paramName = paramName
        self.guiName = guiName
        self.default = default
        self.ondefault = ondefault
        self.offvalue = offvalue

        MDParam.__init__(self, **kwargs)
        
    def createGUI(self, parent, mdh, syncMdh=False, mdhChangedSignal=None):
        import wx
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.cbValue = wx.CheckBox(parent, -1, self.guiName)
        hsizer.Add(self.cbValue, 1,wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.tValue = wx.TextCtrl(parent, -1, value='0', size=(50, -1))
        hsizer.Add(self.tValue, 0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.updateValue(mdh)

        if syncMdh:
            if mdhChangedSignal:
                mdhChangedSignal.connect(self.updateValue)

            self.retrieveValue(mdh)

            self.cbValue.Bind(wx.EVT_CHECKBOX, lambda e : self.retrieveValue(mdh))
            self.tValue.Bind(wx.EVT_TEXT, lambda e : self.retrieveValue(mdh))

        return hsizer
        
    def retrieveValue(self, mdh):
        if self.cbValue.GetValue():
            mdh[self.paramName] = float(self.tValue.GetValue())
        else:
            mdh[self.paramName] = float(self.offvalue)

    def updateValue(self, mdh, **kwargs):
        try:
            fval = mdh[self.paramName]
            if (fval == self.offvalue):
                fval = self.ondefault
                cval = False
            else:
                cval = True
        except (KeyError, AttributeError):
            fval = self.ondefault
            cval = self.default

        self.tValue.SetValue('%3.2f' % fval)
        self.cbValue.SetValue(cval)



