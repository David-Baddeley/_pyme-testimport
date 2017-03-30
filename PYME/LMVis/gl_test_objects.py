#!/usr/bin/python

# gl_test_objects.py
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
import csv

import numpy

from PYME.Acquire.Hardware.Simulator.wormlike2 import wormlikeChain


class TestObject(object):
    MICROMETER_CONVERSION_CONSTANT = 1000

    def __init__(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z
        self.added_objects = set()

    @property
    def x(self):
        new_x = self._x
        for other_object in self.added_objects:
            new_x = numpy.append(new_x, other_object.x)
        return new_x

    @property
    def y(self):
        new_y = self._y
        for other_object in self.added_objects:
            new_y = numpy.append(new_y, other_object.y)
        return new_y

    @property
    def z(self):
        new_z = self._z
        for other_object in self.added_objects:
            new_z = numpy.append(new_z, other_object.z)
        return new_z

    def translate(self, x=0, y=0, z=0):
        self._x += x
        self._y += y
        self._z += z
        for other_object in self.added_objects:
            other_object.translate(x, y, z)

    def scale(self, x=1, y=1, z=1):
        self._x *= x
        self._y *= y
        self._z *= z
        for other_object in self.added_objects:
            other_object.scale(x, y, z)

    def add(self, other):
        self.added_objects.add(other)

    def save(self, file_name):
        with open(file_name, 'wb') as csv_file:
            # fieldnames = ['x', 'z', 'z']
            writer = csv.writer(csv_file)

            # writer.writeheader()
            collection = numpy.column_stack((self._x, self._y, self._z))
            writer.writerow(('x', 'y', 'z'))
            writer.writerows(collection)


class NineCollections(TestObject):

    def __init__(self):
        x = self.MICROMETER_CONVERSION_CONSTANT*((numpy.arange(270) % 27)/9 + 0.1*numpy.random.randn(270))
        y = self.MICROMETER_CONVERSION_CONSTANT*((numpy.arange(270) % 9)/3 + 0.1*numpy.random.randn(270))
        z = self.MICROMETER_CONVERSION_CONSTANT*(numpy.arange(270) % 3 + 0.1*numpy.random.randn(270))
        TestObject.__init__(self, x, y, z)


class Cloud(TestObject):
    DISTANCE = 200.0

    def __init__(self, amount_points):
        x = Cloud.DISTANCE * numpy.random.randn(amount_points)
        y = Cloud.DISTANCE * numpy.random.randn(amount_points)
        z = Cloud.DISTANCE * numpy.random.randn(amount_points)
        TestObject.__init__(self, x, y, z)


class Ellipsoid(TestObject):

    AXIS_A = 4
    AXIS_B = 5
    AXIS_C = 2

    def __init__(self, amount_points,
                 axis_a=AXIS_A,
                 axis_b=AXIS_B,
                 axis_c=AXIS_C,
                 size=5):
        """
        
        Parameters
        ----------
        amount_points   amount of points in this ellipsoid
        axis_a          
        axis_b
        axis_c
        max_size        the maximum dimension of axis_a, axis_b, axis_c is max_size micrometers big
        """
        max_axis = max(axis_a, axis_b, axis_c)
        x = size * self.MICROMETER_CONVERSION_CONSTANT * numpy.random.randn(amount_points) * axis_a / max_axis
        y = size * self.MICROMETER_CONVERSION_CONSTANT * numpy.random.randn(amount_points) * axis_b / max_axis
        z = size * self.MICROMETER_CONVERSION_CONSTANT * numpy.random.randn(amount_points) * axis_c / max_axis
        TestObject.__init__(self, x, y, z)


class Worm(TestObject):
    def __init__(self, kbp=0.1, length_per_kbp=10.0):
        chain = wormlikeChain(kbp, steplength=20.0, lengthPerKbp=length_per_kbp, persistLength=50)
        TestObject.__init__(self, chain.xp, chain.yp, chain.zp)


class Vesicle(TestObject):

    WIDTH = 1

    def __init__(self, diameter=1.0, amount_points=100, hole_size=0.5 * numpy.pi, hole_pos=0):
        """

        Parameters
        ----------
        diameter        of the vesicle in micrometer
        hole_size       in rad [0-2*pi]
        hole_pos        in rad [0-2*pi]
                        0 => y=0, x=1 => right
        """

        radius = diameter * self.MICROMETER_CONVERSION_CONSTANT / 2.0
        rad = numpy.random.rand(amount_points)*(2*numpy.pi-hole_size)+hole_size/2 + hole_pos
        dist = radius - numpy.random.rand(amount_points) * self.WIDTH

        x = dist * numpy.cos(rad)
        y = dist * numpy.sin(rad)
        z = numpy.ones(x.shape) * 0.1 * numpy.random.randn(amount_points)

        TestObject.__init__(self, x, y, z)


class NoisePlane(TestObject):
    def __init__(self, diameter=1.0, density=20.0):
        """
        
        Parameters
        ----------
        diameter    in micrometer
        density     per micrometer^2
        """
        radius = diameter / 2.0
        amount_of_points = int(round(density * radius * radius * numpy.pi))
        radius = radius * self.MICROMETER_CONVERSION_CONSTANT
        rad = numpy.random.rand(amount_of_points) * 2 * numpy.pi
        dist = radius * numpy.sqrt(numpy.random.rand(amount_of_points))
        x = dist * numpy.cos(rad)
        y = dist * numpy.sin(rad)
        z = numpy.ones(amount_of_points) * 0.1 * numpy.random.randn(amount_of_points)
        TestObject.__init__(self, x, y, z)


class Clusterizer(TestObject):
    def __init__(self, test_object, multiply, distance):
        self.test_object = test_object
        self.multiply = multiply
        self.distance = distance

        base_points_x, base_points_y, base_points_z, self.amount_of_points = self.get_points()
        offsets = self.get_offsets()

        new_positions_x = base_points_x + offsets[0]
        new_positions_y = base_points_y + offsets[1]
        new_positions_z = base_points_z + offsets[2]

        TestObject.__init__(self, new_positions_x, new_positions_y, new_positions_z)

    def get_points(self):
        test_object = self.test_object
        return (numpy.repeat(test_object.x, self.multiply),
                numpy.repeat(test_object.y, self.multiply),
                numpy.repeat(test_object.z, self.multiply), len(test_object.x)*self.multiply)

    def get_offsets(self):
        offsets_x = (numpy.random.randn(self.amount_of_points) - 0.5) * 2 * self.distance
        offsets_y = (numpy.random.randn(self.amount_of_points) - 0.5) * 2 * self.distance
        offsets_z = (numpy.random.randn(self.amount_of_points) - 0.5) * 2 * self.distance
        return offsets_x, offsets_y, offsets_z


class ExponentialClusterizer(Clusterizer):
    def __init__(self, test_object, expectation_value, distance):
        self.expectation_value = expectation_value
        super(ExponentialClusterizer, self).__init__(test_object, 0, distance)

    def get_points(self):
        amount_of_input_points = len(self.test_object.x)

        print(amount_of_input_points)
        cluster_sizes = numpy.round(
            numpy.random.exponential(self.expectation_value, amount_of_input_points)).astype(int)
        base_points_x = numpy.repeat(self.test_object.x, cluster_sizes)
        base_points_y = numpy.repeat(self.test_object.y, cluster_sizes)
        base_points_z = numpy.repeat(self.test_object.z, cluster_sizes)
        amount_of_points = len(base_points_x)
        return base_points_x, base_points_y, base_points_z, amount_of_points
