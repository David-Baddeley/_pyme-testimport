#!/usr/bin/python

###############
# fftwWisdom.py
#
# Copyright David Baddeley, 2012
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
################


import fftw3f
import os

WISDOMFILE = os.path.join(os.path.split(__file__)[0], 'fftw_wisdom')

def load_wisdom():
    if os.path.exists(WISDOMFILE):
        f = open(WISDOMFILE, 'r')
        fftw3f.import_wisdom_from_string(f.read())
        f.close()
    
def save_wisdom():
    f = open(WISDOMFILE, 'w')
    f.write(fftw3f.export_wisdom_to_string())
    f.close()