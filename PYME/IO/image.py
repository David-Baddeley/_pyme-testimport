#!/usr/bin/python
##################
# image.py
#
# Copyright David Baddeley, 2011
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
#try:
#    print 'trying to import javabridge & bioformats'
#    import javabridge
#    print 'imported javabridge'
#    import bioformats
#    print 'imported bioformats'
#    javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
#    print 'started java VM'
#except:
#    pass

from __future__ import print_function
import os
import numpy

import weakref

from PYME.IO import MetaDataHandler
from PYME.Analysis import MetaData
from PYME.IO import dataWrap
from PYME.IO.DataSources import BufferedDataSource
#from PYME.LMVis.visHelpers import ImageBounds

from PYME.IO.FileUtils.nameUtils import getRelFilename
from collections import namedtuple
from six import string_types

VS = namedtuple('VS', 'x,y,z')

class ImageBounds:
    def __init__(self, x0, y0, x1, y1, z0=0, z1=0):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.z0 = z0
        self.z1 = z1

    @classmethod
    def estimateFromSource(cls, ds):
        return cls(ds['x'].min(),ds['y'].min(),ds['x'].max(), ds['y'].max() )

    def width(self):
        return self.x1 - self.x0

    def height(self):
        return self.y1 - self.y0

    @classmethod
    def extractFromMetadata(cls, mdh):
        x0 = 0
        y0 = 0

        x1 = mdh['Camera.ROIWidth'] * 1e3 * mdh['voxelsize.x']
        y1 = mdh['Camera.ROIHeight'] * 1e3 * mdh['voxelsize.y']

        if 'Splitter' in mdh.getOrDefault('Analysis.FitModule', ''):
            if 'Splitter.Channel0ROI' in mdh.getEntryNames():
                rx0, ry0, rw, rh = mdh['Splitter.Channel0ROI']
                x1 = rw * 1e3 * mdh['voxelsize.x']
                x1 = rh * 1e3 * mdh['voxelsize.x']
            else:
                y1 = y1 / 2

        return cls(x0, y0, x1, y1)


lastdir = ''

class _DefaultDict(dict):
    """dictionary which returns a default value (0) for items not in the list"""
    def __init__(self, *args):
        dict.__init__(self, *args)

    def __getitem__(self, index):
        try:
            return dict.__getitem__(self, index)
        except KeyError:
            return 0

#keep track of open images - to allow compositing of images etc ... without
#relying on some GUI or global magic to keep track of windows
#use a weakref dictionary so that they still get garbage collected when they
#cease to be used elsewhere
openImages = weakref.WeakValueDictionary()

#this is going to determine the numbering of each new image - images are
#created with a stub name e.g. 'Untitled Image', or 'Filter result', followed
#by an incrementing index - this dictionary stores the current index for each 
#stub. If a stub hasn't been used yet, the index defaults to zero.
nUntitled = _DefaultDict()

