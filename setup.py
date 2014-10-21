#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from os.path import abspath, dirname, join

# get setup directory abspath
_path = dirname(abspath(__file__))

# get long description
with open(join(_path, 'README')) as f:
    desc = f.read()

dependencies = ['b3j0f.utils']

setup(
    name='b3j0f.aop',
    version='0.4.5',
    install_requires=dependencies,
    packages=find_packages(exclude=['test.*', '*.test.*']),
    author="b3j0f",
    author_email="jlabejof@yahoo.fr",
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
    ],
    test_suite='b3j0f'
)
