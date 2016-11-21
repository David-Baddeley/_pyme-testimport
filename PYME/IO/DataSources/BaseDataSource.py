#!/usr/bin/python

###############
# BaseDataSource.py
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

import numpy as np
class DefaultList(list):
    """List which returns a default value for items not in the list"""
    def __init__(self, *args):
        list.__init__(self, *args)

    def __getitem__(self, index):
        try:
            return list.__getitem__(self, index)
        except IndexError:
            return 1


class BaseDataSource(object):
    oldData = None
    oldSlice = None
    #nTrueDims =3
    additionalDims = 'T'
    #sizeZ = 1
    sizeC = 1
    
    @property
    def nTrueDims(self):
        """The number of dimensions which are truely present within the data,
        rather than just faked"""
        return 2 + len(self.additionalDims)
    
    @property
    def shape(self):
        """The 4D shape of the datasource"""
        #if self.type == 'DataSource':
        return DefaultList(self.getSliceShape() + (self.getNumSlices()/self.sizeC,self.sizeC) )
        
    def getSlice(self, ind):
        """Return the nth 2D slice of the DataSource where the higher dimensions
        have been flattened.
        
        equivalent to indexing contiguous 4D data with data[:,:,ind%data.shape[2], ind/data.shape[3]]
        
        e.g. for a 100x100x50x2 DataSource, getSlice(20) would return data[:,:,20,0].squeeze()
        whereas getSlice(75) would return data[:,:,25, 1].squeeze()
        """
        raise NotImplementedError

    def getSliceShape(self):
        """Return the 2D shape of a slice"""
        raise NotImplementedError

    def getNumSlices(self):
        """Return the number of 2D slices. This is the product of the
        dimensions > 2
        """
        raise NotImplementedError

    def getEvents(self):
        """Return any events which are ascociated with this DataSource"""
        raise NotImplementedError
        
    def __getitem__(self, keys):
        """Allows slicing into the DataSource as though it were a numpy ndarray.
        
        We ignore any dimensions higher than the dimensionaltyof the data.
        """
        keys = list(keys)
        #print keys
        for i in range(len(keys)):
            if not keys[i].__class__ == slice:
                keys[i] = slice(keys[i],keys[i] + 1)
        if keys == self.oldSlice:
            return self.oldData
        self.oldSlice = keys
        #if len(keys) > len(self.data.shape):
        #    keys = keys[:len(self.data.shape)]
        #if self.dim_1_is_z:
        #    keys = [keys[2]] + keys[:2] + keys[3:]

        #print keys

        
        if self.nTrueDims <= 3: #x,y, z/t
            r = np.concatenate([np.atleast_2d(self.getSlice(i)[keys[0], keys[1]])[:,:,None] for i in range(*keys[2].indices(self.getNumSlices()))], 2)
        elif self.nTrueDims == 4:
            #print keys[3]
            col_indices =  range(*keys[3].indices(self.shape[3]))
            #print col_indices
            r = []
            for c_i in col_indices:
                if self.additionalDims == 'TC':
                    indices = np.arange(*keys[2].indices(self.shape[2])) + c_i*self.shape[2]
                elif self.additionalDims == 'CT':
                    indices = np.arange(*keys[2].indices(self.shape[2]))*self.shape[3] + c_i

                r.append(np.concatenate([np.atleast_2d(self.getSlice(i)[keys[0], keys[1]])[:,:,None] for i in indices], 2))

            if len(r) > 1:
                r = np.concatenate([r_i[:,:,:,None] for r_i in r], 3)
            else:
                r = r[0]
            

        self.oldData = r

        return r