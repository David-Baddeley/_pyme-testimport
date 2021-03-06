from .base import register_module, ModuleBase, Filter
from .traits import Input, Output, Float, Enum, CStr, Bool, Int, List, DictStrStr, DictStrList, ListFloat, ListStr

import numpy as np
import pandas as pd
from PYME.IO import tabular
from PYME.LMVis import renderers


@register_module('ExtractTableChannel')
class ExtractTableChannel(ModuleBase):
    """Create and return a ColourFilter which has filtered out one colour channel from a table of localizations."""
    inputName = Input('measurements')
    channel = CStr('everything')
    outputName = Output('filtered')

    def execute(self, namespace):
        inp = namespace[self.inputName]

        map = tabular.colourFilter(inp, currentColour=self.channel)

        if 'mdh' in dir(inp):
            map.mdh = inp.mdh

        namespace[self.outputName] = map

    @property
    def _colour_choices(self):
        #try and find the available column names
        try:
            return tabular.colourFilter.get_colour_chans(self._parent.namespace[self.inputName])
        except:
            return []

    @property
    def pipeline_view(self):
        from traitsui.api import View, Group, Item
        from PYME.ui.custom_traits_editors import CBEditor

        modname = ','.join(self.inputs) + ' -> ' + self.__class__.__name__ + ' -> ' + ','.join(self.outputs)

        return View(Group(Item('channel', editor=CBEditor(choices=self._colour_choices)), label=modname))

    @property
    def default_view(self):
        from traitsui.api import View, Group, Item
        from PYME.ui.custom_traits_editors import CBEditor

        return View(Item('inputName', editor=CBEditor(choices=self._namespace_keys)),
                    Item('_'),
                    Item('channel', editor=CBEditor(choices=self._colour_choices)),
                    Item('_'),
                    Item('outputName'), buttons=['OK'])


@register_module('DensityMapping')
class DensityMapping(ModuleBase):
    """ Use density estimation methods to generate an image from localizations

     """
    inputLocalizations = Input('localizations')
    outputImage = Output('output')
    renderingModule = Enum(renderers.RENDERERS.keys())

    pixelSize = Float(5)
    jitterVariable = CStr('1.0')
    jitterScale = Float(1.0)
    jitterVariableZ = CStr('1.0')
    jitterScaleZ = Float(1.0)
    MCProbability = Float(1.0)
    numSamples = Int(10)
    colours = List(['none'])
    zBoundsMode = Enum(['manual', 'min-max'])
    zBounds = ListFloat([-500, 500])
    zSliceThickness = Float(50.0)
    softRender = Bool(True)

    def execute(self, namespace):
        from PYME.IO.image import ImageBounds
        inp = namespace[self.inputLocalizations]
        if not isinstance(inp, tabular.colourFilter):
            cf = tabular.colourFilter(inp, None)
            cf.mdh = inp.mdh
        else:
            cf = inp

        cf.imageBounds = ImageBounds.estimateFromSource(inp)
        if self.zBoundsMode == 'min-max':
            self.zBounds[0], self.zBounds[1] = float(cf.imageBounds.z0), float(cf.imageBounds.z1)

        renderer = renderers.RENDERERS[str(self.renderingModule)](None, cf)

        namespace[self.outputImage] = renderer.Generate(self.get())

