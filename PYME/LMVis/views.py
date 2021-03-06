#!/usr/bin/python

# View.py
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
import json
from collections import OrderedDict

import numpy


class View(object):
    JSON_VIEW_ID = 'view_id'
    JSON_VEC_UP = 'vec_up'
    JSON_VEC_BACK = 'vec_back'
    JSON_VEC_RIGHT = 'vec_right'
    JSON_TRANSLATION = 'translation'
    JSON_ZOOM = 'zoom'

    def __init__(self, view_id, vec_up, vec_back, vec_right, translation, zoom):
        """
        
        Parameters
        ----------
        view_id     is up to you, as long as serializable with json
        vec_up      np.array
        vec_back    np.array
        vec_right   np.array
        translation np.array
        zoom        usually a scalar
        """
        super(View, self).__init__()
        self._view_id = view_id
        self._vec_up = vec_up
        self._vec_back = vec_back
        self._vec_right = vec_right
        self._translation = translation
        self._zoom = zoom

    @property
    def view_id(self):
        return self._view_id

    @view_id.setter
    def view_id(self, value):
        if value:
            self._view_id = value

    @property
    def vec_up(self):
        return self._vec_up

    @property
    def vec_back(self):
        return self._vec_back

    @property
    def vec_right(self):
        return self._vec_right

    @property
    def translation(self):
        return self._translation

    @property
    def zoom(self):
        return self._zoom

    def __add__(self, other):
        return View(None,
                    self.vec_up + other.vec_up,
                    self.vec_back + other.vec_back,
                    self.vec_right + other.vec_right,
                    self.translation + other.translation,
                    self._zoom + other.zoom
                    )

    def __sub__(self, other):
        return View(None,
                    self.vec_up - other.vec_up,
                    self.vec_back - other.vec_back,
                    self.vec_right - other.vec_right,
                    self.translation - other.translation,
                    self._zoom - other.zoom
                    )

    def __mul__(self, scalar):
        return View(None,
                    self.vec_up * scalar,
                    self.vec_back * scalar,
                    self.vec_right * scalar,
                    self.translation * scalar,
                    self._zoom * scalar
                    )

    def __div__(self, scalar):
        return View(None,
                    self.vec_up / scalar,
                    self.vec_back / scalar,
                    self.vec_right / scalar,
                    self.translation / scalar,
                    self._zoom / scalar
                    )

    def normalize_view(self):
        self._vec_up = self.normalize(self.vec_up)
        self._vec_back = self.normalize(self.vec_back)
        self._vec_right = self.normalize(self.vec_right)
        return self

    @staticmethod
    def normalize(array):
        return array / numpy.linalg.norm(array)

    def to_json(self):
        ordered_dict = OrderedDict()
        ordered_dict[self.JSON_VIEW_ID] = self.view_id
        ordered_dict[self.JSON_VEC_UP] = self.vec_up.tolist()
        ordered_dict[self.JSON_VEC_BACK] = self.vec_back.tolist()
        ordered_dict[self.JSON_VEC_RIGHT] = self.vec_right.tolist()
        ordered_dict[self.JSON_TRANSLATION] = self.translation.tolist()
        ordered_dict[self.JSON_ZOOM] = self.zoom

        return ordered_dict

    def __str__(self):
        return str(self.to_json())

    @staticmethod
    def decode_json(json_obj):
        # if '__type__' in json_obj and json_obj['__type__'] == View:
        return View(View.get_json_field(json_obj, View.JSON_VIEW_ID, 'id'),
                    View.get_json_array(json_obj, View.JSON_VEC_UP, numpy.array([0, 1, 0])),
                    View.get_json_array(json_obj, View.JSON_VEC_BACK, numpy.array([0, 0, 1])),
                    View.get_json_array(json_obj, View.JSON_VEC_RIGHT, numpy.array([1, 0, 0])),
                    View.get_json_array(json_obj, View.JSON_TRANSLATION, numpy.array([0, 0, 0])),
                    View.get_json_field(json_obj, View.JSON_ZOOM, 1))

    @staticmethod
    def get_json_field(json_object, key, default=None):
        """
        
        Parameters
        ----------
        key         name of the field in the json file
        default     value that should be used if not found
                    that way we could support older json files

        Returns
        -------

        """
        try:
            return json_object[key]
        except KeyError:
            return default

    @staticmethod
    def get_json_array(json_object, key, default=None):
        """

                Parameters
                ----------
                key         name of the field in the json file
                default     value that should be used if not found
                            that way we could support older json files

                Returns
                -------

                """
        try:
            return numpy.array(json_object[key])
        except KeyError:
            return default


class VideoView(View):
    JSON_DURATION = 'duration'
    
    def __init__(self, view_id, vec_up, vec_back, vec_right, translation, zoom, duration):
        """

        Parameters
        ----------
        view_id     is up to you, as long as serializable with json
        vec_up      np.array
        vec_back    np.array
        vec_right   np.array
        translation np.array
        zoom        usually a scalar
        duration    duration of the view transition in seconds
        """
        super(VideoView, self).__init__(view_id, vec_up, vec_back, vec_right, translation, zoom)
        self._duration = duration
    
    @property
    def duration(self):
        return self._duration
    
    @duration.setter
    def duration(self, value):
        if value:
            self._duration = value
    
    def to_json(self):
        ordered_dict = super(VideoView, self).to_json()
        ordered_dict[self.JSON_DURATION] = self._duration
        return ordered_dict
    
    @staticmethod
    def decode_json(json_obj):
        # if '__type__' in json_obj and json_obj['__type__'] == View:
        return VideoView(View.get_json_field(json_obj, View.JSON_VIEW_ID, 'id'),
                         View.get_json_array(json_obj, View.JSON_VEC_UP, numpy.array([0, 1, 0])),
                         View.get_json_array(json_obj, View.JSON_VEC_BACK, numpy.array([0, 0, 1])),
                         View.get_json_array(json_obj, View.JSON_VEC_RIGHT, numpy.array([1, 0, 0])),
                         View.get_json_array(json_obj, View.JSON_TRANSLATION, numpy.array([0, 0, 0])),
                         View.get_json_field(json_obj, View.JSON_ZOOM, 1),
                         View.get_json_field(json_obj, VideoView.JSON_DURATION, 1))


if __name__ == '__main__':
    view = View(1, numpy.array([1, 1, 1]), numpy.array([2, 2, 2]), numpy.array([3, 3, 3]),
                numpy.array([0, 0, 0]), 5)
    a = json.loads(json.dumps(view.to_json()))
    view2 = View.decode_json(a)
