
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
    
    #config.make_svn_version_py()  # installs __svn_version__.py
    #config.make_config_py()
    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())
