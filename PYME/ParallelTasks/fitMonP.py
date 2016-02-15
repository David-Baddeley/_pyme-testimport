#!/usr/bin/python

##################
# fitMon.py
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# generated by wxGlade 0.5 on Mon Jun 23 16:22:12 2008 from /home/david/taskMon.wxg

import wx
import wx.grid

import Pyro.core
import time
import os

from PYME.misc.computerName import GetComputerName
compName = GetComputerName()

if 'PYRO_NS_HOSTNAME' in os.environ.keys():
    Pyro.config.PYRO_NS_HOSTNAME=os.environ['PYRO_NS_HOSTNAME']

#if 'PYME_TASKQUEUENAME' in os.environ.keys():
#    taskQueueName = os.environ['PYME_TASKQUEUENAME']
#else:
#    taskQueueName = 'taskQueue'

taskQueueName = 'TaskQueues.%s' % compName

class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.panel_1 = wx.Panel(self, -1)
        self.sizer_4_staticbox = wx.StaticBox(self.panel_1, -1, "Queues")
        self.sizer_5_staticbox = wx.StaticBox(self.panel_1, -1, "Workers")
        #self.sizer_3_staticbox = wx.StaticBox(self.panel_1, -1, "General")
        #self.label_1 = wx.StaticText(self.panel_1, -1, "label_1")
        self.gQueues = wx.grid.Grid(self.panel_1, -1, size=(400, 150))
        self.gWorkers = wx.grid.Grid(self.panel_1, -1, size=(400, 150))

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        
        try:
            from PYME.misc import pyme_zeroconf 
            ns = pyme_zeroconf.getNS()
            URI = ns.resolve(taskQueueName)
        except:
            URI = 'PYRONAME://' + taskQueueName
    
        self.tq = Pyro.core.getProxyForURI(URI)

        #self.tq = Pyro.core.getProxyForURI("PYRONAME://" + taskQueueName)
        self.workerProc = {}
        self.tLast = 0
        self.gQueues.SetRowLabelSize(0)
        self.gWorkers.SetRowLabelSize(0)
        self.onTimer()

        self.timer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        self.timer.Start(10000)


    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("PYME TaskMon")
        self.gQueues.CreateGrid(0, 4)
        self.gQueues.EnableEditing(0)
        self.gQueues.SetColLabelValue(0, "Name")
        self.gQueues.SetColLabelValue(1, "Open")
        self.gQueues.SetColLabelValue(2, "In Progress")
        self.gQueues.SetColLabelValue(3, "Complete")
        self.gQueues.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.gWorkers.CreateGrid(0, 4)
        self.gWorkers.EnableEditing(0)
        self.gWorkers.SetColLabelValue(0, "Name")
        self.gWorkers.SetColLabelValue(1, "Processed")
        self.gWorkers.SetColLabelValue(2, "Tasks/s")
        self.gWorkers.SetColLabelValue(3, "Loc. Tasks/s")
        self.gWorkers.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "Sans"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5 = wx.StaticBoxSizer(self.sizer_5_staticbox, wx.VERTICAL)
        sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.VERTICAL)
        #sizer_3 = wx.StaticBoxSizer(self.sizer_3_staticbox, wx.VERTICAL)
        #sizer_3.Add(self.label_1, 0, 0, 1)
        #sizer_2.Add(sizer_3, 0, wx.LEFT|wx.EXPAND, 5)
        sizer_4.Add(self.gQueues, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_4, 1, wx.LEFT|wx.EXPAND, 5)
        sizer_5.Add(self.gWorkers, 1, wx.EXPAND, 5)
        sizer_2.Add(sizer_5, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 5)
        self.panel_1.SetSizer(sizer_2)
        sizer_1.Add(self.panel_1, 1, wx.EXPAND, 0)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bRemove = wx.Button(self, -1, 'Remove selected Queue(s)')        
        self.bRemove.Bind(wx.EVT_BUTTON, self.OnBRemove)
        hsizer.Add(self.bRemove, 1, wx.ALL, 2)
        sizer_1.Add(hsizer, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade
        
    def OnBRemove(self, event):
        rows = self.gQueues.GetSelectedRows()
        
        for r in rows:
            qn = self.queueNames[r]
            self.tq.removeQueue(qn)

    def onTimer(self, ev = None):
        queues = self.tq.getQueueNames()
        self.queueNames = queues
        nq = len(queues)

        self.gQueues.ClearGrid()

        n = nq + 2
        #print n
        if (n > self.gQueues.GetNumberRows()):
            self.gQueues.AppendRows(n - self.gQueues.GetNumberRows())
        elif(n < self.gQueues.GetNumberRows()):
            self.gQueues.DeleteRows(0,self.gQueues.GetNumberRows()- n)
            
        for i in range(nq):
            self.gQueues.SetCellValue(i, 0,queues[i])
            self.gQueues.SetCellValue(i, 1, '%d' % self.tq.getNumberOpenTasks(queues[i]))
            self.gQueues.SetCellValue(i, 2, '%d' % self.tq.getNumberTasksInProgress(queues[i]))
            self.gQueues.SetCellValue(i, 3, '%d' % self.tq.getNumberTasksCompleted(queues[i]))

        
        self.gQueues.SetCellValue(n - 1, 0,'Total')
        self.gQueues.SetCellValue(n - 1, 1, '%d' % self.tq.getNumberOpenTasks())
        self.gQueues.SetCellValue(n - 1, 2, '%d' % self.tq.getNumberTasksInProgress())
        self.gQueues.SetCellValue(n - 1, 3, '%d' % self.tq.getNumberTasksCompleted())

        
        workers = self.tq.getWorkerNames()
        
        nw = len(workers)

        self.gWorkers.ClearGrid()

        n = nw + 2
        #print n
        if (n > self.gWorkers.GetNumberRows()):
            self.gWorkers.AppendRows(n - self.gWorkers.GetNumberRows())
        elif(n < self.gWorkers.GetNumberRows()):
            self.gWorkers.DeleteRows(0,self.gWorkers.GetNumberRows()- n)

        tm = time.time()
        dt = float(tm - self.tLast)
        self.tLast = tm

        #print dt
    
        for i in range(nw):
            self.gWorkers.SetCellValue(i, 0,workers[i])
            nt = self.tq.getNumTasksProcessed(workers[i])
            #print nt
            self.gWorkers.SetCellValue(i, 1, '%d' % nt)
            if workers[i] in self.workerProc.keys():
                fps =  (nt - self.workerProc[workers[i]])/dt
                self.gWorkers.SetCellValue(i, 2, '%3.3f' % fps)
            self.workerProc[workers[i]] = nt
            self.gWorkers.SetCellValue(i, 3, '%d' % self.tq.getWorkerFPS(workers[i]))


        
        self.gWorkers.SetCellValue(n - 1, 0,'Total')
        nt = self.tq.getNumTasksProcessed()
        #print nt
        self.gWorkers.SetCellValue(n -1, 1, '%d' % nt)
        if 'Total' in self.workerProc.keys():   
            self.gWorkers.SetCellValue(n - 1, 2, '%3.3f' % ((nt - int(self.workerProc['Total']))/dt,))
        self.workerProc['Total'] = nt

        self.Layout()
        


       
        

# end of class MyFrame
    
def main():
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    fTaskMon = MyFrame(None, -1, "")
    app.SetTopWindow(fTaskMon)
    fTaskMon.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