@register_module('AddPipelineDerivedVars')
class Pipelineify(ModuleBase):
    inputFitResults = Input('FitResults')
    inputDriftResults = Input('')
    inputEvents = Input('')
    outputLocalizations = Output('localizations')

    pixelSizeNM = Float(1)


    def execute(self, namespace):
        from PYME.LMVis import pipeline
        fitResults = namespace[self.inputFitResults]
        mdh = fitResults.mdh

        mapped_ds = tabular.mappingFilter(fitResults)


        if not self.pixelSizeNM == 1: # TODO - check close instead?
            mapped_ds.addVariable('pixelSize', self.pixelSizeNM)
            mapped_ds.setMapping('x', 'x*pixelSize')
            mapped_ds.setMapping('y', 'y*pixelSize')

        #extract information from any events
        events = namespace.get(self.inputEvents, None)
        if isinstance(events, tabular.TabularBase):
            events = events.to_recarray()

        ev_maps, ev_charts = pipeline._processEvents(mapped_ds, events, mdh)
        pipeline._add_missing_ds_keys(mapped_ds, ev_maps)

        #Fit module specific filter settings
        if 'Analysis.FitModule' in mdh.getEntryNames():
            fitModule = mdh['Analysis.FitModule']

            if 'LatGaussFitFR' in fitModule:
                mapped_ds.addColumn('nPhotons', pipeline.getPhotonNums(mapped_ds, mdh))

        mapped_ds.mdh = mdh

        namespace[self.outputLocalizations] = mapped_ds


@register_module('MultiviewFold') #FIXME - move to multi-view specific module and potentially rename
class MultiviewFold(ModuleBase):
    """Fold localizations from images which have been taken with an image splitting device but analysed without channel
    awareness.

    Images taken in this fashion will have the channels side by side. This module folds the x co-ordinate to overlay the
    different channels, using the image metadata to determine the appropriate ROI boundaries. The current implementation
    is somewhat limited as it only handles folding along the x axis, and assumes that ROI sizes and spacings are completely
    uniform.
    """
    inputName = Input('localizations')
    outputName = Output('folded')

    def execute(self, namespace):
        from PYME.Analysis.points import multiview

        inp = namespace[self.inputName]

        if 'mdh' not in dir(inp):
            raise RuntimeError('Unfold needs metadata')

        mapped = multiview.foldX(inp, inp.mdh)
        mapped.mdh = inp.mdh

        namespace[self.outputName] = mapped


@register_module('MultiviewShiftCorrect') #FIXME - move to multi-view specific module and rename OR make consistent with existing shift correction
class MultiviewShiftCorrect(ModuleBase):
    """Applies chromatic shift correction to folded localization data that was acquired with an image splitting device,
    but localized without splitter awareness."""
    inputName = Input('folded')
    shiftMapLocation = CStr('') #FIXME - change name to indicate that this is a filename/path/URL. Should probably be a File trait (or derived class which deals with clusterIO)
    outputName = Output('registered')

    def execute(self, namespace):
        from PYME.Analysis.points import multiview
        from PYME.IO import unifiedIO
        import json

        inp = namespace[self.inputName]

        if 'mdh' not in dir(inp):
            raise RuntimeError('ShiftCorrect needs metadata')

        if self.shiftMapLocation == '':  # grab shftmap from the metadata
            s = unifiedIO.read(inp.mdh['Shiftmap'])
        else:
            s = unifiedIO.read(self.shiftMapLocation)

        shiftMaps = json.loads(s)

        mapped = tabular.mappingFilter(inp)

        dx, dy = multiview.calcShifts(mapped, shiftMaps)
        mapped.addColumn('chromadx', dx)
        mapped.addColumn('chromady', dy)

        mapped.setMapping('x', 'x + chromadx')
        mapped.setMapping('y', 'y + chromady')

        mapped.mdh = inp.mdh

        namespace[self.outputName] = mapped


@register_module('FindClumps') #FIXME - move to multi-view specific module and rename OR make consistent with existing clumping
class FindClumps(ModuleBase):
    """Create a new mapping object which derives mapped keys from original ones"""
    inputName = Input('registered')
    gapTolerance = Int(1, desc='Number of off-frames allowed to still be a single clump')
    radiusScale = Float(2.0, desc='Factor by which error_x is multiplied to detect clumps. The default of 2-sigma means we link ~95% of the points which should be linked')
    radius_offset = Float(0., desc='Extra offset (in nm) for cases where we want to link despite poor channel alignment')
    probeAware = Bool(False, desc='''Use probe-aware clumping. NB this option does not work with standard methods of colour
                                             specification, and splitting by channel and clumping separately is preferred''') 
    outputName = Output('clumped')

    def execute(self, namespace):
        from PYME.Analysis.points import multiview

        inp = namespace[self.inputName]

        if self.probeAware and 'probe' in inp.keys(): #special case for using probe aware clumping NB this is a temporary fudge for non-standard colour handling
            mapped = multiview.probeAwareFindClumps(inp, self.gapTolerance, self.radiusScale, self.radius_offset)
        else: #default
            mapped = multiview.findClumps(inp, self.gapTolerance, self.radiusScale, self.radius_offset)
        
        if 'mdh' in dir(inp):
            mapped.mdh = inp.mdh

        namespace[self.outputName] = mapped


