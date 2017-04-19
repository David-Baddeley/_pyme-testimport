#!/usr/bin/python

# snapshot.py
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
import PIL

from PYME.LMVis.Extras.animation import VideoPanel
from scipy.misc import toimage
from wx import wx
from OpenGL.GL import GL_LUMINANCE, GL_RGB

#FIXME - does this shadow / duplicate existing functionality?

def save_snapshot(canvas):
    #FIXME - This is the WRONG way to do pixel sizes - we should be using a value in nm
    # we also shouldn't be calling a static method of an unrelated class to do this.
    pixel_size = float(VideoPanel.ask(canvas, message='Please enter the pixel size (1 pixel on the screen = x pixel '
                                                      'in the snapshot', default_value='1'))
    file_name = wx.FileSelector('Save Image as ... (image .png will be appended to filename)')
    if file_name:
        # snap = canvas.getIm(pixel_size, GL_LUMINANCE)
        snap = canvas.getIm(pixel_size, GL_RGB)
        if snap.ndim == 3:
            img = toimage(snap.transpose(1, 0, 2))
        else:
            img = toimage(snap.transpose())
        img = img.transpose(PIL.Image.FLIP_TOP_BOTTOM)
        if not file_name.endswith('.png'):
            img.save('{}.png'.format(file_name))
        else:
            img.save('{}'.format(file_name))


def Plug(vis_fr):
    vis_fr.AddMenuItem('Extras', 'Save Snapshot', lambda e: save_snapshot(vis_fr.glCanvas))
