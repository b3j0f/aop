#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from os.path import abspath, dirname, join

from sys import path

# get setup directory abspath
_path = dirname(abspath(__file__))

# import aspects
path.append(_path)
import b3j0f.aop as package

# get long description
with open(join(_path, 'README')) as f:
    desc = f.read()

dependencies = ['b3j0f.utils==0.3']

setup(
    name=package.__name__,
    version=package.__version__,
    install_requires=dependencies,
    packages=find_packages(where='.', exclude=['test.*', '*.test.*']),
    author="b3j0f",
    author_email="jlabejof@yahoo.fr",
    description="Python Aspect Oriented Programming",
    long_description=desc,
    include_package_data=True,
    url='https://github.com/mrbozzo/aop/',
    license='MIT License',
    classifiers=[
        "Development Status :: 1 - Planning",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: French",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    test_suite='b3j0f'
)
