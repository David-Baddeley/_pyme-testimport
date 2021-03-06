#!/usr/bin/python

##################
# MetaDataHandler.py
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

#!/usr/bin/python
"""
Defines metadata handlers for the saving of acquisiton metadata to a variety 
of file formats, as well as keeping track of metadata sources. 

Metadata sources
----------------

Metadata sources are simply functions, which when called, write information into
a provided handler. e.g.::
    def metadataGenerator(mdhandler):
        mdhandler['a.key'] = value

These generator functions are registered by adding them to one of two lists exposed 
by this module: **provideStartMetadata** or **provideStopMetadata**. depending on
whether it makes more sense to record the metadata at the start or stop of an 
acquisition.

A good example can be found in PYME.Acquire.Hardware.Camera.AndorIXon.AndorIXon.

MetaData Handlers
-----------------

**NestedClassMDHandler**
    An in-memory metadatahandler used to buffer metadata or to store values prior
    to the file format being known.
**HDFMDHandler**
    For local pytables/hdf5 datasets
**QueueMDHandler**
    For use with data hosted in a taskqueue
**XMLMDHandler**
    For use with PYMEs XML metadata format - typically used with .tiff files or
    other data for which it is difficult to embed metadata.
**SimpleMDHandler**
    Saves and reads metadata as a python script (a series of md[key]=value statements).
    Used where you might want to construct or modify metadata by hand - e.g. with
    foreign source data.
    

The format of a metadata handler is defined by the `MDHandlerBase` class. 


"""
try:
    # noinspection PyCompatibility
    from UserDict import DictMixin
except ImportError:
    #py3
    from collections import MutableMapping as DictMixin
    
import six

import logging
logger = logging.getLogger(__name__)

#lists where bits of hardware can register the fact that they are capable of 
#providing metadata, by appending a function with the signature:
#genMetadata(MetaDataHandler)
provideStartMetadata = []
provideStopMetadata = []

def instanceinlist(cls, list):
    for c in list:
        if isinstance(cls, c):
            return True

    return False
    