@register_module('MergeClumps') #FIXME - move to multi-view specific module and rename OR make consistent with existing clumping
class MergeClumps(ModuleBase):
    """Create a new mapping object which derives mapped keys from original ones"""
    inputName = Input('clumped')
    outputName = Output('merged')
    labelKey = CStr('clumpIndex')

    def execute(self, namespace):
        from PYME.Analysis.points import multiview

        inp = namespace[self.inputName]

        try:
            grouped = multiview.mergeClumps(inp, inp.mdh.getOrDefault('Multiview.NumROIs', 0), labelKey=self.labelKey)
            grouped.mdh = inp.mdh
        except AttributeError:
            grouped = multiview.mergeClumps(inp, numChan=0, labelKey=self.labelKey)

        namespace[self.outputName] = grouped


@register_module('MapAstigZ') #FIXME - move to multi-view specific module and rename
class MapAstigZ(ModuleBase):
    """Create a new mapping object which derives mapped keys from original ones"""
    inputName = Input('merged')
    astigmatismMapLocation = CStr('') #FIXME - rename and possibly change type
    outputName = Output('zmapped')

    def execute(self, namespace):
        from PYME.Analysis.points.astigmatism import astigTools
        from PYME.IO import unifiedIO
        import json

        inp = namespace[self.inputName]

        if 'mdh' not in dir(inp):
            raise RuntimeError('MapAstigZ needs metadata')

        if self.astigmatismMapLocation == '':  # grab calibration from the metadata
            s = unifiedIO.read(inp.mdh['Analysis.AstigmatismMapID'])
        else:
            s = unifiedIO.read(self.astigmatismMapLocation)

        astig_calibrations = json.loads(s)

        mapped = tabular.mappingFilter(inp)

        z, zerr = astigTools.lookup_astig_z(mapped, astig_calibrations, plot=False)

        mapped.addColumn('astigZ', z)
        mapped.addColumn('zLookupError', zerr)
        mapped.setMapping('z', 'astigZ + z')

        mapped.mdh = inp.mdh

        namespace[self.outputName] = mapped

@register_module('IDTransientFrames')
class IDTransientFrames(ModuleBase): #FIXME - move to multi-view specific module and potentially rename (depending on whether we introduce scoping)
    """
    Adds an 'isTransient' column to the input datasource so that one can filter localizations that are from frames
    acquired during z-translation
    """
    inputName = Input('zmapped')
    inputEvents = Input('Events')
    framesPerStep = Float()
    outputName = Output('transientFiltered')

    def execute(self, namespace):
        from PYME.experimental import zMotionArtifactUtils

        inp = namespace[self.inputName]

        mapped = tabular.mappingFilter(inp)

        if 'mdh' not in dir(inp):
            if self.framesPerStep <= 0:
                raise RuntimeError('idTransientFrames needs metadata')
            else:
                fps = self.framesPerStep
        else:
            fps = inp.mdh['StackSettings.FramesPerStep']

        mask = zMotionArtifactUtils.flagMotionArtifacts(mapped, namespace[self.inputEvents], fps)
        mapped.addColumn('piezoUnstable', mask)

        mapped.mdh = inp.mdh

        namespace[self.outputName] = mapped

