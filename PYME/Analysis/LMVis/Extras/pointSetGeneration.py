#!/usr/bin/python
##################
# pointSetGeneration.py
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


import wx
try:
    from enthought.traits.api import HasTraits, Float, File, BaseEnum, Enum, List, Instance, Str
    from enthought.traits.ui.api import View, Item, EnumEditor, InstanceEditor
except ImportError:
    from traits.api import HasTraits, Float, File, BaseEnum, Enum, List, Instance, Str
    from traitsui.api import View, Item, EnumEditor, InstanceEditor
    
from PYME.DSView import image

#class PointGenerationPanel(wx.Panel):
#    def __init__(self, parent, generator):
#        wx.Panel.__init__(self, parent)
#
#        vsizer = wx.BoxSizer(wx.VERTICAL)
#
#        self.nbPointDataSource = wx.Notebook(self,-1)
#
#        wormlikePanel = wx.Panel(self, -1)
#        wsizer =


class PointSource(HasTraits):
    def refresh_choices(self):
        pass

class WormlikeSource(PointSource):
    kbp = Float(100)
    steplength=Float(10.0)
    lengthPerKbp=Float(10.0)
    persistLength=Float(150.0)
    #name = Str('Wormlike Chain')

    def getPoints(self):
        from PYME.Acquire.Hardware.Simulator import wormlike2
        wc = wormlike2.wormlikeChain(self.kbp, self.steplength, self.lengthPerKbp, self.persistLength)

        return wc.xp, wc.yp



class FileSource(PointSource):
    file = File()
    #name = Str('Points File')

    def getPoints(self):
        import numpy as np
        return np.load(self.file)



class WRDictEnum (BaseEnum):
    def __init__ ( self, wrdict, *args, **metadata ):
        self.wrdict = wrdict
        #self.values        = tuple( values )
        #self.fast_validate = ( 5, self.values )
        self.name = ''
        super( BaseEnum, self ).__init__( None, **metadata )

    @property
    def values(self):
        return self.wrdict.keys()

    #def info ( self ):
    #    return ' or '.join( [ repr( x ) for x in self.values ] )

    def create_editor ( self):
        #from enthought.traits.ui.api import EnumEditor
        #print dict(self.wrdict.items())

        ed = EnumEditor( values   = self,
                           cols     = self.cols or 3,
                           evaluate = self.evaluate,
                           mode     = self.mode or 'radio' )

        return ed


class ImageSource(PointSource):
    image = WRDictEnum(image.openImages)
    points_per_pixel = Float(0.1)
    #name = Str('Density Image')
    #foo = Enum([1,2,3,4])

    def getPoints(self):
        from PYMEnf.Simulation import locify
        print((self.image))

        im = image.openImages[self.image]
        #import numpy as np
        d = im.data[:,:,0,0]

        #normalise the image
        d = d/d.max()

        return locify.locify(d, pixelSize=im.pixelSize, pointsPerPixel=self.points_per_pixel)

    def refresh_choices(self):
        ed = self.trait('image').editor

        if ed:
            ed._values_changed()

        #super( HasTraits, self ).configure_traits(*args, **kwargs)


#    traits_view = View( Item('points_per_pixel'),
#                        Item('image'),
##                        Item( 'image',
##                              label='Image',
##                              editor =
##                                  EnumEditor(values={'foo':0, 'bar' : 1}),#image.openImages),
##                              ),
#                        buttons = ['OK'])
        





class Generator(HasTraits):
    meanIntensity = Float(500)
    meanDuration = Float(3)
    backgroundIntensity = Float(300)
    meanEventNumber = Float(2)
    scaleFactor = Float(2)
    meanTime= Float(2000)

    sources = List([WormlikeSource(), ImageSource(), FileSource()])

    source = Instance(PointSource)

    traits_view = View( Item( 'source',
                            label= 'Point source',
                            editor =
                            InstanceEditor(name = 'sources',
                                editable = True),
                                ),
                        Item('_'),
                        Item('meanIntensity'),
                        Item('meanDuration'),
                        Item('meanEventNumber'),
                        Item('meanTime'),
                        Item('_'),
                        Item('backgroundIntensity'),
                        
                        buttons = ['OK'])

    def __init__(self, visFr = None):
        self.visFr = visFr
        self.source = self.sources[0]

        if visFr:
            ID_GEN_POINTS = wx.NewId()
            ID_CONF_SIMUL = wx.NewId()
            ID_GEN_EVENTS = wx.NewId()

            mSimul = wx.Menu()

            mSimul.Append(ID_CONF_SIMUL, "Configure")
            mSimul.Append(ID_GEN_POINTS, "Generate fluorophore positions and events")
            mSimul.Append(ID_GEN_EVENTS, "Generate events")

            visFr.extras_menu.AppendSubMenu(mSimul, 'Synthetic Data')

            visFr.Bind(wx.EVT_MENU, self.OnGenPoints, id=ID_GEN_POINTS)
            visFr.Bind(wx.EVT_MENU, self.OnGenEvents, id=ID_GEN_EVENTS)
            visFr.Bind(wx.EVT_MENU, self.OnConfigure, id=ID_CONF_SIMUL)

    def OnConfigure(self, event):
        self.source.refresh_choices()
        self.edit_traits()

    def OnGenPoints(self, event):
        self.xp, self.yp = self.source.getPoints()
        self.OnGenEvents(None)

    def OnGenEvents(self, event):
        from PYMEnf.Simulation import locify
        #from PYME.Acquire.Hardware.Simulator import wormlike2
        from PYME.Analysis.LMVis import inpFilt
        from PYME.Analysis.LMVis.visHelpers import ImageBounds
        import pylab
        
        #wc = wormlike2.wormlikeChain(100)
        
        pipeline = self.visFr.pipeline
        pipeline.filename='Simulation'

        pylab.figure()
        pylab.plot(self.xp, self.yp, 'x') #, lw=2)
        if isinstance(self.source, WormlikeSource):
            pylab.plot(self.xp, self.yp, lw=2)

        res = locify.eventify(self.xp, self.yp, self.meanIntensity, self.meanDuration, self.backgroundIntensity, self.meanEventNumber, self.scaleFactor, self.meanTime)
        pylab.plot(res['fitResults']['x0'],res['fitResults']['y0'], '+')

        pipeline.selectedDataSource = inpFilt.mappingFilter(inpFilt.fitResultsSource(res))
        pipeline.imageBounds = ImageBounds.estimateFromSource(pipeline.selectedDataSource)
        pipeline.dataSources.append(pipeline.selectedDataSource)

        from PYME.Acquire.MetaDataHandler import NestedClassMDHandler
        pipeline.mdh = NestedClassMDHandler()
        pipeline.mdh['Camera.ElectronsPerCount'] = 1
        pipeline.mdh['Camera.TrueEMGain'] = 1
        pipeline.mdh['Camera.CycleTime'] = 1
        pipeline.mdh['voxelsize.x'] = .110

        try:
            pipeline.filterKeys.pop('sig')
        except:
            pass
        self.visFr.RegenFilter()
        self.visFr.SetFit()



def Plug(visFr):
    '''Plugs this module into the gui'''
    Generator(visFr)