class ImageStack(object):
    """ An Image Stack. This is the core PYME image type and wraps around the various different supported file formats.

        This is a essentially a wrapper of the image data and any ascociated
        metadata. The class can be given a ndarray like* data source, or
        alternatively supports loading from file, or from a PYME task queue
        URI, in which case individual slices will be fetched from the server
        as required.

        For details on the file type support, see the Load method.

        You should provide one of the 'data' or 'filename' parmeters,
        with all other parameters being optional.

        Parameters
        ----------
        data
            Image data. Something that supports ndarray like slicing and exposes
            a .shape parameter, something implementing the
            PYME.IO.DataSources interface, or a list of either
            of the above. Dimensionality can be between 1 and 4, with
            the dimensions being interpreted as x, y, z/t, colour.
            A mangled (will support slicing, but not necessarily other array
            operations) version of the data will be stored as the .data
            member of the class.

        mdh : something derived from PYME.IO.MetaDataHandler.MDHandlerBase
            Image metadata. If None, and empty one will be created.

        filename : str
            filename of the data to load (see Load), or PYME queue identifier

        queueURI : str
            PYRO URI of the task server. This exists to optionally speed up
            loading from a queue by eliminating the PYRO nameserver
            lookup. The queue name itself should be passed in the filename,
            with a leading QUEUE://.

        events : list / array
            An array of time series events (TODO - more doc)

        haveGUI : bool
            Whether we have a wx GUI available, so that we can
            display dialogs asking for, e.g. a file name if no
            data or filename is supplied, or for missing metadata
            entries

        Attributes
        ----------
        data : PYME.IO.DataSources data source.
            This is an object which can be sliced as though it was a numpy array, and which yields a numpy array as a
            result of the slicing. It differs from an array in that it loads data lazily (i.e. individual chunks might
            still be on disk, and are only loaded and assembled into an array when sliced). Slicing is the only array
            operation permitted.

        mdh : PYME.IO.MetdataHandler metadata source
            This contains image metadata. It behaves like a dictionary, and individual metadata entries can be accessed by key.

        events : list/array
            Any events which occured during image acquisition

        voxelsize : 3-tuple (float)
            The image voxel size in nm

        pixelsize : float
            The pixelsize in nm (shortcut for voxelsize[0])

        names : list of str
            The channel names

        origin : tuple of float
            position, in nm, of the top-left pixel in the image from the camera origin. Useful for lining up images taken
            with different ROIs.

        """
    def __init__(self, data = None, mdh = None, filename = None, queueURI = None, events = [], titleStub='Untitled Image', haveGUI=True):

        global nUntitled
        self.data = data      #image data
        self.mdh = mdh        #metadata (a MetaDataHandler class)
        self.events = events  #events

        self.queueURI = queueURI
        self.filename = filename

        self.haveGUI = haveGUI

        #default 'mode' / image type - see PYME/DSView/modules/__init__.py        
        self.mode = 'LM'

        self.saved = False
        self.volatile = False #is the data likely to change and need refreshing?
        
        #support for specifying metadata as filename
        if isinstance(mdh, string_types):#os.path.exists(mdh):
            self.mdh = None
            self._findAndParseMetadata(mdh)
        
        if (data is None):
            #if we've supplied data, use that, otherwise load from file
            self.Load(filename)

        #do the necessary munging to get the data in the format we want it        
        self.SetData(self.data)

        #generate a placeholder filename / window title        
        if self.filename is None:
            self.filename = '%s %d' % (titleStub, nUntitled[titleStub])
            nUntitled[titleStub] += 1
            
            self.seriesName = self.filename

        #generate some empty metadata if we don't have any        
        if self.mdh is None:
            self.mdh = MetaDataHandler.NestedClassMDHandler()

        #hack to make spectral data behave right - doesn't really belong here        
        if 'Spectrum.Wavelengths' in self.mdh.getEntryNames():
            self.xvals = self.mdh['Spectrum.Wavelengths']
            self.xlabel = 'Wavelength [nm]'

        #if we have 1D data, plot as graph rather than image        
        if self.data.shape[1] == 1:
            self.mode = 'graph'

        #add ourselves to the list of open images        
        openImages[self.filename] = self

    def SetData(self, data):
        """
        Set / replace the data associated with the image. This is primarily used in the acquisition program when we want
        a live view of constantly updating data. It is also used for the same purpose during deconvolution.

        Parameters
        ----------
        data : numpy array or PYME.IO.DataSources datasource

        Returns
        -------

        """
        #the data does not need to be a numpy array - it could also be, eg., queue data
        #on a remote server - wrap so that is is indexable like an array
        self.data = dataWrap.Wrap(data)
    
    @property
    def voxelsize(self):
        """Returns voxel size, in nm, as a 3-tuple. Expects metadata voxel size
        to be in um"""
        try:
            return VS(1e3*self.mdh['voxelsize.x'], 1e3*self.mdh['voxelsize.y'],  1e3*self.mdh['voxelsize.z'])
        except:
            return (1,1,1)    
    
    @property
    def pixelSize(self):
        try:
            return 1e3*self.mdh['voxelsize.x']
        except:
            return 1

    @pixelSize.setter
    def pixelSize(self, value):
        self.mdh['voxelsize.x'] = .001*value
        self.mdh['voxelsize.y'] = .001*value

    @property
    def sliceSize(self):
        try:
            return 1e3*self.mdh['voxelsize.z']
        except:
            return 1

    @sliceSize.setter
    def sliceSize(self, value):
        self.mdh['voxelsize.z'] = .001*value


    @property
    def names(self):
        """Return the names of the colour channels"""
        try:
            return self.mdh['ChannelNames']
        except:
            return ['Chan %d'% d for d in range(self.data.shape[3])]

    @names.setter
    def names(self, value):
        self.mdh['ChannelNames'] = value

    @property
    def imgBounds(self):
        """Return the bounds (or valid area) of the image in nm as (x0, y0, x1, y1, z0, z1)"""
        try:
            return ImageBounds(self.mdh['ImageBounds.x0'],self.mdh['ImageBounds.y0'],self.mdh['ImageBounds.x1'],self.mdh['ImageBounds.y1'],self.mdh['ImageBounds.z0'],self.mdh['ImageBounds.z1'])
        except:
            return ImageBounds(0, 0, self.pixelSize*self.data.shape[0], self.pixelSize*self.data.shape[1],0, self.sliceSize*self.data.shape[2])

    @imgBounds.setter
    def imgBounds(self, value):
        self.mdh['ImageBounds.x0'] = value.x0
        self.mdh['ImageBounds.y0'] = value.y0
        self.mdh['ImageBounds.x1'] = value.x1
        self.mdh['ImageBounds.y1'] = value.y1
        self.mdh['ImageBounds.z0'] = value.z0
        self.mdh['ImageBounds.z1'] = value.z1

    @property
    def metadata(self):
        return self.mdh
        
    @property
    def origin(self):
        #the origin, in nm from the camera - used for overlaying with different ROIs
        
            
        if 'Origin.x' in self.mdh.getEntryNames():
            return self.mdh['Origin.x'], self.mdh['Origin.y'], self.mdh['Origin.z']
        
        elif 'Camera.ROIPosX' in self.mdh.getEntryNames():
            #has ROI information
            try:
                voxx, voxy = 1e3*self.mdh['voxelsize.x'], 1e3*self.mdh['voxelsize.y']
            except AttributeError:
                voxx = self.pixelSize
                voxy = voxx
            
            ox = (self.mdh['Camera.ROIPosX'] - 1)*voxx
            oy = (self.mdh['Camera.ROIPosY'] - 1)*voxy
            
            oz = 0
            
            if 'AcquisitionType' in self.mdh.getEntryNames() and self.mdh['AcquisitionType'] == 'Stack':
                oz = self.mdh['StackSettings.StartPos']*1e3
            elif 'Positioning.PIFoc' in self.mdh.getEntryNames():
                oz = self.mdh['Positioning.PIFoc']*1e3
            
            return ox, oy, oz
            
        elif 'Source.Camera.ROIPosX' in self.mdh.getEntryNames():
            #a rendered image with information about the source ROI
            voxx, voxy = 1e3*self.mdh['Source.voxelsize.x'], 1e3*self.mdh['Source.voxelsize.y']
            
            ox = (self.mdh['Source.Camera.ROIPosX'] - 1)*voxx
            oy = (self.mdh['Source.Camera.ROIPosY'] - 1)*voxy
            
            return ox, oy, 0
            
        else:
            return 0,0, 0
            


    def _loadQueue(self, filename):
        """Load data from a remote PYME.ParallelTasks.HDFTaskQueue queue using
        Pyro.
        
        Parameters:
        -----------

        filename  : string
            the name of the queue         
        
        """
        import Pyro.core
        from PYME.IO.DataSources import TQDataSource
        from PYME.misc.computerName import GetComputerName
        compName = GetComputerName()

        if self.queueURI is None:
            #do a lookup
            taskQueueName = 'TaskQueues.%s' % compName
            
            try:
                from PYME.misc import pyme_zeroconf 
                ns = pyme_zeroconf.getNS()
                URI = ns.resolve(taskQueueName)
            except:
                URI = 'PYRONAME://' + taskQueueName
            
            self.tq = Pyro.core.getProxyForURI(URI)
        else:
            self.tq = Pyro.core.getProxyForURI(self.queueURI)

        self.seriesName = filename[len('QUEUE://'):]

        self.dataSource = TQDataSource.DataSource(self.seriesName, self.tq)
        self.data = self.dataSource #this will get replaced with a wrapped version

        self.mdh = MetaDataHandler.QueueMDHandler(self.tq, self.seriesName)
        MetaData.fillInBlanks(self.mdh, self.dataSource)

        #self.timer.WantNotification.append(self.dsRefresh)

        self.events = self.dataSource.getEvents()

    def _loadh5(self, filename):
        """Load PYMEs semi-custom HDF5 image data format. Offloads all the
        hard work to the HDFDataSource class"""
        import tables
        from PYME.IO.DataSources import HDFDataSource, BGSDataSource
        from PYME.IO import tabular

        self.dataSource = HDFDataSource.DataSource(filename, None)
        #chain on a background subtraction data source, so we can easily do 
        #background subtraction in the GUI the same way as in the analysis
        self.data = BGSDataSource.DataSource(self.dataSource) #this will get replaced with a wrapped version

        if 'MetaData' in self.dataSource.h5File.root: #should be true the whole time
            self.mdh = MetaData.TIRFDefault
            self.mdh.copyEntriesFrom(MetaDataHandler.HDFMDHandler(self.dataSource.h5File))
        else:
            self.mdh = MetaData.TIRFDefault
            wx.MessageBox("Carrying on with defaults - no gaurantees it'll work well", 'ERROR: No metadata found in file ...', wx.OK)
            print("ERROR: No metadata fond in file ... Carrying on with defaults - no gaurantees it'll work well")

        #attempt to estimate any missing parameters from the data itself        
        MetaData.fillInBlanks(self.mdh, self.dataSource)

        #calculate the name to use when we do batch analysis on this        
        #from PYME.IO.FileUtils.nameUtils import getRelFilename
        self.seriesName = getRelFilename(filename)

        #try and find a previously performed analysis
        fns = filename.split(os.path.sep)
        cand = os.path.sep.join(fns[:-2] + ['analysis',] + fns[-2:]) + 'r'
        print(cand)
        if False:#os.path.exists(cand):
            h5Results = tables.openFile(cand)

            if 'FitResults' in dir(h5Results.root):
                self.fitResults = h5Results.root.FitResults[:]
                self.resultsSource = tabular.h5rSource(h5Results)

                self.resultsMdh = MetaData.TIRFDefault
                self.resultsMdh.copyEntriesFrom(MetaDataHandler.HDFMDHandler(h5Results))

        self.events = self.dataSource.getEvents()
        
    def _loadHTTP(self, filename):
        """Load PYMEs semi-custom HDF5 image data format. Offloads all the
        hard work to the HDFDataSource class"""
        import tables
        from PYME.IO.DataSources import HTTPDataSource, BGSDataSource
        #from PYME.LMVis import inpFilt
        
        #open hdf5 file
        self.dataSource = HTTPDataSource.DataSource(filename)
        #chain on a background subtraction data source, so we can easily do 
        #background subtraction in the GUI the same way as in the analysis
        self.data = BGSDataSource.DataSource(self.dataSource) #this will get replaced with a wrapped version

        #try: #should be true the whole time
        self.mdh = MetaData.TIRFDefault
        self.mdh.copyEntriesFrom(self.dataSource.getMetadata())
        #except:
        #    self.mdh = MetaData.TIRFDefault
        #    wx.MessageBox("Carrying on with defaults - no gaurantees it'll work well", 'ERROR: No metadata found in file ...', wx.OK)
        #    print("ERROR: No metadata fond in file ... Carrying on with defaults - no gaurantees it'll work well")

        #attempt to estimate any missing parameters from the data itself        
        MetaData.fillInBlanks(self.mdh, self.dataSource)

        #calculate the name to use when we do batch analysis on this        
        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = filename

        self.events = self.dataSource.getEvents()
        
    def _loadClusterPZF(self, filename):
        """Load PYMEs semi-custom HDF5 image data format. Offloads all the
        hard work to the HDFDataSource class"""

        from PYME.IO.DataSources import ClusterPZFDataSource, BGSDataSource

        self.dataSource = ClusterPZFDataSource.DataSource(filename)
        #chain on a background subtraction data source, so we can easily do 
        #background subtraction in the GUI the same way as in the analysis
        self.data = BGSDataSource.DataSource(self.dataSource) #this will get replaced with a wrapped version

        #try: #should be true the whole time
        self.mdh = MetaData.TIRFDefault
        self.mdh.copyEntriesFrom(self.dataSource.getMetadata())

        #attempt to estimate any missing parameters from the data itself        
        MetaData.fillInBlanks(self.mdh, self.dataSource)

        #calculate the name to use when we do batch analysis on this        
        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = filename

        self.events = self.dataSource.getEvents()

    

    def _loadPSF(self, filename):
        """Load PYME .psf data.
        
        .psf files consist of a tuple containing the data and the voxelsize.
        """
        from PYME.IO import unifiedIO
        with unifiedIO.local_or_temp_filename(filename) as fn:
            self.data, vox = numpy.load(fn)
        self.mdh = MetaDataHandler.NestedClassMDHandler(MetaData.ConfocDefault)

        self.mdh.setEntry('voxelsize.x', vox.x)
        self.mdh.setEntry('voxelsize.y', vox.y)
        self.mdh.setEntry('voxelsize.z', vox.z)


        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'psf'
        
    def _loadNPY(self, filename):
        """Load numpy .npy data.
        
       
        """
        from PYME.IO import unifiedIO
        mdfn = self._findAndParseMetadata(filename)

        with unifiedIO.local_or_temp_filename(filename) as fn:
            self.data = numpy.load(fn)


        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'default'
        
    def _loadDBL(self, filename):
        """Load Bewersdorf custom STED data.
       
        """
        mdfn = self._findAndParseMetadata(filename)
        
        self.data = numpy.memmap(filename, dtype='<f4', mode='r', offset=128, shape=(self.mdh['Camera.ROIWidth'],self.mdh['Camera.ROIHeight'],self.mdh['NumImages']), order='F')


        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'default'
        

    def _findAndParseMetadata(self, filename):
        """Try and find and load a .xml or .md metadata file that might be ascociated
        with a given image filename. See the relevant metadatahandler classes
        for details."""
        import xml.parsers.expat
        from PYME.IO import unifiedIO
        
        if not self.mdh is None:
            return #we already have metadata (probably passed in on command line)
        
        mdf = None
        xmlfn = os.path.splitext(filename)[0] + '.xml'
        xmlfnmc = os.path.splitext(filename)[0].split('__')[0] + '.xml'
        if os.path.exists(xmlfn):
            try:
                self.mdh = MetaDataHandler.NestedClassMDHandler(MetaData.TIRFDefault)
                self.mdh.copyEntriesFrom(MetaDataHandler.XMLMDHandler(xmlfn))
                mdf = xmlfn
            except xml.parsers.expat.ExpatError:
                #fix for bug in which PYME .md was written with a .xml extension
                self.mdh = MetaDataHandler.NestedClassMDHandler(MetaData.BareBones)
                self.mdh.copyEntriesFrom(MetaDataHandler.SimpleMDHandler(xmlfn))
                mdf = xmlfn
                
        elif os.path.exists(xmlfnmc): #this is a single colour channel of a pair
            self.mdh = MetaDataHandler.NestedClassMDHandler(MetaData.TIRFDefault)
            self.mdh.copyEntriesFrom(MetaDataHandler.XMLMDHandler(xmlfnmc))
            mdf = xmlfnmc
        else:
            self.mdh = MetaDataHandler.NestedClassMDHandler(MetaData.BareBones)
            
            #check for simple metadata (python code with an .md extension which 
            #fills a dictionary called md)
            mdfn = os.path.splitext(filename)[0] + '.md'
            jsonfn = os.path.splitext(filename)[0] + '.json'
            if os.path.exists(mdfn):
                self.mdh.copyEntriesFrom(MetaDataHandler.SimpleMDHandler(mdfn))
                mdf = mdfn
            elif os.path.exists(jsonfn):
                import json
                with open(jsonfn, 'r') as f: 
                    mdd = json.load(f)
                    self.mdh.update(mdd)
            elif filename.endswith('.lsm'):
                #read lsm metadata
                from PYME.contrib.gohlke.tifffile import TIFFfile
                tf = TIFFfile(filename)
                lsm_info = tf[0].cz_lsm_scan_information
                self.mdh['voxelsize.x'] = lsm_info['line_spacing']
                self.mdh['voxelsize.y'] = lsm_info['line_spacing']
                self.mdh['voxelsize.z'] = lsm_info['plane_spacing']
                
                def lsm_pop(basename, dic):
                    for k, v in dic.items():
                        if isinstance(v, list):
                            #print k, v
                            for i, l_i in enumerate(v):
                                #print i, l_i, basename
                                lsm_pop(basename + k + '.' + k[:-1] + '%i.' %i, l_i)
                                
                        else:
                            self.mdh[basename + k] = v
                
                lsm_pop('LSM.', lsm_info)
                
            elif filename.endswith('.tif'):
                #look for OME data...
                from PYME.contrib.gohlke.tifffile import TIFFfile
                tf = TIFFfile(filename)
                
                if tf.is_ome:
                    try:
                        omemdh = MetaDataHandler.OMEXMLMDHandler(tf.pages[0].tags['image_description'].value)
                        
                        self.mdh.copyEntriesFrom(omemdh)
                    except IndexError:
                        pass

            elif filename.endswith('.dcimg'): #Bewersdorf lab Biplane
                # FIXME load seriesXX.json for seriesXX_chunkXX.dcimg files more elegantly
                jsonfn = filename[:-22] + '.json'

                import json
                try:
                    mdd = json.loads(unifiedIO.read(jsonfn))
                    self.mdh.update(mdd)

                except IOError:
                    pass

            elif filename.endswith('.dbl'): #Bewersdorf lab STED
                mdfn = filename[:-4] + '.txt'
                entrydict = {}
                
                try: #try to read in extra metadata if possible
                    with unifiedIO.openFile(mdfn, 'r') as mf:
                        for line in mf:
                            s = line.split(':')
                            if len(s) == 2:
                                entrydict[s[0]] = s[1]
                            
                except IOError:
                    pass
                            
