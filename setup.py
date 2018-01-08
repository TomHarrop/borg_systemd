#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages


# load README.rst
def readme():
    with open('README.rst') as file:
        return file.read()


setup(
    name='borg_slurm',
    version='0.0.1',
    description='python3 wrapper for borgbackup',
    long_description=readme(),
    url='https://github.com/TomHarrop/borg-slurm',
    author='Tom Harrop',
    author_email='twharrop@gmail.com',
    license='GPL-3',
    packages=find_packages(),
    install_requires=['borgbackup>=1.1.3',
                      'Cython>=0.27.3'],
    entry_points={
        'console_scripts': [
            'borg_slurm = borg_slurm.__main__:main']},
    package_data={
        '': ['README.rst']},
    zip_safe=False)
