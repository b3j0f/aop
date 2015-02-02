b3j0f.aop: Aspect Oriented Programming for Python
=================================================

This library aims to improve python aspects oriented programming efficiency among several existing library in respecting reflective properties provided by python.

.. image:: https://pypip.in/license/b3j0f.aop/badge.svg
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: License

.. image:: https://pypip.in/status/b3j0f.aop/badge.svg
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: Development Status

.. image:: https://pypip.in/version/b3j0f.aop/badge.svg?text=version
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: Latest release

.. image:: https://pypip.in/py_versions/b3j0f.aop/badge.svg
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: Supported Python versions

.. image:: https://pypip.in/implementation/b3j0f.aop/badge.svg
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: Supported Python implementations

.. image:: https://pypip.in/format/b3j0f.aop/badge.svg
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: Download format

.. image:: https://travis-ci.org/b3j0f/aop.svg?branch=master
   :target: https://travis-ci.org/b3j0f/aop
   :alt: Build status

.. image:: https://coveralls.io/repos/b3j0f/aop/badge.png
   :target: https://coveralls.io/r/b3j0f/aop
   :alt: Code test coverage

.. image:: https://pypip.in/download/b3j0f.aop/badge.svg?period=month
   :target: https://pypi.python.org/pypi/b3j0f.aop/
   :alt: Downloads

Links
-----

- `Homepage`_
- `PyPI`_
- `Documentation`_

Installation
------------

pip install b3j0f.aop

Features
--------

1. Free and unlimited access: no limit to idea and to knowledge sharing with the license MIT.

2. Performance:

   - less memory consumption in using the __slots__ class property.
   - less time on (un-)weaving and advice application improvement with binary python encoding and in using constants var in code.
   - (dis/en)abling advices without remove them in using dedicated Advice class.

3. Easy to use:

   - joinpoint matching with function or regex.
   - distributed programming:

      + interception context sharing in order to ease behaviour sharing between advices.
      + uuid for advice identification in order to ease its use in a distributed context.

   - maintenable with well named variables and functions, comments and few lines.
   - extensible through pythonic code (PEP8), same logic to function code interception and concern modularisation with one module by joinpoint or advice.
   - respect of aspects vocabulary in order to ease its use among AOP users.
   - close to callable python objects in weaving all types of callable elements such as (built-in) functions, (built-in) class, (built-in) methods, callable objects, etc.
   - advices are callable objects.
   - Unit tests for all functions such as examples.

4. Benchmark:

   - speed execution

Examples
--------

How to change the behaviour of min by max ?

>>> from b3j0f.aop import weave, is_intercepted
>>> advice = lambda joinpoint: max(*joinpoint.args)
>>> weave(target=min, advices=advice)
>>> min(6, 7)
7

How to check if a function is intercepted ?

>>> from b3j0f.aop import is_intercepted
>>> is_intercepted(min)
True

Ok, let's get back its previous behaviour ...

>>> from b3j0f.aop import unweave
>>> unweave(min)
>>> min(6, 7)
6
>>> is_intercepted(min)
False

And with an annotation ?

>>> from b3j0f.aop import weave_on
>>> weave_on(advices=advice)(min)
>>> min(6, 7)
7
>>> is_intercepted(min)
True

Enjoy ...

State of the art
----------------

Related to improving criteria points (1. Free and unlimited access, etc.), a state of the art is provided here.

+------------+----------------------------+----------+-----------+-----+-----------+---------------+
| Library    | Url                        | License  | Execution | Use | Benchmark | Compatibility |
+============+============================+==========+===========+=====+===========+===============+
| b3j0f.aop  | http://tinyurl.com/kaukuco | MIT      | +++       | +++ | +++       | +++ (>=2.6)   |
+------------+----------------------------+----------+-----------+-----+-----------+---------------+
| pyaspects  | http://tinyurl.com/n7ccof5 | GPL 2    | +++       | +   | +         | +             |
+------------+----------------------------+----------+-----------+-----+-----------+---------------+
| aspects    | http://tinyurl.com/obp8t2v | LGPL 2.1 | +         | +   | +         | +             |
+------------+----------------------------+----------+-----------+-----+-----------+---------------+
| aspect     | http://tinyurl.com/lpd87bd | BSD      | +         | -   | -         | +             |
+------------+----------------------------+----------+-----------+-----+-----------+---------------+
| spring     | http://tinyurl.com/dmkpj3  | Apache   | ++        | +   | ++        | ++            |
+------------+----------------------------+----------+-----------+-----+-----------+---------------+
| pytilities | http://tinyurl.com/q49ulr5 | GPL 3    | +         | +   | -         | +             |
+------------+----------------------------+----------+-----------+-----+-----------+---------------+

pyaspects
#########

- Not functional approach: Aspect class definition.
- Side effects: Not close to python API.
- Not optimized Weaving and Time execution: use classes and generic methods.
- Not maintenable: poor comments.
- open-source and use limitations: GPL 2.
- limited in weave filtering.

aspects
#######

- open-source and use limitations: LGPL 2.1.
- more difficulties to understand code with no respect of the AOP vocabulary, packaged into one module and more than 600 files.
- limited in weave filtering.

aspect
######

+ invert the AOP in decorating advices with joinpoint instead of weaving advices on joinpoint.
+ open-source and no use limitations: BSD.

- Simple and functional approach with use of python tools.
- maintenable: commented in respect of the PEP8.
- limited in weave filtering.

spring
######

pytilities
##########

+ Very complex and full library for doing aspects and other things.

- open-source and use limitations: GPL 3.
- not maintenable: missing documentations and not respect of the PEP8.
- Executon time is not optimized with several classes used with generic getters without using __slots__. The only one optimization comes from the yield which requires from users to use it in their own advices (which must be a class).

Perspectives
------------

- Cython implementation.
- Generated documentation.

Donating
--------

.. image:: https://cdn.rawgit.com/gratipay/gratipay-badge/2.3.0/dist/gratipay.png
   :target: https://gratipay.com/b3j0f/
   :alt: I'm grateful for gifts, but don't have a specific funding goal.

.. _Homepage: https://github.com/b3j0f/aop
.. _Documentation: http://pythonhosted.org/b3j0f.aop
.. _PyPI: https://pypi.python.org/pypi/b3j0f.aop/
