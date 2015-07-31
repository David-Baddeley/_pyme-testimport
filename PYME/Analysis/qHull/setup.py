#!/usr/bin/python

###############
# setup.py
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
import os
import sys
if sys.platform == 'darwin':#MacOS
    linkArgs = []
else:
    linkArgs = ['-static-libgcc']

qhullSources = ['user.c', 'global.c', 'stat.c', 'io.c', 'geom2.c', 'poly2.c',
       'merge.c', 'geom.c', 'poly.c', 'qset.c', 'mem.c', 'usermem.c', 'userprintf.c', 'rboxlib.c','random.c','libqhull.c']

qhullSources = ['qhull/' + s for s in qhullSources]

def configuration(parent_package = '', top_path = None):
    from numpy.distutils.misc_util import Configuration, get_numpy_include_dirs, yellow_text
    config = Configuration('qHull', parent_package, top_path)

    #print 'foo'
    #print yellow_text('foo' + config.local_path)

    srcs = ['triangWrap.c', 'triangRend.c', '../SoftRend/drawTriang.c']

    #check for drift correction code
    if os.path.exists(os.path.join(config.local_path, '../DriftCorrection/triangLhood.c')):
        print((yellow_text('compiling with drift correction')))
        srcs.append('../DriftCorrection/triangLhood.c')
    else:
        print((yellow_text('compiling without drift correction')))
        srcs.append('lhoodStubs.c')

    config.add_extension('triangWrap',
        sources=srcs + qhullSources,
        include_dirs = get_numpy_include_dirs()+['qhull', '../SoftRend'],
	extra_compile_args = ['-O3', '-fno-exceptions', '-ffast-math'],
        extra_link_args=linkArgs)

    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(description = 'qhull wrapper',
    	author = 'David Baddeley',
       	author_email = 'd.baddeley@auckland.ac.nz',
       	url = '',
       	long_description = '''
qhull wrapper for various triangularsiation functions
''',
          license = "Proprietary",
          **configuration(top_path='').todict()
          )
