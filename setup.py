import fnmatch
import os
from setuptools import setup, find_packages
from distutils.extension import Extension
from codecs import open  # For consistent encoding

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(os.path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().splitlines()

usdQtFiles = os.listdir(os.path.join(here, 'usdQt'))
extensionSources = []
extensionSources.extend(fnmatch.filter(usdQtFiles, '*.cpp'))
extensionSources.extend(fnmatch.filter(usdQtFiles, '*.h'))
extensionSources = ['usdQt/%s' % name for name in extensionSources]

cppModule = Extension(
    'usdQt._usdQt',
     define_macros = [('BUILD_OPTLEVEL_OPT', None),
                      ('BUILD_COMPONENT_SRC_PREFIX', ""),
                      ('MFB_PACKAGE_NAME', 'usdQt'),
                      ('MFB_ALT_PACKAGE_NAME', 'usdQt'),
                      ('MFB_PACKAGE_MODULE', 'UsdQt'),
                      ('BOOST_PYTHON_NO_PY_SIGNATURES', None),
                      ('PXR_PYTHON_SUPPORT_ENABLED', None)],
     libraries = ['boost_python-mt', 'tbb', 'usd', 'sdf', 'tf'],
     sources = extensionSources,
     extra_compile_args=['-std=c++11', '-Wno-unused-local-typedefs', '-Wno-deprecated'])

packages = find_packages(exclude=['tests'])

setup(
    name='UsdQt',
    version='0.5.0',
    description='USD Qt Components',
    long_description=long_description,
    url='https://github.com/LumaPictures/usd-qt',
    license='Modified Apache 2.0 License',
    packages=packages,
    package_dir={'UsdQt':'usdQt'},
    install_requires=requirements,
    ext_modules=[cppModule]
    # entry_points={
    #     'console_scripts': [
    #         'usdoutliner=sample:main',
    #     ],
    # },
)