class MDHandlerBase(DictMixin):
    """Base class from which all metadata handlers are derived.

    Metadata attributes can be read and set using either a dictionary like
    interface, or by calling the `getEntry` and `setEntry` methods. 
    
    .. note:: Derived classes **MUST** override `getEntry`, `setEntry`, and `getEntryNames`.
    """
    #base class to make metadata behave like a dictionary
    def getEntry(self, name):
        """Returns the entry for a given name.
        
        Parameters
        ----------
        name : string
            The entry name. This name should be heirachical, and deliminated
            with dots e.g. 'Camera.EMCCDGain'
            
        Returns
        -------
        value : object
            The value stored for the given key. This can, in principle, be 
            anything that can be pickled. strings, ints, bools and floats are
            all stored in a human readable form in the textual metadata 
            representations, wheras more complex objects are base64 encoded.
        """
        raise NotImplementedError('getEntry must be overridden in derived classes')
        
    def setEntry(self, name):
        """Sets the entry for a given name.
        
        Parameters
        ----------
        name : string
            The entry name. This name should be heirachical, and deliminated
            with dots e.g. 'Camera.EMCCDGain'
            
        value : object
            The value stored for the given key. This can, in principle, be 
            anything that can be pickled. strings, ints, bools and floats are
            all stored in a human readable form in the textual metadata 
            representations, wheras more complex objects are base64 encoded.
        """
        raise NotImplementedError('setEntry must be overridden in derived classes')
        
    def getEntryNames(self):
        """Returns a list of defined entries.
            
        Returns
        -------
        names : list of string
            The keys which are defined in the metadata.
        """
        raise NotImplementedError('getEntryNames must be overridden in derived classes')
        
    def __setitem__(self, name, value):
        self.setEntry(name, value)

    def __getitem__(self, name):
        return self.getEntry(name)

    if six.PY3:
        def __len__(self):
            return len(self.getEntryNames())
    
        def __iter__(self):
            for k in self.getEntryNames():
                yield self.getEntry(k)
                
        def __delitem__(self, key):
            raise RuntimeError('Cannot delete metadata item')
        
    def getOrDefault(self, name, default):
        """Returns the entry for a given name, of a default value if the key
        is not present.
        
        Parameters
        ----------
        name : string
            The entry name. This name should be heirachical, and deliminated
            with dots e.g. 'Camera.EMCCDGain'
        default : object
            What to return if the name is not defined
            
        Returns
        -------
        value : object
            The value stored for the given key. This can, in principle, be 
            anything that can be pickled. strings, ints, bools and floats are
            all stored in a human readable form in the textual metadata 
            representations, wheras more complex objects are base64 encoded.
        """
        try: 
            return self.getEntry(name)
        except (KeyError, AttributeError):
            return default

    def keys(self):
        """Alias for getEntryNames to make us look like a dictionary"""
        return self.getEntryNames()

    def copyEntriesFrom(self, mdToCopy):
        """Copies entries from another metadata object into this one. Duplicate
        keys will be overwritten.
        
        Parameters
        ----------
        mdToCopy : an instance of a metadata handler
            The metadata handler from which to copy entries.
        """
        for en in mdToCopy.getEntryNames():
            #print en
            self.setEntry(en, mdToCopy.getEntry(en))
        #self.update(mdToCopy)

    def mergeEntriesFrom(self, mdToCopy):
        """Copies entries from another metadata object into this one. Values
        are only copied if they are not already defined locally.
        
        Parameters
        ----------
        mdToCopy : an instance of a metadata handler
            The metadata handler from which to copy entries.
        """
        #only copies values if not already defined
        for en in mdToCopy.getEntryNames():
            if not en in self.getEntryNames():
                self.setEntry(en, mdToCopy.getEntry(en))

    def __repr__(self):
        s = ['%s: %s' % (en, self.getEntry(en)) for en in self.getEntryNames()]
        return '<%s>:\n\n' % self.__class__.__name__ + '\n'.join(s)

    def GetSimpleString(self):
        """Writes out metadata in simplfied format.
        
        Returns
        -------
            mdstring : string
                The metadata in a simple, human readable format.
                
        See Also
        --------
        SimpleMDHandler
        """
        
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
            
        import numpy as np
        s = ['#PYME Simple Metadata v1\n']

        for en in self.getEntryNames():
            val = self.getEntry(en)

            if val.__class__ in [str, unicode] or np.isscalar(val): #quote string
                val = repr(val)
            elif not val.__class__ in [int, float, list, dict, tuple]: #not easily recovered from representation
                val = "pickle.loads('''%s''')" % pickle.dumps(val).replace('\n', '\\n')

            s.append("md['%s'] = %s\n" % (en, val))
        
        return s
    
    def WriteSimple(self, filename):
        """Dumps metadata to file in simplfied format.
        
        Parameters
        ----------
            filename : string
                The the filename to write to. Should end in .md.
                
        See Also
        --------
        SimpleMDHandler
        """
        s = self.GetSimpleString()
        f = open(filename, 'w')
        f.writelines(s)
        f.close()
        
    def to_JSON(self):
        import json
        import numpy as np
        
        def _jsify(obj):
            """call a custom to_JSON method, if available"""
            #if isinstance(obj, np.integer):
            #    return int(obj)
            #elif isinstance(obj, np.number):
            #    return float(obj)
            if isinstance(obj, np.generic):
                return obj.tolist()

            try:
                return obj.to_JSON()
            except AttributeError:
                return obj
                
        d = { k: _jsify(self.getEntry(k)) for k in self.getEntryNames()}
        
        return json.dumps(d, indent=0, sort_keys=True)

class HDFMDHandler(MDHandlerBase):
    def __init__(self, h5file, mdToCopy=None):
        self.h5file = h5file
        self.md = None

        if self.h5file.__contains__('/MetaData'):
            self.md = self.h5file.root.MetaData
        else:
            self.md = self.h5file.create_group(self.h5file.root, 'MetaData')

        if not mdToCopy is None:
            self.copyEntriesFrom(mdToCopy)


    def setEntry(self,entryName, value):
        entPath = entryName.split('.')
        en = entPath[-1]
        ep = entPath[:-1]

        currGroup = self.h5file._get_or_create_path('/'.join(['', 'MetaData']+ ep), True)
        currGroup._f_setattr(en, value)
        self.h5file.flush()


    def getEntry(self,entryName):
        entPath = entryName.split('.')
        en = entPath[-1]
        ep = entPath[:-1]

        res =  self.h5file.get_node_attr('/'.join(['', 'MetaData']+ ep), en)
        
        #dodgy hack to get around a problem with zero length strings not
        #being picklable if they are numpy (rather than pure python) types
        #this code should convert a numpy empty string into a python empty string
        if res == '':
            return ''
        
        return res
        


    def getEntryNames(self):
        entryNames = []
        for a in [self.md] + list(self.md._f_walknodes()):
            entryNames.extend(['.'.join(a._v_pathname.split('/')[2:] +[ i]) for i in a._v_attrs._f_list()])

        return entryNames

