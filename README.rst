b3j0f.aop: Aspect Oriented Programming for Python
=================================================

.. image:: https://travis-ci.org/b3j0f/aop.svg?branch=master
    :target: https://travis-ci.org/b3j0f/aop

This library aims to improve python aspects oriented programming efficiency among several existing library.

Installation
------------

pip install b3j0f.aop


Examples
--------

   >>> from b3j0f.aop.advice import weave

   >>> def function_to_intercept():
   >>>    return 1

   >>> weave(function_to_intercept, lambda adviceexecutor: adviceexecutor.proceed(), 1)

   >>> assert function_to_intercept(), (1, 1)
