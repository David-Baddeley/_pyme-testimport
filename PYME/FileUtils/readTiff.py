#!/usr/bin/python

##################
# readTiff.py
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

import Image
import numpy as np
from PYME.misc import TiffImagePlugin #monkey patch PIL with improved tiff support from Priithon



def read3DTiff(filename):
    im = Image.open(filename)

    im.seek(0)

    #PIL's endedness support is subtly broken - try to fix it
    #NB this is untested for floating point tiffs
    endedness = 'LE'
    if im.ifd.prefix =='MM':
        endedness = 'BE'
    

    #ima = np.array(im.getdata(), 'int16').newbyteorder('BE')
    ima = np.array(im.getdata()).newbyteorder(endedness)

    print ima.dtype
    
    #print ima.shape

    ima = ima.reshape((im.size[1], im.size[0], 1))

    pos = im.tell()

    try:
        while True:
            pos += 1
            im.seek(pos)

            #ima = np.concatenate((ima, np.array(im.getdata(), 'int16').newbyteorder('BE').reshape((im.size[1], im.size[0], 1))), 2)
            ima = np.concatenate((ima, np.array(im.getdata()).newbyteorder(endedness).reshape((im.size[1], im.size[0], 1))), 2)

    except EOFError:
        pass

    return ima