class QueueMDHandler(MDHandlerBase):
    def __init__(self, tq, queueName, mdToCopy=None):
        self.tq = tq
        self.queueName = queueName
        self.md = None

        if not mdToCopy is None:
            self.copyEntriesFrom(mdToCopy)
            
    def copyEntriesFrom(self, mdToCopy):
        self.tq.setQueueMetaDataEntries(self.queueName, mdToCopy)

    def setEntry(self,entryName, value):
        self.tq.setQueueMetaData(self.queueName, entryName, value)


    def getEntry(self,entryName):
        #print entryName
        return self.tq.getQueueMetaData(self.queueName, entryName)


    def getEntryNames(self):
        return self.tq.getQueueMetaDataKeys(self.queueName)
        


class NestedClassMDHandler(MDHandlerBase):
    def __init__(self, mdToCopy=None):
        if not mdToCopy is None:
            self.copyEntriesFrom(mdToCopy)


    def setEntry(self,entryName, value):
        entPath = entryName.split('.')
        if len(entPath) == 1: #direct child of this node
            self.__dict__[entPath[0]] = value
        else:
            if not entPath[0] in dir(self):
                self.__dict__[entPath[0]] = NestedClassMDHandler()
            self.__dict__[entPath[0]].setEntry('.'.join(entPath[1:]), value)

    
    def getEntry(self,entryName):
        #print(entryName)
        return eval('self.'+entryName)
#        try:
#            return eval('self.'+entryName)
#        except AttributeError:
#            raise KeyError('No entry found for %s' % entryName)


    def getEntryNames(self):
        en = []
        for k in self.__dict__.keys():
            if hasattr(self.__dict__[k], 'getEntryNames') and not self.__dict__[k].__module__ == 'Pyro.core':
                en += [k + '.' + kp for kp in self.__dict__[k].getEntryNames()]
            else:
                en.append(k)

        return en
        
        
class CachingMDHandler(MDHandlerBase):
    def __init__(self, mdToCache):
        self.mdToCache = mdToCache
        
        if not mdToCache is None:
            self.cache = dict(mdToCache.items())
            
    @classmethod
    def recreate(cls, cache):
        c = cls(None)
        c.cache = cache
        
    def __reduce__(self):
        return (CachingMDHandler.recreate, (self.cache,))
        
    def getEntry(self, entryName):
        return self.cache[entryName]
        
    def setEntry(self, entryName, value):
        self.cache[entryName] = value
        if not self.mdToCache is None:
            self.mdToCache.setEntry(entryName, value)
        
    def getEntryNames(self):
        return self.cache.keys()
    

from xml.dom.minidom import getDOMImplementation, parse, parseString
#from xml.sax.saxutils import escape, unescape
import base64

class SimpleMDHandler(NestedClassMDHandler):
    """simple metadata format - consists of a python script with a .md extension
    which adds entrys using the dictionary syntax to a metadata handler called md"""

    def __init__(self, filename = None, mdToCopy=None):
        if not filename is None:
            from PYME.Acquire.ExecTools import _execfile
            import cPickle as pickle
            #loading an existing file
            md = self
            fn = __file__
            globals()['__file__'] = filename
            _execfile(filename, locals(), globals())
            globals()['__file__'] = fn

        if not mdToCopy is None:
            self.copyEntriesFrom(mdToCopy)

    def write(self, filename):
        s = ''
        for en in self.getEntryNames():
            s += "md['%s'] = %s\n" % (en, self.getEntry(en))

        fid = open(filename, 'w')
        fid.write(s)
        fid.close()

    