@register_module('DBSCANClustering')
class DBSCANClustering(ModuleBase):
    """
    Performs DBSCAN clustering on input dictionary

    Parameters
    ----------

        searchRadius: search radius for clustering
        minPtsForCore: number of points within SearchRadius required for a given point to be considered a core point

    Notes
    -----

    See `sklearn.cluster.dbscan` for more details about the underlying algorithm and parameter meanings.

    """
    inputName = Input('filtered')

    columns = ListStr(['x', 'y', 'z'])
    searchRadius = Float()
    minClumpSize = Int()

    outputName = Output('dbscanClustered')

    def execute(self, namespace):
        from sklearn.cluster import dbscan

        inp = namespace[self.inputName]
        mapped = tabular.mappingFilter(inp)

        # Note that sklearn gives unclustered points label of -1, and first value starts at 0.
        core_samp, dbLabels = dbscan(np.vstack([inp[k] for k in self.columns]).T,
                                     self.searchRadius, self.minClumpSize)

        # shift dbscan labels up by one to match existing convention that a clumpID of 0 corresponds to unclumped
        mapped.addColumn('dbscanClumpID', dbLabels + 1)

        # propogate metadata, if present
        try:
            mapped.mdh = inp.mdh
        except AttributeError:
            pass

        namespace[self.outputName] = mapped

    @property
    def hide_in_overview(self):
        return ['columns']

#TODO - this is very specialized and probably doesn't belong here - at least not in this form
@register_module('ClusterCountVsImagingTime')
class ClusterCountVsImagingTime(ModuleBase):
    """
    WARNING: This module will likely move, dissapear, or be refactored

    ClusterCountVsImagingTime iteratively filters a dictionary-like object on t, and at each step counts the number of
    labeled objects (e.g. DBSCAN clusters) which contain at least N-points. It does this for two N-points, so one can be
    set according to density with all frames included, and the other can be set for one of the earlier frame-counts.

    args:
        stepSize: number of frames to add in on each iteration
        labelsKey: key containing labels for each localization
        lowerMinPtsPerCluster:
        higherMinPtsPerCluster:

    returns:
        dictionary-like object with the following keys:
            t: upper bound on frame number included in calculations on each iteration.
            N_labelsWithLowMinPoints:
            N_labelsWithHighMinPoints:

    From wikipedia: "While minPts intuitively is the minimum cluster size, in some cases DBSCAN can produce smaller
    clusters. A DBSCAN cluster consists of at least one core point. As other points may be border points to more than
    one cluster, there is no guarantee that at least minPts points are included in every cluster."
    """
    inputName = Input('input')

    labelsKey = CStr('dbscanClumpID')
    lowerMinPtsPerCluster = Int(3)
    higherMinPtsPerCluster = Int(6)
    stepSize = Int(3000)

    outputName = Output('incremented')

    def execute(self, namespace):
        from PYME.IO import tabular

        if self.lowerMinPtsPerCluster > self.higherMinPtsPerCluster:
            print('Swapping low and high MinPtsPerCluster - input was reversed')
            temp = self.lowerMinPtsPerCluster
            self.lowerMinPtsPerCluster = self.higherMinPtsPerCluster
            self.higherMinPtsPerCluster = temp

        iters = (int(np.max(namespace[self.inputName]['t']))/int(self.stepSize)) + 2

        # other counts
        lowDensMinPtsClumps = np.empty(iters)
        lowDensMinPtsClumps[0] = 0
        hiDensMinPtsClumps = np.empty(iters)
        hiDensMinPtsClumps[0] = 0
        t = np.empty(iters)
        t[0] = 0

        inp = tabular.mappingFilter(namespace[self.inputName])

        for ind in range(1, iters):  # start from 1 since t=[0,0] will yield no clumps
            # filter time
            inc = tabular.resultsFilter(inp, t=[0, self.stepSize*ind])
            t[ind] = np.max(inc['t'])

            cid, counts = np.unique(inc[self.labelsKey], return_counts=True)
            # cmask = np.in1d(inc['DBSCAN_allFrames'], cid)

            cidL = cid[counts >= self.lowerMinPtsPerCluster]
            lowDensMinPtsClumps[ind] = np.sum(cidL != -1)  # ignore unclumped in count
            cid = cid[counts >= self.higherMinPtsPerCluster]
            hiDensMinPtsClumps[ind] = np.sum(cid != -1)  # ignore unclumped in count


        res = tabular.resultsFilter({'t': t,
                                     'N_labelsWithLowMinPoints': lowDensMinPtsClumps,
                                     'N_labelsWithHighMinPoints': hiDensMinPtsClumps})

        # propagate metadata, if present
        try:
            res.mdh = namespace[self.inputName].mdh
        except AttributeError:
            pass

        namespace[self.outputName] = res


