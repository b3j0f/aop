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
with open(join(_path, 'README.rst')) as f:
    desc = f.read()

dependencies = ['b3j0f.utils==0.1.0']

setup(
    name=package.__name__,
    version=package.__version__,
    install_requires=dependencies,
    packages=find_packages(where=_path, exclude=['*.test']),
    package_dir={'': _path},
    author="b3j0f",
    author_email="mrb3j0f@gmail.com",
    description="Python Aspect Oriented Programming",
    long_description=desc,
    url='https://github.com/mrbozzo/aop/',
    license='MIT License',
    classifiers=[
        "Development Status :: 1 - Planning",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: French",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Communications",
    ],
    test_suite='b3j0f'
)