class XMLMDHandler(MDHandlerBase):
    def __init__(self, filename = None, mdToCopy=None):
        if not filename is None:
            #loading an existing file
            self.doc = parse(filename)
            self.md = self.doc.documentElement.getElementsByTagName('MetaData')[0]
        else:
            #creating a new document
            self.doc = getDOMImplementation().createDocument(None, 'PYMEImageData', None)
            self.md = self.doc.createElement('MetaData')
            self.doc.documentElement.appendChild(self.md)

        if not mdToCopy is None:
            self.copyEntriesFrom(mdToCopy)

    def writeXML(self, filename):
        f = open(filename, 'w')
        f.write(self.doc.toprettyxml())
        f.close()


    def setEntry(self,entryName, value):
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
        
        import numpy as np
        entPath = entryName.split('.')

        node = self.md
        while len(entPath) >= 1:
            el = [e for e in node.childNodes if e.tagName == entPath[0]]
            if len(el) == 0:
                #need to create node
                newNode = self.doc.createElement(entPath[0])
                node.appendChild(newNode)
                node = newNode
            else:
                node = el[0]

            entPath.pop(0)

        #typ = type(value) #.__name__
        
        if isinstance(value, float):
            node.setAttribute('class', 'float')
            node.setAttribute('value', str(value))
        elif isinstance(value, int):
            node.setAttribute('class', 'int')
            node.setAttribute('value', str(value))
        elif isinstance(value, str):
            node.setAttribute('class', 'str')
            node.setAttribute('value', value)
        elif isinstance(value, unicode):
            node.setAttribute('class', 'unicode')
            node.setAttribute('value', value)
        elif np.isscalar(value):
            node.setAttribute('class', 'float')
            node.setAttribute('value', str(value)) 
        else: #pickle more complicated structures
            node.setAttribute('class', 'pickle')
            print((value, pickle.dumps(value)))
            node.setAttribute('value', base64.b64encode((pickle.dumps(value))))


    def getEntry(self,entryName):
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
            
        entPath = entryName.split('.')

        node = self.md
        while len(entPath) >= 1:
            el = [e for e in node.childNodes if e.nodeName == entPath[0]]
            if len(el) == 0:
                #node not there
                raise RuntimeError('Requested node not found')
            else:
                node = el[0]

            entPath.pop(0)

        cls = node.getAttribute('class')
        val = node.getAttribute('value')
        
        if val == 'True': #booleans get cls 'int'
                val = True
        elif val == 'False':
                val = False
        elif cls == 'int':
                val = int(val)
        elif cls == 'float':
            val = float(val)
        elif cls == 'pickle':
            #return None
            try:
                val = pickle.loads(base64.b64decode(val))
            except:
                logger.exception('Error loading metadata from pickle')

        return val


    def getEntryNames(self):
        elements = self.md.getElementsByTagName('*')

        en = []

        for e in elements:
            if not e.hasChildNodes(): #we are at the end of the tree
                n = e.nodeName #starting name
                while not e.parentNode == self.md:
                    e = e.parentNode
                    n = '.'.join((e.nodeName, n))

                en.append(n)        

        return en


