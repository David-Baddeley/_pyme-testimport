#!/usr/bin/python

# gl_test_apps.py
#
# Copyright Michael Graff
#   graff@hm.edu
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
import argparse
from ast import literal_eval

import pylab
import time
from numpy import random
from wx import wx

from PYME.LMVis import gl_test_objects
from PYME.LMVis.gl_render3D_shaders import LMGLShaderCanvas
from PYME.LMVis.gl_test_objects import *


class TestApp(wx.App):
    def __init__(self, *args):
        wx.App.__init__(self)
        self._frame = None
        self._canvas = None

    def OnInit(self):
        self.setup()
        to = NineCollections()
        self._canvas.displayMode = '3D'
        self._canvas.pointSize = 50

        self._canvas.setPoints3D(to.x, to.y, to.z, mode='pointsprites')
        self._canvas.recenter(to.x, to.y)
        self.done()
        return True

    def setup(self):
        self._frame = wx.Frame(None, -1, 'ball_wx', wx.DefaultPosition, wx.Size(800, 800))
        self._canvas = LMGLShaderCanvas(self._frame)
        self._canvas.gl_context.SetCurrent(self._canvas)
        self._canvas.SetCurrent()
        self._canvas.initialize()
        self._canvas.setCMap(pylab.cm.hot)
        self._canvas.clim = [0.1, 0.9]
        self._canvas.displayMode = '3D'
        self._canvas.pointSize = 50

    def done(self):
        self._canvas.Refresh()
        self._frame.Show()
        self.SetTopWindow(self._frame)

    def save(self, test_object_file, configuration_file):
        if self.to:
            self.to.save(test_object_file)
            self.to.add_to_json('file', test_object_file)
            self.to.add_to_json('time', '%s' % pylab.datetime.datetime.now())
            configurations = json.dumps(self.to, cls=TestObjectEncoder, indent=4)
            with open(configuration_file, 'wb') as f:
                f.writelines(configurations)


class XTestApp(TestApp):
    def OnInit(self):
        self.setup()
        to = Cloud(40)
        self._canvas.setPoints3D(to.x, to.y, to.z, mode='pointsprites')
        self._canvas.recenter(to.x, to.y)
        self.done()
        return True


class MassTest(TestApp):
    def OnInit(self):
        self.setup()
        to = Cloud(1000000)
        self._canvas.setPoints3D(to.x, to.y, to.z, normalize(to.z), self._canvas.cmap, self._canvas.clim,
                                 mode='pointsprites')
        self._canvas.recenter(to.x, to.y)
        self.done()
        return True


class Fish(TestApp):
    def __init__(self, *args):
        self.to = Ellipsoid(3000)
        self.to = ExponentialClusterizer(self.to, 4, 30)
        concentration = Worm(250)
        concentration.translate(1, 0, 0)
        self.to.add(concentration)
        concentration = Worm(200)
        concentration.translate(-2.3, 0.5, 0)
        self.to.add(concentration)
        super(Fish, self).__init__(*args)

    def OnInit(self):
        self.setup()

        self._canvas.pointSize = 50

        self._canvas.setPoints3D(self.to.x, self.to.y, self.to.z, normalize(self.to.z),
                                 self._canvas.cmap, self._canvas.clim, mode='pointsprites')
        self._canvas.recenter(self.to.x, self.to.y)

        self.done()
        return True


class Vesicles(TestApp):
    def __init__(self, *args):
        # scales in micrometer
        scales = [1, 0.5, 0.125, 0.100, 0.080]
        x_shifts = [-3, -1, 1, 3]
        base_amount_of_points = 70
        offset = 0
        self.to = TestObjectContainer()
        row, column = 1, 1
        for scale in scales:
            for x_shift in x_shifts:
                hole_position = numpy.random.random()
                hole_position_with_pi = hole_position * 2 * numpy.pi
                has_hole = numpy.random.random() >= 0.5
                amount_points = max(int(round(numpy.random.normal(base_amount_of_points, 20))), 0)
                if has_hole:
                    new_test_object = Vesicle(diameter=scale, amount_points=amount_points,
                                              hole_pos=hole_position_with_pi)
                else:
                    new_test_object = Vesicle(diameter=scale, amount_points=amount_points, hole_size=0)
                new_test_object.translate(x_shift, offset, 0)

                self.to.add(new_test_object)
                new_test_object.add_to_json('row', row)
                new_test_object.add_to_json('column', column)
                column += 1
            row += 1
            column = 1
            offset -= 2

        noise = NoisePlane(20, 10)
        noise.translate(0, offset / 2, 0)
        self.to.add(noise)

        self.to = ExponentialClusterizer(self.to, 4, 10)

        super(Vesicles, self).__init__(*args)

    def OnInit(self):
        self.setup()

        self._canvas.pointSize = 10

        self._canvas.setPoints3D(self.to.x, self.to.y, self.to.z, normalize(self.to.z),
                                 self._canvas.cmap, self._canvas.clim, mode='pointsprites')
        self._canvas.recenter(self.to.x, self.to.y)

        self.done()
        return True


class Worms(TestApp):
    def __init__(self, *args):
        super(Worms, self).__init__(*args)
        self.to = gl_test_objects.Worm()

    def OnInit(self):
        self.setup()

        self._canvas.pointSize = 50

        self._canvas.setPoints3D(self.to.x, self.to.y, self.to.z, normalize(self.to.z),
                                 self._canvas.cmap, self._canvas.clim, mode='pointsprites')
        self._canvas.recenter(self.to.x, self.to.y)

        self.done()
        return True


class HarmonicCells(TestApp):
    def __init__(self, args):
        self._input_file = args.harmonics_file
        self._dimensions = literal_eval(args.harmonics_dimensions)
        self.to = TestObjectContainer()
        row_offset = self._dimensions[0] * 1.2
        column_offset = self._dimensions[1] * 1.2
        for row in numpy.arange(4):
            for column in numpy.arange(4):
                print('row {}: column {}'.format(row, column))
                cell = self.create_harmonic_cell()
                cell.translate(row * row_offset, column * column_offset, 0)
                cell.add_to_json('row', row + 1)
                cell.add_to_json('column', column + 1)
                self.to.add(cell)
        super(HarmonicCells, self).__init__(args)

    def create_harmonic_cell(self):
        return HarmonicCell(self._input_file, self._dimensions)

    def OnInit(self):
        self.setup()

        self._canvas.pointSize = 20

        self._canvas.setPoints3D(self.to.x, self.to.y, self.to.z, normalize(self.to.z),
                                 self._canvas.cmap, self._canvas.clim, mode='pointsprites')
        self._canvas.recenter(self.to.x, self.to.y)

        self.done()
        return True

def normalize(values):
    return (values - min(values)) / (max(values) - min(values))


def main():
    args = parse()
    start_time = time.time()
    app = eval(args.testapp)(args)
    app.save(args.output_csv, args.output_json)
    end_time = time.time()
    print('Duration to generate the test objects in s: {}'.format(end_time-start_time))
    app.MainLoop()


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('testapp', help="testapp that should be used", default=Vesicles)
    parser.add_argument('output_csv', help='file that should be used to save the generated points as csv')
    parser.add_argument('output_json', help='file that should be used to save the configuration as json')
    parser.add_argument('--harmonics_file', help='the file used for input spherical harmonics data')
    parser.add_argument('--harmonics_dimensions', help='the dimensions of the bounding box in micrometer (x, y, z)')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()