@register_module('LabelsFromImage')
class LabelsFromImage(ModuleBase):
    """
    Maps each point in the input table to a pixel in a labelled image, and extracts the pixel value at that location to
    use as a label for the point data. 

    Inputs
    ------
    inputName: name of tabular input containing positions ('x', 'y', and optionally 'z' columns should be present)
    inputImage: name of image input containing labels

    Outputs
    -------
    outputName: name of tabular output. A mapped version of the tabular input with 2 extra columns
        objectID: Label number from image, mapped to each localization within that label
        NEvents: Number of localizations within the label that a given localization belongs to

    """
    inputName = Input('input')
    inputImage = Input('labeled')

    outputName = Output('labeled_points')

    def execute(self, namespace):
        from PYME.IO import tabular
        from PYME.Analysis.points import cluster_morphology

        inp = namespace[self.inputName]
        img = namespace[self.inputImage]
        #img = image.openImages[dlg.GetStringSelection()]

        ids, numPerObject = cluster_morphology.get_labels_from_image(img, inp)

        labeled = tabular.mappingFilter(inp)
        labeled.addColumn('objectID', ids)
        labeled.addColumn('NEvents', numPerObject[ids - 1])

        # propagate metadata, if present
        try:
            labeled.mdh = namespace[self.inputName].mdh
        except AttributeError:
            pass

        namespace[self.outputName] = labeled


@register_module('MeasureClusters3D')
class MeasureClusters3D(ModuleBase):
    """
    Measures the 3D morphology of clusters of points

    Inputs
    ------

    inputName : name of tabular data containing x, y, and z columns and labels identifying which cluster each point
                belongs to.

    Outputs
    -------

    outputName: a new tabular data source containing measurements of the clusters
    
    Parameters
    ----------
        labelKey: name of column to use as a label identifying clusters

    Notes
    -----

    Measures calculated (to be expanded)
    --------------------------------------
        count: the number of points in the cluster
        x, y, z: Center of mass positions, no weighting based on localization precision
        gyrationRadius: AKA RMS distance to center of cluster - see also supplemental text of DOI: 10.1038/nature16496
        axis0, axis1, axis2: principle axes of point cloud using SVD
        sigma0, sigma1, sigma2: spread along each principle axis (the singular values/ sqrt(N-1))

    """
    inputName = Input('input')
    labelKey = CStr('clumpIndex')

    outputName = Output('clusterMeasures')

    def execute(self, namespace):
        from PYME.Analysis.points import cluster_morphology as cmorph
        import numpy as np

        inp = namespace[self.inputName]

        # make sure labeling scheme is consistent with what pyme conventions
        if np.min(inp[self.labelKey]) < 0:
            raise UserWarning('This module expects 0-label for unclustered points, and no negative labels')

        labels = inp[self.labelKey]
        I = np.argsort(labels)
        I = I[labels[I] > 0]
        
        x_vals, y_vals, z_vals = inp['x'][I], inp['y'][I], inp['z'][I]
        labels = labels[I]
        maxLabel = labels[-1]
        
        #find the unique labels, and their separation in the sorted list of points
        unique_labels, counts = np.unique(labels, return_counts=True)
        
        #allocate memory to store results in
        measurements = np.zeros(maxLabel+1, cmorph.measurement_dtype)

        # loop over labels, recalling that input is now sorted, and we know how many points are in each label.
        # Note that missing labels result in zeroed entries (i.e. the initial values are not changed).
        # Missing values can be filtered out later, if desired, by filtering on the 'counts' column, but having a dense
        # array where index == label number makes any postprocessing in which we might want to find the data
        # corresponding to a particular label MUCH easier and faster.
        indi = 0
        for label_num, ct in zip(unique_labels, counts):
            indf = indi + ct

            # create x,y,z arrays for this cluster, and calculate center of mass
            x, y, z = x_vals[indi:indf], y_vals[indi:indf], z_vals[indi:indf]
            
            cmorph.measure_3d(x, y, z, output=measurements[label_num])

            indi = indf

        meas = tabular.recArrayInput(measurements)

        try:
            meas.mdh = namespace[self.inputName].mdh
        except AttributeError:
            pass

        namespace[self.outputName] = meas


