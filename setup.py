from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().split('\n')

setup(
    name='usdqt',
    version='0.0.1',
    description='USD Qt Components',
    long_description=long_description,
    url='https://github.com/LumaPictures/usdqt-components',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    install_requires=requirements,

    # entry_points={
    #     'console_scripts': [
    #         'usdoutliner=sample:main',
    #     ],
    # },
)