#                vx, vy = entrydict['Pixel size (um)'].split('x')
#                self.mdh['voxelsize.x'] = float(vx)
#                self.mdh['voxelsize.y'] = float(vy)
#                self.mdh['voxelsize.z'] = 0.2 #FIXME for stacks ...
#                
#                sx, sy = entrydict['Image format'].split('x')
#                self.mdh['Camera.ROIWidth'] = int(sx)
#                self.mdh['Camera.ROIHeight'] = int(sy)
#                
#                self.mdh['NumImages'] = int(entrydict['# Images'])
                
                with unifiedIO.openFile(filename) as df:
                    s = df.read(8)
                    Z, X, Y, T = numpy.fromstring(s, '>u2')
                    s = df.read(16)
                    depth, width, height, elapsed = numpy.fromstring(s, '<f4')
                    
                    self.mdh['voxelsize.x'] = width/X
                    self.mdh['voxelsize.y'] = height/Y
                    self.mdh['voxelsize.z'] = depth
                    
                    self.mdh['Camera.ROIWidth'] = X
                    self.mdh['Camera.ROIHeight'] = Y
                    self.mdh['NumImages'] = Z*T
                
                def _sanitise_key(key):
                    k = key.replace('#', 'Num')
                    k = k.replace('(%)', '')
                    k = k.replace('(', '')
                    k = k.replace(')', '')
                    k = k.replace('.', '')
                    k = k.replace('/', '')
                    k = k.replace('?', '')
                    k = k.replace(' ', '')
                    if not k[0].isalpha():
                        k = 's' + k
                    return k
                    
                for k, v in entrydict.items():
                    self.mdh['STED.%s'%_sanitise_key(k)] = v
                    
            #else: #try bioformats
            #    OMEXML = bioformats.get_omexml_metadata(filename).encode('utf8')
            #    OMEmd = MetaDataHandler.OMEXMLMDHandler(OMEXML)
            #    self.mdh.copyEntriesFrom(OMEmd)
                    
                    
                    
                    
                
                

        if self.haveGUI and not ('voxelsize.x' in self.mdh.keys() and 'voxelsize.y' in self.mdh.keys()):
            from PYME.DSView.voxSizeDialog import VoxSizeDialog

            dlg = VoxSizeDialog(None)
            dlg.ShowModal()

            self.mdh.setEntry('voxelsize.x', dlg.GetVoxX())
            self.mdh.setEntry('voxelsize.y', dlg.GetVoxY())
            self.mdh.setEntry('voxelsize.z', dlg.GetVoxZ())

        return mdf

    def _loadTiff(self, filename):
        #from PYME.IO.FileUtils import readTiff
        from PYME.IO.DataSources import TiffDataSource

        mdfn = self._findAndParseMetadata(filename)

        self.dataSource = TiffDataSource.DataSource(filename, None)
        print(self.dataSource.shape)
        self.dataSource = BufferedDataSource.DataSource(self.dataSource, min(self.dataSource.getNumSlices(), 50))
        self.data = self.dataSource #this will get replaced with a wrapped version

        print(self.data.shape)


        #if we have a multi channel data set, try and pull in all the channels
        if 'ChannelFiles' in self.mdh.getEntryNames() and not len(self.mdh['ChannelFiles']) == self.data.shape[3]:
            try:
                from PYME.IO.dataWrap import ListWrap
                #pull in all channels

                chans = []

                for cf in self.mdh.getEntry('ChannelFiles'):
                    cfn = os.path.join(os.path.split(filename)[0], cf)

                    ds = TiffDataSource.DataSource(cfn, None)
                    ds = BufferedDataSource.DataSource(ds, min(ds.getNumSlices(), 50))

                    chans.append(ds)

                self.data = ListWrap(chans) #this will get replaced with a wrapped version

                self.filename = mdfn
            except:
                pass
            
        elif 'ChannelNames' in self.mdh.getEntryNames() and len(self.mdh['ChannelNames']) == self.data.getNumSlices():
            from PYME.IO.dataWrap import ListWrap
            chans = [numpy.atleast_3d(self.data.getSlice(i)) for i in range(len(self.mdh['ChannelNames']))]
            self.data = ListWrap(chans)
        elif filename.endswith('.lsm') and 'LSM.images_number_channels' in self.mdh.keys() and self.mdh['LSM.images_number_channels'] > 1:
            from PYME.IO.dataWrap import ListWrap
            nChans = self.mdh['LSM.images_number_channels']
            
            chans = []
            
            for n in range(nChans):
                ds = TiffDataSource.DataSource(filename, None, n)
                ds = BufferedDataSource.DataSource(ds, min(ds.getNumSlices(), 50))

                chans.append(ds)

            self.data = ListWrap(chans)


        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'default'
        
    def _loadBioformats(self, filename):
        #from PYME.IO.FileUtils import readTiff
        from PYME.IO.DataSources import BioformatsDataSource
        import bioformats

        #mdfn = self.FindAndParseMetadata(filename)
        print("Bioformats:loading data")
        self.dataSource = BioformatsDataSource.DataSource(filename, None)
        self.mdh = MetaDataHandler.NestedClassMDHandler(MetaData.BareBones)
        
        print("Bioformats:loading metadata")
        OMEXML = bioformats.get_omexml_metadata(filename).encode('utf8')
        print("Bioformats:parsing metadata")
        OMEmd = MetaDataHandler.OMEXMLMDHandler(OMEXML)
        self.mdh.copyEntriesFrom(OMEmd)
        print("Bioformats:done")
                
        
        print(self.dataSource.shape)
        self.dataSource = BufferedDataSource.DataSource(self.dataSource, min(self.dataSource.getNumSlices(), 50))
        self.data = self.dataSource #this will get replaced with a wrapped version
        
        print(self.data.shape)

        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'default'

    def _loadDCIMG(self, filename):
        from PYME.IO.DataSources import DcimgDataSource, MultiviewDataSource

        self._findAndParseMetadata(filename)

        self.dataSource = DcimgDataSource.DataSource(filename)

        if 'Multiview.NumROIs' in self.mdh.keys():
            self.dataSource = MultiviewDataSource.DataSource(self.dataSource, self.mdh)
        
        self.data = self.dataSource #this will get replaced with a wrapped version

        self.seriesName = getRelFilename(filename)

        self.mode = 'default'
        
        
    def _loadImageSeries(self, filename):
        #from PYME.IO.FileUtils import readTiff
        from PYME.IO.DataSources import ImageSeriesDataSource

        self.dataSource = ImageSeriesDataSource.DataSource(filename, None)
        self.dataSource = BufferedDataSource.DataSource(self.dataSource, min(self.dataSource.getNumSlices(), 50))
        self.data = self.dataSource #this will get replaced with a wrapped version
        #self.data = readTiff.read3DTiff(filename)

        self._findAndParseMetadata(filename)

        #from PYME.ParallelTasks.relativeFiles import getRelFilename
        self.seriesName = getRelFilename(filename)

        self.mode = 'default'

    def Load(self, filename=None):
        """
        Load a file from disk / queue / cluster

        NB: this is usually called from __init__. Call ImageStack(filename = filename) rather than calling this function directly.

        Parameters
        ----------
        filename : str [optional]
            filename or URI of data to load. Natively supported types are:
                - .tif
                - .h5 (PYME HDF5 format)
                - .npy (numpy array)
                - .psf (PYME PSF files)
                - .dbl (Bewersdorf STED files)
                - .dcimg (Hamamatsu .dcimg)
                - QUEUE:// (PYME task queue data)
                - PYME-CLUSTER:// (Data stored in our custom cluster file system)
                - .md (sequence of images with a type supported by PIL, described by a .md metadta file)

            If the filename doesn't match one of these patterns, we fall back on bioformats, if available. This works
            well for most biological file formats, but can be fairly slow. At present, .tif is handled by our native
            handler (which falls back on the excellent Gohlke tiffile library) and .tiff is handled by bioformats.

            If no filename is given, we display an open file dialog box.

        Returns
        -------

        """
        print('filename == %s' % filename)
        if (filename is None or filename == ''):
            import wx #only introduce wx dependency here - so can be used non-interactively
            global lastdir
            
            #fdialog = wx.FileDialog(None, 'Please select Data Stack to open ...',
            #    wildcard='Image Data|*.h5;*.tif;*.lsm;*.kdf;*.md;*.psf;*.npy;*.dbl|All files|*.*', style=wx.OPEN, defaultDir = lastdir)
            #succ = fdialog.ShowModal()
            #if (succ == wx.ID_OK):
            #    filename = fdialog.GetPath()
            #    lastdir = fdialog.GetDirectory()
            #else:
                #print succ

            filename = wx.FileSelector('Please select Data Stack to open ...',
                                       wildcard='Image Data|*.h5;*.tif;*.lsm;*.kdf;*.md;*.psf;*.npy;*.dbl|All files|*.*', 
                                        default_path = lastdir)            
            
            if filename is None or filename == '':
                raise RuntimeError('No file selected')
                pass
            else:
                lastdir = os.path.split(filename)[0]
            #print(succ, filename)

        if not filename is None:
            if filename.startswith('QUEUE://'):
                self._loadQueue(filename)
            elif filename.startswith('http://'):
                self._loadHTTP(filename)
            elif filename.startswith('PYME-CLUSTER://') or filename.startswith('pyme-cluster://'):
                self._loadClusterPZF(filename)
            elif filename.endswith('.h5'):
                self._loadh5(filename)
            #elif filename.endswith('.kdf'):
            #    self.LoadKdf(filename)
            elif filename.endswith('.psf'): #psf
                self._loadPSF(filename)
            elif filename.endswith('.md'): #treat this as being an image series
                self._loadImageSeries(filename)
            elif filename.endswith('.npy'): #treat this as being an image series
                self._loadNPY(filename)
            elif filename.endswith('.dbl'): #treat this as being an image series
                self._loadDBL(filename)
            elif os.path.splitext(filename)[1] in ['.tif', '.tif', '.lsm']: #try tiff
                self._loadTiff(filename)
            elif filename.endswith('.dcimg'):
                self._loadDCIMG(filename)
            else: #try bioformats
                self._loadBioformats(filename)


            #self.SetTitle(filename)
            self.filename = filename
            self.saved = True

    def Save(self, filename=None, crop=False, view=None, progressCallback=None):
        """
        Saves an image to file.

        Parameters
        ----------
        filename : str
            The filename to save to. File type is deduced by the extension. For supported data types, see PYME.IO.dataExporter.
            If no filename is given, we display a dialog box to ask.

        crop : bool
            Do we want to crop the image? Note that this displays a cropping dialog box (ie needs a GUI) and requires
            that view be defined. TODO - remove GUI dependance

        view : PYME.DSView.arrayViewPanel instance
            Our current view of the data. Used to get selection information to provide starting values for our crop region
            TODO - make this GUI independant by passing the selection / crop region to save.

        Returns
        -------

        """
        from PYME.IO import dataExporter

        ofn = self.filename

        if crop:
            dataExporter.CropExportData(view, self.mdh, self.events, self.seriesName)
        else:
            if 'defaultExt' in dir(self):
                self.filename = dataExporter.ExportData(self.data, self.mdh, self.events, defaultExt=self.defaultExt, filename=filename, progressCallback=progressCallback)
            else:
                self.filename = dataExporter.ExportData(self.data, self.mdh, self.events, filename=filename, progressCallback=progressCallback)
            #self.SetTitle(fn)

            if not (self.filename is None):
                self.saved = True

                openImages.pop(ofn)
                openImages[self.filename] = self

            else:
                self.filename = ofn


def GeneratedImage(img, imgBounds, pixelSize, sliceSize, channelNames, mdh=None):
    """Helper function for LMVis which creates an image and fills in a few
    metadata parameters"""
    image = ImageStack(img, mdh=mdh)
    image.pixelSize = pixelSize
    image.sliceSize = sliceSize
    image.imgBounds = imgBounds
    image.names = [c if c else 'Image' for c in channelNames]

    return image



