from setuptools import setup, find_packages
from distutils.extension import Extension
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().split('\n')
    
with open(path.join(here, 'usdQt', 'extensionModule.txt'), encoding='utf-8') as f:
    extensionSources = [str("usdQt/%s" % line.strip()) for line in f.readlines() 
                        if not line.startswith('#') and not line.isspace()]

cppModule = Extension('usdQt._usdQt',
     define_macros = [('BUILD_OPTLEVEL_OPT', None),
                      ('BUILD_COMPONENT_SRC_PREFIX', ""),
                      ('MFB_PACKAGE_NAME', 'usdQt'),
                      ('MFB_ALT_PACKAGE_NAME', 'usdQt'),
                      ('MFB_PACKAGE_MODULE', 'UsdQt'),
                      ('BOOST_PYTHON_NO_PY_SIGNATURES', None)],
     libraries = ['boost_python-mt', 'tbb', 'usd', 'sdf', 'tf'],
     sources = extensionSources,
     extra_compile_args=['-std=c++11'])

setup(
    name='UsdQt',
    version='0.0.1',
    description='USD Qt Components',
    long_description=long_description,
    url='https://github.com/LumaPictures/usdqt-components',
    license='Modified Apache 2.0 License',
    packages=find_packages(exclude=['tests']),
    package_dir={'UsdQt':'usdQt'},
    install_requires=requirements,
    ext_modules=[cppModule]
    # entry_points={
    #     'console_scripts': [
    #         'usdoutliner=sample:main',
    #     ],
    # },
)
