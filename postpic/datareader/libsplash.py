#
# This file is part of postpic.
#
# postpic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# postpic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with postpic. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014 Axel Huebl
'''
.. _PIConGPU:  http://picongpu.hzdr.de
.. _libSplash: https://github.com/ComputationalRadiationPhysics/libSplash

Reader for the libSplash file format written by PIConGPU_.

Dependencies:
  - h5py: A hdf5 reader for python (libSplash writes field and particle
          data in a certain hirachy in hdf5 format)

Axel Huebl 2014
'''

from . import Dumpreader_ifc
from . import Simulationreader_ifc
import numpy as np
import h5py as h5
import re
from .. import _const

__all__ = ['Splashreader']#, 'Visitreader']


class Splashreader(Dumpreader_ifc):
    '''
    The Reader implementation for data written by PIConGPU
    in libSplash's HDF5 format.

    Args:
      hdf5file : String
        A String containing the relative Path to the .h5 file.
    '''

    def __init__(self, hdf5file, **kwargs):
        super(self.__class__, self).__init__(hdf5file, **kwargs)
        import os.path
        import sdf
        if not os.path.isfile(hdf5file):
            raise IOError('File "' + str(hdf5file) + '" doesnt exist.')
        self._data = h5.File(hdf5file, "r")["data/<T>/[particles/fields]/Name[/y]"]

    def keys(self):
        return self._data.keys()

    def __getitem__(self, key):
        return self._data[key]

    def timestep(self):
        return self['Header']['step']

    def time(self):
        return np.float64(self['Header']['time'])

    def simdimensions(self):
        return float(re.match('Epoch(\d)d',
                     self['Header']['code_name']).group(1))

    def _returnkey2(self, key1, key2, average=False):
        key = key1 + key2
        if average:
            key = key1 + '_average' + key2
        return self[key]

    def dataE(self, axis, **kwargs):
        axsuffix = {0: 'x', 1: 'y', 2: 'z'}[_const.axesidentify[axis]]
        return np.float64(self._returnkey2('Electric Field', '/E' +
                                           axsuffix, **kwargs))

    def dataB(self, axis, **kwargs):
        axsuffix = {0: 'x', 1: 'y', 2: 'z'}[_const.axesidentify[axis]]
        return np.float64(self._returnkey2('Magnetic Field', '/B' +
                                           axsuffix, **kwargs))

    def grid(self, axis):
        axsuffix = {0: 'X', 1: 'Y', 2: 'Z'}[_const.axesidentify[axis]]
        return self['Grid/Grid/' + axsuffix]

    def listSpecies(self):
        ret = []
        for key in self.keys():
            match = re.match('Particles/Px/(\w+)', key)
            if match:
                ret = np.append(ret, match.group(1))
        ret.sort()
        return ret

    def getSpecies(self, species, attrib):
        """
        Returns one of the attributes out of (x,y,z,px,py,pz,weight,ID) of
        this particle species.
        returning None means that this particle property wasnt dumped.
        Note that this is different from returning an empty list!
        """
        attribid = _const.attribidentify[attrib]
        options = {9: lambda s: 'Particles/Weight/' + s,
                   0: lambda s: 'Grid/Particles/' + s + '/X',
                   1: lambda s: 'Grid/Particles/' + s + '/Y',
                   2: lambda s: 'Grid/Particles/' + s + '/Z',
                   3: lambda s: 'Particles/Px/' + s,
                   4: lambda s: 'Particles/Py/' + s,
                   5: lambda s: 'Particles/Pz/' + s,
                   10: lambda s: 'Particles/ID/' + s}
        try:
            ret = np.float64(self[options[attribid](species)])
        except(KeyError):
            ret = None
        return ret

    def getderived(self):
        '''
        Returns all Keys starting with "Derived/".
        '''
        ret = []
        for key in self._data.keys():
            r = re.match('Derived/[\w/ ]*', key)
            if r:
                ret.append(r.group(0))
        ret.sort()
        return ret

    def __str__(self):
        return '<libSplashreader at "' + str(self.dumpidentifier) + '">'


class Visitreader(Simulationreader_ifc):
    '''
    Reads a series of dumps specified in a .visit file. This is specifically
    written for .visit files from the PIConGPU_ code, but should also work for
    any other code using these files.
    '''

    def __init__(self, visitfile, dumpreadercls=Sdfreader, **kwargs):
        super(self.__class__, self).__init__(visitfile, **kwargs)
        self.visitfile = visitfile
        self.dumpreadercls = dumpreadercls
        import os.path
        if not os.path.isfile(visitfile):
            raise IOError('File "' + str(visitfile) + '" doesnt exist.')
        self._dumpfiles = []
        with open(visitfile) as f:
            relpath = os.path.dirname(visitfile)
            for line in f:
                self._dumpfiles.append(os.path.join(relpath,
                                       line.replace('\n', '')))

    def __len__(self):
        return len(self._dumpfiles)

    def getDumpreader(self, index):
        return self.dumpreadercls(self._dumpfiles[index])

    def __str__(self):
        return '<Visitreader at "' + self.visitfile + '">'
