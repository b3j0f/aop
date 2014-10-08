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

setup(
    name=package.__name__,
    version=package.__version__,
    packages=find_packages(where=_path, exclude=['*.test']),
    package_dir={'': _path},
    author="b3j0f",
    author_email="mrb3j0f@gmail.com",
    description="Python Aspect Oriented Programming",
    long_description=desc,
    url='https://github.com/mrbozzo/aspects/',
    license='MIT License',
    classifiers=[
        "Development Status :: 1 - Planning",
        "License :: MIT",
        "Natural Language :: French",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Communications",
    ],
    test_suite='b3j0f'
)