@register_module('FiducialCorrection')
class FiducialCorrection(ModuleBase):
    """
    Maps each point in the input table to a pixel in a labelled image, and extracts the pixel value at that location to
    use as a label for the point data.

    Inputs
    ------
    inputName: name of tabular input containing positions ('x', 'y', and optionally 'z' columns should be present)
    inputImage: name of image input containing labels

    Outputs
    -------
    outputName: name of tabular output. A mapped version of the tabular input with 2 extra columns
        objectID: Label number from image, mapped to each localization within that label
        NEvents: Number of localizations within the label that a given localization belongs to

    """
    inputLocalizations = Input('Localizations')
    inputFiducials = Input('Fiducials')

    clumpRadiusVar = CStr('error_x')
    clumpRadiusMultiplier = Float(5.0)
    timeWindow = Int(25)
    
    temporalFilter = Enum(['Gaussian', 'Uniform', 'Median'])
    temporalFilterScale = Float(10.0)

    outputName = Output('corrected_localizations')
    outputFiducials = Output('corrected_fiducials')

    def execute(self, namespace):
        from PYME.IO import tabular
        from PYME.Analysis.points import fiducials

        locs = namespace[self.inputLocalizations]
        fids = namespace[self.inputFiducials]
        
        t_fid, fid_trajectory, clump_index = fiducials.extractAverageTrajectory(fids, clumpRadiusVar=self.clumpRadiusVar,
                                                        clumpRadiusMultiplier=float(self.clumpRadiusMultiplier),
                                                        timeWindow=int(self.timeWindow),
                                                        filter=self.temporalFilter, filterScale=float(self.temporalFilterScale))
        
        out = tabular.mappingFilter(locs)
        t_out = out['t']

        out_f = tabular.mappingFilter(fids)
        out_f.addColumn('clumpIndex', clump_index)
        t_out_f = out_f['t']

        for dim in fid_trajectory.keys():
            print(dim)
            out.addColumn('fiducial_{0}'.format(dim), np.interp(t_out, t_fid, fid_trajectory[dim]))
            out.setMapping(dim, '{0} - fiducial_{0}'.format(dim))

            out_f.addColumn('fiducial_{0}'.format(dim), np.interp(t_out_f, t_fid, fid_trajectory[dim]))
            out_f.setMapping(dim, '{0} - fiducial_{0}'.format(dim))

        # propagate metadata, if present
        try:
            out.mdh = locs.mdh
        except AttributeError:
            pass

        namespace[self.outputName] = out
        namespace[self.outputFiducials] = out_f


