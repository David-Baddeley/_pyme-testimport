#!/usr/bin/python

##################
# HDFDataSource.py
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

#from PYME.ParallelTasks.relativeFiles import getFullFilename
#import tables
from .BaseDataSource import BaseDataSource

#import httplib
#import urllib
#import requests
#import cPickle as pickle
import time
import json

SHAPE_LIFESPAN = 30

from PYME.io import clusterIO
from PYME.io import PZFFormat
from PYME.io import MetaDataHandler

class DataSource(BaseDataSource):
    moduleName = 'ClusterPZFDataSource'
    def __init__(self, url, queue=None):
        self.seriesName = url
        print url
        self.clusterfilter = url.split('://')[1].split('/')[0]
        print self.clusterfilter
        self.sequenceName = url.split('://%s/' % self.clusterfilter)[1]
        print self.sequenceName
        self.lastShapeTime = 0
        
        mdfn = '/'.join([self.sequenceName, 'metadata.json'])  
        
        print mdfn
        
        self.mdh = MetaDataHandler.NestedClassMDHandler()
        self.mdh.update(json.loads(clusterIO.getFile(mdfn, self.clusterfilter)))
        
        self.fshape = None#(self.mdh['Camera.ROIWidth'],self.mdh['Camera.ROIHeight'])
        
        self._getNumFrames()
    
    def _getNumFrames(self):
        frameNames = [f for f in clusterIO.listdir(self.sequenceName, self.clusterfilter) if f.endswith('.pzf')]
        self.numFrames = len(frameNames)
        self.lastShapeTime = time.time()
    
    def getSlice(self, ind):
        frameName = '%s/frame%05d.pzf' % (self.sequenceName, ind)
        sl = PZFFormat.loads(clusterIO.getFile(frameName, self.clusterfilter))[0]
        
        #print sl.shape, sl.dtype
        return sl.squeeze()

    def getSliceShape(self):
        if self.fshape is None:
            self.fshape = self.getSlice(0).shape
        return self.fshape
        
    def getNumSlices(self):
        t = time.time()
        if (t-self.lastShapeTime) > SHAPE_LIFESPAN:
            self._getNumFrames()
            
        return self.numFrames

    def getEvents(self):
        eventFileName = self.sequenceName + '/events.json'
        try:
            return json.loads(clusterIO.getFile(eventFileName, self.clusterfilter))
        except IOError:
            #our series might not have any events
            return []
        
    def getMetadata(self):
        return self.mdh
 
