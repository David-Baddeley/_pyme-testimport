#!/usr/bin/python

##################
# setup.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################
import setuptools #to monkey-patch distutils for ms visualc for python
from PYME.misc import cython_numpy_monkey

def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('PYME',parent_package,top_path)
    config.add_subpackage('PYME')
    
    #config.make_svn_version_py()  # installs __svn_version__.py
    #config.make_config_py()
    config.get_version('PYME/version.py')
    return config

entry_points={
    'console_scripts': [
        'PYMEBatch = PYME.Analysis.Modules.batchProcess:main',
        'taskServerZC = PYME.ParallelTasks.taskServerZC:main',
        'taskWorkerZC = PYME.ParallelTasks.taskWorkerZC:main',
        'PYMEDataServer = PYME.ParallelTasks.HTTPDataServer:main',
        'PYMEClusterDup = PYME.io.clusterDuplication:main',
        'PYMEDistributor = PYME.ParallelTasks.PYMEDistributor:main',
        'PYMEscmosmapgen = PYME.Analysis.gen_sCMOS_maps:main',
        'PYMENodeServer = PYME.ParallelTasks.PYMENodeServer:main',
        'dh5view = PYME.DSView.dsviewer:main',
        'PYMEAcquire = PYME.Acquire.PYMEAcquire:main',
        'VisGUI = PYME.LMVis.VisGUI:main',
        'launchWorkers = PYME.ParallelTasks.launchWorkers:main',
        #'taskServerZC = PYME.ParallelTasks.taskServerZC:main',
        #'taskWorkerZC = PYME.ParallelTasks.taskWorkerZC:main',
        'fitMonP = PYME.ParallelTasks.fitMonP:main',
        'bakeshop = PYME.recipes.bakeshop:main',
    ]
}

if __name__ == '__main__':
    import setuptools
    from numpy.distutils.core import setup
    conf = configuration(top_path='').todict()
    conf['entry_points'] = entry_points
    setup(**conf)
