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


def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('PYME',parent_package,top_path)
    config.add_subpackage('Analysis')
    config.add_subpackage('Acquire')
    config.add_subpackage('DSView')
    config.add_subpackage('PSFGen')
    config.add_subpackage('cSMI')
    config.add_subpackage('ParallelTasks')
    config.add_subpackage('FileUtils')
    config.add_subpackage('misc')
    config.add_subpackage('pad')
    config.add_subpackage('dataBrowser')
    
    #config.make_svn_version_py()  # installs __svn_version__.py
    #config.make_config_py()
    return config

if __name__ == '__main__':
    #from numpy.distutils.core import setup
    #setup(**configuration(top_path='').todict())

    from cx_Freeze import setup, Executable
    import matplotlib
    setup(executables=[Executable('Analysis/LMVis/VisGUI.py'),Executable('Acquire/PYMEAquire.py'),Executable('DSView/dh5view.py')],
        options= {'build_exe' : {
          'excludes' : ['pyreadline', 'Tkconstants', 'Tkinter', 'tcl', '_imagingtk', 'PIL._imagingtk', 'ImageTK', 'PIL.ImageTK', 'FixTk'],
          'packages' : ['OpenGL', 'OpenGL.platform', 'OpenGL.arrays']}},

        #data_files=matplotlib.get_py2exe_datafiles(),
      #cmdclass = {'build_ext': build_ext},
      #ext_modules = ext_modules
      )
