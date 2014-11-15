#!/usr/bin/env python
# -*- coding: utf-8 -*-

# --------------------------------------------------------------------
# The MIT License (MIT)
#
# Copyright (c) 2014 Jonathan Labéjof <jonathan.labejof@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# --------------------------------------------------------------------

from unittest import main

from b3j0f.utils.ut import UTCase
from b3j0f.aop.joinpoint import (
    Joinpoint,
    is_intercepted, get_intercepted,
    _apply_interception, _unapply_interception,
    _get_function
)
from b3j0f.utils.version import PY3, PY2

from types import MethodType, FunctionType


class JoinpointTest(UTCase):

    def setUp(self):

        self.count = 0

        def a():
            self.count += 1
            return self.count

        self.joinpoint = Joinpoint(target=a, advices=[])

    def test_execution(self):

        result = self.joinpoint.start()

        self.assertEqual(result, 1)

    def test_execution_twice(self):

        result = self.joinpoint.start()

        self.assertEqual(result, 1)

        result = self.joinpoint.start()

        self.assertEqual(result, 2)

    def test_add_advices(self):

        def advice(joinpoint):

            proceed = joinpoint.proceed()

            return proceed, 3

        self.joinpoint._advices = [advice]

        result = self.joinpoint.start()

        self.assertEqual(result, (1, 3))

        result = self.joinpoint.start()

        self.assertEqual(result, (2, 3))


class GetFunctionTest(UTCase):

    def test_class(self):

        class A(object):
            pass

        func = _get_function(A)

        self.assertEqual(func, A.__init__)

    def test_namespace(self):

        class A:
            pass

        func = _get_function(A)

        _function = A if PY2 else A.__init__

        self.assertEqual(func, _function)

    def test_builtin(self):

        _max = _get_function(max)

        self.assertIs(_max, max)

    def test_method(self):

        class A:
            def method(self):
                pass

        func = _get_function(A.method)

        _func = A.method if PY3 else A.method.__func__

        self.assertIs(func, _func)

    def test_instancemethod(self):

        class A:
            def method(self):
                pass

        a = A()

        func = _get_function(a.method)

        self.assertIs(func, a.method.__func__)
        _func = A.method if PY3 else A.method.__func__
        self.assertIs(func, _func)

    def test_function(self):

        def function():
            pass

        func = _get_function(function)

        self.assertIs(func, function)

    def test_call(self):

        class A:
            def __call__(self):
                pass

        a = A()

        func = _get_function(a)

        self.assertEqual(func, a.__call__.__func__)


class ApplyInterceptionTest(UTCase):

    def test_function(self):
        def function():
            pass

        __code__ = function.__code__

        self.assertFalse(is_intercepted(function))
        self.assertIsNone(get_intercepted(min))

        interception, intercepted = _apply_interception(
            function, lambda x: None)

        self.assertTrue(isinstance(interception, FunctionType))

        self.assertIs(interception, function)
        self.assertIs(get_intercepted(interception), intercepted)
        self.assertTrue(is_intercepted(interception))
        self.assertIsNot(interception.__code__, __code__)
        self.assertIs(intercepted.__code__, __code__)

        _unapply_interception(function)

        self.assertFalse(is_intercepted(function))
        self.assertIs(interception, function)
        self.assertIs(function.__code__, __code__)
        self.assertIsNone(get_intercepted(function))

    def test_method(self):
        class A(object):
            def method(self):
                pass

        self.assertIsNone(get_intercepted(A.method))
        self.assertFalse(is_intercepted(A.method))

        interception_fn = lambda: None

        interception, intercepted = _apply_interception(
            target=A.method,
            interception_fn=interception_fn,
            ctx=A)

        joinpoint_type = FunctionType if PY3 else MethodType

        self.assertTrue(isinstance(interception, joinpoint_type))
        self.assertTrue(is_intercepted(A.method))
        self.assertEqual(interception, A.method)
        self.assertIs(intercepted, get_intercepted(A.method))

        _unapply_interception(target=A.method, ctx=A)

        self.assertFalse(is_intercepted(A.method))
        self.assertIsNone(get_intercepted(A.method))

    def test_class_container(self):
        class A(object):
            def method(self):
                pass

        class B(A):
            pass

        self.assertEqual(A.method, B.method)

        _apply_interception(
            target=B.method,
            interception_fn=lambda: None,
            ctx=B)

        self.assertNotEqual(A.method, B.method)

        _unapply_interception(
            target=B.method, ctx=B)

        self.assertEqual(A.method, B.method)

    def test_instance(self):
        class A(object):
            def method(self):
                pass

        class B(A):
            pass

        a = A()
        b = B()

        self.assertEqual(a.__dict__, b.__dict__)

        _apply_interception(
            target=b.method,
            interception_fn=lambda: None)

        self.assertNotEqual(a.__dict__, b.__dict__)

        _unapply_interception(target=b.method)

        self.assertEqual(a.__dict__, b.__dict__)

    def test_builtin(self):

        function = min

        self.assertIsNone(get_intercepted(min))
        self.assertFalse(is_intercepted(min))

        interception, intercepted = _apply_interception(min, lambda: None)

        self.assertTrue(isinstance(interception, FunctionType))

        self.assertTrue(is_intercepted(min))
        self.assertIs(interception, min)
        self.assertIsNot(min, function)
        self.assertIs(get_intercepted(min), intercepted)

        _unapply_interception(interception)

        self.assertFalse(is_intercepted(min))
        self.assertIsNot(interception, min)
        self.assertIs(min, function)
        self.assertIsNone(get_intercepted(min))

    def test_class(self):

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertIsNone(get_intercepted(ApplyInterceptionTest))

        func = (lambda: None)

        __init__ = ApplyInterceptionTest.__init__

        interception, intercepted = _apply_interception(
            ApplyInterceptionTest,
            func
        )

        self.assertEqual(intercepted, __init__)
        self.assertEqual(interception, ApplyInterceptionTest.__init__)

        self.assertTrue(is_intercepted(ApplyInterceptionTest))
        self.assertIs(get_intercepted(ApplyInterceptionTest), intercepted)

        _unapply_interception(ApplyInterceptionTest)

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertIsNone(get_intercepted(ApplyInterceptionTest))


if __name__ == '__main__':
    main()