@register_module('SphericalHarmonicShell')
class SphericalHarmonicShell(ModuleBase): #FIXME - this likely doesnt belong here
    """
    Fits a shell represented by a series of spherical harmonic co-ordinates to a 3D set of points. The points
    should represent a hollow, fairly round structure (e.g. the surface of a cell nucleus). The object should NOT
    be filled (i.e. points should only be on the surface).
    
    Parameters
    ----------

        max_m_mode: Maximum order to calculate to.
        zscale: Factor to scale z by when projecting onto spherical harmonics. It is helpful to scale z such that the
            x, y, and z extents are roughly equal.
            
    Inputs
    ------
        inputName: name of a tabular datasource containing the points to be fitted with a spherical harmonic shell
        

    """
    inputName = Input('input')
    max_m_mode = Int(5)
    z_scale = Float(5.0)
    n_iterations = Int(2)
    init_tolerance = Float(0.3, desc='Fractional tolerance on radius used in first iteration')
    outputName = Output('harmonicShell')

    def execute(self, namespace):
        import PYME.Analysis.points.spherical_harmonics as spharm
        from PYME.IO.ragged import RaggedCache
        from PYME.IO import MetaDataHandler

        inp = namespace[self.inputName]

        modes, c, centre = spharm.sphere_expansion_clean(inp['x'], inp['y'], inp['z'] * self.z_scale,
                                                               mmax=self.max_m_mode,
                                                               centre_points=True,
                                                               nIters=self.n_iterations,
                                                               tol_init=self.init_tolerance)
        
        mdh = MetaDataHandler.NestedClassMDHandler()
        try:
            mdh.copyEntriesFrom(namespace[self.inputName].mdh)
        except AttributeError:
            pass
        
        mdh['Processing.SphericalHarmonicShell.ZScale'] = self.z_scale
        mdh['Processing.SphericalHarmonicShell.MaxMMode'] = self.max_m_mode
        mdh['Processing.SphericalHarmonicShell.NIterations'] = self.n_iterations
        mdh['Processing.SphericalHarmonicShell.InitTolerance'] = self.init_tolerance

        namespace[self.outputName] = RaggedCache([{'z_scale': self.z_scale, 'centre': centre,
                                                   'modes': modes, 'coeffs' : c},], mdh)

@register_module('AddShellMappedCoordinates')
class AddShellMappedCoordinates(ModuleBase): #FIXME - this likely doesnt belong here
    """

    Maps x,y,z co-ordinates into the co-ordinate space of spherical harmonic shell. Notably, a normalized
    radius is provided, which can be used to determine which localizations are within the structure.

    Inputs
    ------

    inputName : name of tabular data whose coordinates one would like to have generated with respect to a spherical
            harmonic structure
    inputSphericalHarmonics: name of reference spherical harmonic shell representation (e.g.
            output of recipes.localizations.SphericalHarmonicShell). See PYME.Analysis.points.spherical_harmonics.

    Outputs
    -------

    outputName: a new tabular data source containing spherical coordinates generated with respect to the spherical
    harmonic representation.

    Parameters
    ----------

    None

    Notes
    -----

    """


    inputName = Input('points')
    inputSphericalHarmonics = Input('harmonicShell')

    outputName = Output('shell_mapped')

    def execute(self, namespace):
        import PYME.Analysis.points.spherical_harmonics as spharm
        from PYME.IO.MetaDataHandler import NestedClassMDHandler

        inp = namespace[self.inputName]
        mapped = tabular.mappingFilter(inp)

        rep = namespace[self.inputSphericalHarmonics][0]
        
        x0, y0, z0 = rep['centre']

        # calculate theta, phi, and rad for each localization in the pipeline
        theta, phi, datRad = spharm.cart2sph(inp['x'] - x0, inp['y'] - y0,
                                             (inp['z'] - z0)/rep['z_scale'])

        mapped.addColumn('r', datRad)
        mapped.addColumn('theta', theta)
        mapped.addColumn('phi', phi)
        mapped.addColumn('r_norm', datRad / spharm.reconstruct_from_modes(rep['modes'],rep['coefficients'], theta, phi))

        try:
            # note that copying overwrites shared fields
            mapped.mdh = NestedClassMDHandler(rep.mdh)
            mapped.mdh.copyEntriesFrom(inp.mdh)
        except AttributeError:
            pass

        namespace[self.outputName] = mapped

