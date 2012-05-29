from PYME.Analysis.LMVis import inpFilt
from PYME.Analysis.LMVis.visHelpers import ImageBounds
from PYME.Analysis.LMVis import dyeRatios
from PYME.Analysis.LMVis import statusLog
from PYME.Analysis.LMVis import renderers

from PYME.Analysis import piecewiseMapping
from PYME.Acquire import MetaDataHandler

import numpy as np
import scipy.special
import os
#from PYME.Analysis.BleachProfile.kinModels import getPhotonNums


class Pipeline:
    def __init__(self, filename=None, visFr=None):
        self.dataSources = []
        self.selectedDataSource = None
        self.filterKeys = {'error_x': (0,30), 'A':(5,2000), 'sig' : (95, 200)}

        self.filter = None
        self.mapping = None
        self.colourFilter = None
        self.events = None

        self.fluorSpecies = {}
        self.fluorSpeciesDyes = {}
        self.chromaticShifts = {}
        self.t_p_dye = 0.1
        self.t_p_other = 0.1
        self.t_p_background = .01

        self.objThreshold = 30
        self.objMinSize = 10
        self.blobJitter = 0
        self.objects = None

        self.imageBounds = ImageBounds(0,0,0,0)
        
        self.Triangles = None
        self.edb = None
        self.Quads = None
        self.GeneratedMeasures = {}
        
        self.QTGoalPixelSize = 5
        
        self.filesToClose = []
        
        self.ready = False
        self.visFr = visFr

        if not filename==None:
            self.OpenFile(filename)
            
        #renderers.renderMetadataProviders.append(self.SaveMetadata)
            
    def __getitem__(self, key):
        '''gets values from the 'tail' of the pipeline (ie the colourFilter)'''
        
        return self.colourFilter[key]

    def keys(self):
        return self.colourFilter.keys()


    def Rebuild(self):
        if not self.selectedDataSource == None:
            self.filter = inpFilt.resultsFilter(self.selectedDataSource, **self.filterKeys)
            if self.mapping:
                self.mapping.resultsSource = self.filter
            else:
                self.mapping = inpFilt.mappingFilter(self.filter)

            if not self.colourFilter:
                self.colourFilter = inpFilt.colourFilter(self.mapping, self)
                
            self.ready = True

        self.edb = None
        self.objects = None
        
        self.Triangles = None
        self.Quads = None

        self.GeneratedMeasures = {}
        
    def ClearGenerated(self):
        self.Triangles = None
        self.edb = None
        self.GeneratedMeasures = {}
        self.Quads = None

        if self.visFr:
            self.visFr.RefreshView()
        
        
    def _processEvents(self):
        '''Read data from events table and translate it into variables for, 
        e.g. z position'''
        
        if not self.events == None:
            evKeyNames = set()
            for e in self.events:
                evKeyNames.add(e['EventName'])
        
            if 'ProtocolFocus' in evKeyNames:
                self.zm = piecewiseMapping.GeneratePMFromEventList(self.events, self.mdh, self.mdh.getEntry('StartTime'), self.mdh.getEntry('Protocol.PiezoStartPos'))
                self.z_focus = 1.e3*self.zm(self.selectedDataSource['t'])
        
                self.selectedDataSource.z_focus = self.z_focus
                self.selectedDataSource.setMapping('focus', 'z_focus')
        
            if 'ScannerXPos' in evKeyNames:
                x0 = 0
                if 'Positioning.Stage_X' in self.mdh.getEntryNames():
                    x0 = self.mdh.getEntry('Positioning.Stage_X')
                self.xm = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), x0, 'ScannerXPos', 0)
        
                self.selectedDataSource.scan_x = 1.e3*self.xm(self.selectedDataSource['t']-.01)
                self.selectedDataSource.setMapping('ScannerX', 'scan_x')
                self.selectedDataSource.setMapping('x', 'x + scan_x')
        
            if 'ScannerYPos' in evKeyNames:
                y0 = 0
                if 'Positioning.Stage_Y' in self.mdh.getEntryNames():
                    y0 = self.mdh.getEntry('Positioning.Stage_Y')
                self.ym = piecewiseMapping.GeneratePMFromEventList(self.elv.eventSource, self.mdh, self.mdh.getEntry('StartTime'), y0, 'ScannerYPos', 0)
        
                self.selectedDataSource.scan_y = 1.e3*self.ym(self.selectedDataSource['t']-.01)
                self.selectedDataSource.setMapping('ScannerY', 'scan_y')
                self.selectedDataSource.setMapping('y', 'y + scan_y')
        
            if 'ScannerXPos' in evKeyNames or 'ScannerYPos' in evKeyNames:
                self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)
                
    def _processSplitter(self):
        '''set mappings ascociated with the use of a splitter'''
        self.selectedDataSource.setMapping('A', 'fitResults_Ag + fitResults_Ar')
        self.selectedDataSource.setMapping('gFrac', 'fitResults_Ag/(fitResults_Ag + fitResults_Ar)')
        
        if 'fitError_Ag' in self.selectedDataSource.keys():    
            self.selectedDataSource.setMapping('error_gFrac', 'sqrt((fitError_Ag/fitResults_Ag)**2 + (fitError_Ag**2 + fitError_Ar**2)/(fitResults_Ag + fitResults_Ar)**2)*fitResults_Ag/(fitResults_Ag + fitResults_Ar)')
        else:
            self.selectedDataSource.setMapping('error_gFrac','0*x + 0.01')
            self.selectedDataSource.setMapping('fitError_Ag', '1*sqrt(fitResults_Ag/1)')
            self.selectedDataSource.setMapping('fitError_Ar', '1*sqrt(fitResults_Ar/1)')
            
        sg = self.selectedDataSource['fitError_Ag']
        sr = self.selectedDataSource['fitError_Ar']
        g = self.selectedDataSource['fitResults_Ag']
        r = self.selectedDataSource['fitResults_Ar']
        I = self.selectedDataSource['A']
        
        self.selectedDataSource.colNorm = np.sqrt(2*np.pi)*sg*sr/(2*np.sqrt(sg**2 + sr**2)*I)*(
            scipy.special.erf((sg**2*r + sr**2*(I-g))/(np.sqrt(2)*sg*sr*np.sqrt(sg**2+sr**2)))
            - scipy.special.erf((sg**2*(r-I) - sr**2*g)/(np.sqrt(2)*sg*sr*np.sqrt(sg**2+sr**2))))
        
        self.selectedDataSource.setMapping('ColourNorm', '1.0*colNorm')
        
    def CloseFiles(self):
        while len(self.filesToClose) > 0:
            self.filesToClose.pop().close()

    def OpenFile(self, filename, **kwargs):
        '''Open a file - accepts optional keyword arguments for use with files
        saved as .txt and .mat. These are:
            
            FieldNames: a list of names for the fields in the text file or
                        matlab variable.
            VarName:    the name of the variable in the .mat file which 
                        contains the data.
        '''
        
        #close any files we had open previously
        while len(self.filesToClose) > 0:
            self.filesToClose.pop().close()
        
        #clear our state
        self.dataSources = []
        if 'zm' in dir(self):
            del self.zm
        self.filter = None
        self.mapping = None
        self.colourFilter = None
        self.events = None
        self.mdh = MetaDataHandler.NestedClassMDHandler()
        
        self.filename = filename
        
        if os.path.splitext(filename)[1] == '.h5r':
            try:
                self.selectedDataSource = inpFilt.h5rSource(filename)
                self.dataSources.append(self.selectedDataSource)

                self.filesToClose.append(self.selectedDataSource.h5f)

                if 'DriftResults' in self.selectedDataSource.h5f.root:
                    self.dataSources.append(inpFilt.h5rDSource(self.selectedDataSource.h5f))

                    if len(self.selectedDataSource['x']) == 0:
                        self.selectedDataSource = self.dataSources[-1]

            except: #fallback to catch series that only have drift data
                self.selectedDataSource = inpFilt.h5rDSource(filename)
                self.dataSources.append(self.selectedDataSource)
                
                self.filesToClose.append(self.selectedDataSource.h5f)

            #catch really old files which don't have any metadata
            if 'MetaData' in self.selectedDataSource.h5f.root:
                self.mdh = MetaDataHandler.HDFMDHandler(self.selectedDataSource.h5f)

           
            if ('Events' in self.selectedDataSource.h5f.root) and ('StartTime' in self.mdh.keys()):
                self.events = self.selectedDataSource.h5f.root.Events[:]

                        
        elif os.path.splitext(filename)[1] == '.mat': #matlab file
            ds = inpFilt.matfileSource(filename, kwargs['FieldNames'], kwargs['VarName'])
            self.selectedDataSource = ds
            self.dataSources.append(ds)

        else: #assume it's a text file
            ds = inpFilt.textfileSource(filename, kwargs['FieldNames'])
            self.selectedDataSource = ds
            self.dataSources.append(ds)
            

        #Retrieve or estimate image bounds
        if 'Camera.ROIWidth' in self.mdh.getEntryNames():
            x0 = 0
            y0 = 0

            x1 = self.mdh.getEntry('Camera.ROIWidth')*1e3*self.mdh.getEntry('voxelsize.x')
            y1 = self.mdh.getEntry('Camera.ROIHeight')*1e3*self.mdh.getEntry('voxelsize.y')

            if 'Splitter' in self.mdh.getEntry('Analysis.FitModule'):
                y1 = y1/2

            self.imageBounds = ImageBounds(x0, y0, x1, y1)
        else:
            self.imageBounds = ImageBounds.estimateFromSource(self.selectedDataSource)        
            
            
        #wrap the data source with a mapping so we can fiddle with things
        #e.g. combining z position and focus            
        self.selectedDataSource = inpFilt.mappingFilter(self.selectedDataSource)
        self.dataSources.append(self.selectedDataSource)
            
        #extract information from any events
        self._processEvents()
            
        
        #handle special cases which get detected by looking for the presence or
        #absence of certain variables in the data.        
        if 'fitResults_Ag' in self.selectedDataSource.keys():
            #if we used the splitter set up a number of mappings e.g. total amplitude and ratio
            self._processSplitter()

        if 'fitResults_sigxl' in self.selectedDataSource.keys():
            #fast, quickpalm like astigmatic fitting 
            self.selectedDataSource.setMapping('sig', 'fitResults_sigxl + fitResults_sigyu')
            self.selectedDataSource.setMapping('sig_d', 'fitResults_sigxl - fitResults_sigyu')

            self.selectedDataSource.dsigd_dz = -30.
            self.selectedDataSource.setMapping('fitResults_z0', 'dsigd_dz*sig_d')
            
        if not 'y' in self.selectedDataSource.keys():
            self.selectedDataSource.setMapping('y', '10*t')
            
            
            
        #set up correction for foreshortening and z focus stepping
        if not 'foreShort' in dir(self.selectedDataSource):
            self.selectedDataSource.foreShort = 1.

        if not 'focus' in self.selectedDataSource.mappings.keys():
            self.selectedDataSource.focus= np.zeros(self.selectedDataSource['x'].shape)
            
        if 'fitResults_z0' in self.selectedDataSource.keys():
            self.selectedDataSource.setMapping('z', 'fitResults_z0 + foreShort*focus')
        else:
            self.selectedDataSource.setMapping('z', 'foreShort*focus')

        
        
        #remove any keys from the filter which are not present in the data
        for k in self.filterKeys.keys():
            if not k in self.selectedDataSource.keys():
                self.filterKeys.pop(k)

        
        self.Rebuild()


        if 'Sample.Labelling' in self.mdh.getEntryNames():
            self.SpecFromMetadata()


    def SpecFromMetadata(self):
        labels = self.mdh.getEntry('Sample.Labelling')

        for structure, dye in labels:
            ratio = dyeRatios.getRatio(dye, self.mdh)

            if not ratio == None:
                self.fluorSpecies[structure] = ratio
                self.fluorSpeciesDyes[structure] = dye
                self.mapping.setMapping('p_%s' % structure, '(1.0/(ColourNorm*2*numpy.pi*fitError_Ag*fitError_Ar))*exp(-(fitResults_Ag - %f*A)**2/(2*fitError_Ag**2) - (fitResults_Ar - %f*A)**2/(2*fitError_Ar**2))' % (ratio, 1-ratio))
                
    def getNeighbourDists(self, forceRetriang = False):
        from PYME.Analysis.LMVis import visHelpers
        
        if forceRetriang or not 'neighbourDistances' in self.GeneratedMeasures.keys():
            statNeigh = statusLog.StatusLogger("Calculating mean neighbour distances ...")
            self.GeneratedMeasures['neighbourDistances'] = np.array(visHelpers.calcNeighbourDists(self.getTriangles(forceRetriang)))
            
        return self.GeneratedMeasures['neighbourDistances']
        
    def getTriangles(self, recalc = False):
        from matplotlib import delaunay
        
        if self.Triangles == None or recalc:
            statTri = statusLog.StatusLogger("Generating Triangulation ...")
            self.Triangles = delaunay.Triangulation(self.colourFilter['x'] + .1*np.random.normal(size=len(self.colourFilter['x'])), self.colourFilter['y']+ .1*np.random.normal(size=len(self.colourFilter['x'])))
            
            #reset things which will have changed
            self.edb = None
            try:
                self.GeneratedMeasures.pop('neighbourDistances')
            except KeyError:
                pass
            
        return self.Triangles
        
    def getEdb(self):
        from PYME.Analysis.EdgeDB import edges
        if self.edb == None:
            self.edb = edges.EdgeDB(self.getTriangles())
            
    def getBlobs(self):
        from PYME.Analysis.EdgeDB import edges
        
        tri = self.getTriangles()        
        edb = self.getEdb()
        
        if self.blobJitter == 0:
            self.objIndices = edges.objectIndices(edb.segment(self.objThreshold), self.objMinSize)
            self.objects = [np.vstack((tri.x[oi], tri.y[oi])).T for oi in self.objIndices]
        else:
            from matplotlib import delaunay
            
            ndists = self.getNeighbourDists()
            
            x_ = np.hstack([self['x'] + 0.5*ndists*np.random.normal(size=ndists.size) for i in range(self.blobJitter)])
            y_ = np.hstack([self['y'] + 0.5*ndists*np.random.normal(size=ndists.size) for i in range(self.blobJitter)])

            T = delaunay.Triangulation(x_, y_)
            edb = edges.EdgeDB(T)
            
            objIndices = edges.objectIndices(edb.segment(self.objThreshold), self.objMinSize)
            self.objects = [np.vstack((T.x[oi], T.y[oi])).T for oi in objIndices]
            
        return self.objects, self.objThreshold
        
    def getQuads(self):
        from PYME.Analysis.QuadTree import pointQT
        
        di = max(self.imageBounds.x1 - self.imageBounds.x0, 
                 self.imageBounds.y1 - self.imageBounds.y0)

        np = di/self.QTGoalPixelSize

        di = self.QTGoalPixelSize*2**np.ceil(np.log2(np))

        
        self.Quads = pointQT.qtRoot(self.imageBounds.x0, self.imageBounds.x0+di, 
                                    self.imageBounds.y0, self.imageBounds.y0 + di)

        for xi, yi in zip(self['x'],self['y']):
            self.Quads.insert(pointQT.qtRec(xi,yi, None))
            
    def measureObjects(self):
        from PYME.Analysis.LMVis import objectMeasure
        
        self.objectMeasures = objectMeasure.measureObjects(self.objects, self.objThreshold)
        
        return self.objectMeasures
    