class OMEXMLMDHandler(XMLMDHandler):
    def __init__(self, XMLData = None, mdToCopy=None):
        if not XMLData is None:
            #loading an existing file
            self.doc = parseString(XMLData)
            #try:
            try:
                self.md = self.doc.documentElement.getElementsByTagName('MetaData')[0]
            except IndexError:
                self.md = self.doc.createElement('MetaData')
                self.doc.documentElement.appendChild(self.md)
                
                #try to load pixel size etc fro OME metadata
                pix = self.doc.getElementsByTagName('Pixels')[0]
                
                #print 'PhysicalSizeX: ', pix.getAttribute('PhysicalSizeX')
                try:
                    self['voxelsize.x'] = float(pix.getAttribute('PhysicalSizeX'))
                    self['voxelsize.y'] = float(pix.getAttribute('PhysicalSizeY'))
                except:
                    print('WARNING: Malformed OME XML. Pixel size not defined, using 100nm')

                    self['voxelsize.x'] = .1 #FIXME - Get user to set pixel size if absent
                    self['voxelsize.x'] = .1
                try:
                    self['voxelsize.z'] = float(pix.getAttribute('PhysicalSizeZ'))
                except:
                    self['voxelsize.z'] = 0.2
                    
                try:
                    self['Camera.CycleTime'] = float(pix.getAttribute('TimeIncrement'))
                except:
                    pass
                
                self['OME.SizeX'] = int(pix.getAttribute('SizeX'))
                self['OME.SizeY'] = int(pix.getAttribute('SizeY'))
                self['OME.SizeZ'] = int(pix.getAttribute('SizeZ'))
                self['OME.SizeT'] = int(pix.getAttribute('SizeT'))
                self['OME.SizeC'] = int(pix.getAttribute('SizeC'))
                
                self['OME.DimensionOrder'] = pix.getAttribute('DimensionOrder')
                    
                #except:
                #    pass
            
            
                
            
        else:
            #creating a new document
            self.doc = getDOMImplementation().createDocument(None, 'OME', None)
            self.doc.documentElement.setAttribute('xmlns', "http://www.openmicroscopy.org/Schemas/OME/2015-01")
            #self.doc.documentElement.setAttribute('xmlns:ROI', "http://www.openmicroscopy.org/Schemas/ROI/2015-01")
            #self.doc.documentElement.setAttribute('xmlns:BIN', "http://www.openmicroscopy.org/Schemas/BinaryFile/2015-01")
            self.doc.documentElement.setAttribute('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
            self.doc.documentElement.setAttribute('xsi:schemaLocation','http://www.openmicroscopy.org/Schemas/OME/2015-01 http://www.openmicroscopy.org/Schemas/OME/2015-01/ome.xsd')
            
            
            self.img = self.doc.createElement('Image')
            self.img.setAttribute('ID', 'Image:0')
            self.img.setAttribute('Name', 'Image:0')
            self.doc.documentElement.appendChild(self.img)
            
            self.pixels = self.doc.createElement('Pixels')
            self.img.appendChild(self.pixels)
            self.pixels.setAttribute('ID', 'Pixels:0')
            self.pixels.setAttribute('DimensionOrder', 'XYCZT')
            
            tf = self.doc.createElement('TiffData')
            self.pixels.appendChild(tf)
            
            sa = self.doc.createElement('StructuredAnnotations')
            self.doc.documentElement.appendChild(sa)
            
            xa = self.doc.createElement('XMLAnnotation')
            sa.appendChild(xa)
            xa.setAttribute('ID', 'PYME')
            #self.doc = getDOMImplementation().createDocument(None, 'PYMEImageData', None)
            v = self.doc.createElement('Value')
            xa.appendChild(v)
            
            self.md = self.doc.createElement('MetaData')
            v.appendChild(self.md)

        if not mdToCopy is None:
            self.copyEntriesFrom(mdToCopy)
            
    def getXML(self, data = None):
        #sync the OME data from the ordinary metadata
        if not data is None:
            ims = data.shape
            if len(ims) > 3:
                SizeY, SizeX, SizeT, SizeC = ims
                SizeZ = 1
            else:
                SizeY, SizeX, SizeT = ims
                SizeZ = 1
                SizeC = 1
                
            
            if str(data[0,0,0,0,0].dtype) in ('float32', 'float64'):
                self.pixels.setAttribute('Type', 'float')
            else:
                self.pixels.setAttribute('Type', str(data[0,0,0,0,0].dtype))
            self.pixels.setAttribute('SizeX', str(SizeX))
            self.pixels.setAttribute('SizeY', str(SizeY))
            self.pixels.setAttribute('SizeZ', str(SizeZ))
            self.pixels.setAttribute('SizeT', str(SizeT))
            self.pixels.setAttribute('SizeC', str(SizeC))
            
            self.pixels.setAttribute('PhysicalSizeX', '%3.4f' % self.getEntry('voxelsize.x'))
            self.pixels.setAttribute('PhysicalSizeY', '%3.4f' % self.getEntry('voxelsize.y'))
    
        return self.doc.toprettyxml()
    
    def writeXML(self, filename):
        f = open(filename, 'w')
        f.write(self.getXML())
        f.close()

#    def copyEntriesFrom(self, mdToCopy):
#        for en in mdToCopy.getEntryNames():
#            self.setEntry(en, mdToCopy.getEntry(en))

#    def mergeEntriesFrom(self, mdToCopy):
#        #only copies values if not already defined
#        for en in mdToCopy.getEntryNames():
#            if not en in self.getEntryNames():
#                self.setEntry(en, mdToCopy.getEntry(en))
#
#    def __repr__(self):
#        s = ['%s: %s' % (en, self.getEntry(en)) for en in self.getEntryNames()]
#        return '<%s>:\n\n' % self.__class__.__name__ + '\n'.join(s)
