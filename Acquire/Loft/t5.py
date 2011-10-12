#!/usr/bin/python

##################
# t5.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################

import sys
sys.path.append(".")

import example
import vfr
import previewaquisator

example.CShutterControl.init()
cam = example.CCamera()
cam.Init()

cam.SetHorizBin(1)
cam.SetVertBin(1)
cam.SetCOC()
cam.GetStatus()

class chaninfo:
    names = ['bw']
    cols = [1]
    hw = [example.CShutterControl.CH1]

pa = previewaquisator.PreviewAquisator(chaninfo,cam)

pa.Prepare()

fr = vfr.ViewFrame(None, "Live Prev", pa.ds)

def refr(source):
    fr.vp.Refresh()

pa.WantFrameNotification.append(refr)
fr.Show()

pa.start()