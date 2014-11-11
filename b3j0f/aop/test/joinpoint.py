#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

        self.joinpoint = Joinpoint(target=a)

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

        self.joinpoint.advices = [advice]

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

        self.assertEqual(func, A.__init__)

    def test_builtin(self):

        _max = _get_function(max)

        self.assertIs(_max, max)

    def test_method(self):

        class A:
            def method(self):
                pass

        func = _get_function(A.method)

        self.assertIs(func, A.method.__func__)

    def test_instancemethod(self):

        class A:
            def method(self):
                pass

        a = A()

        func = _get_function(a.method)

        self.assertIs(func, a.method.__func__)
        self.assertIs(func, A.method.__func__)

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

    def test_function(self, interception=None, function=None):
        if function is None:
            def function():
                pass

        __code__ = function.__code__

        self.assertFalse(is_intercepted(function))
        self.assertIsNone(get_intercepted(min))

        if interception is None:
            interception, intercepted = _apply_interception(
                function, lambda x: None)

        self.assertTrue(isinstance(interception, FunctionType))

        self.assertIs(interception, function)
        self.assertIs(get_intercepted(function), intercepted)
        self.assertTrue(is_intercepted(function))
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

        self.assertIsNone(get_intercepted(A.method, container=A))
        self.assertFalse(is_intercepted(A.method, container=A))

        interception, intercepted = _apply_interception(
            joinpoint=A.method,
            interception_function=lambda: None,
            container=A)

        joinpoint_type = FunctionType if PY3 else MethodType

        self.assertTrue(
            isinstance(_get_function(interception, container=A),
                joinpoint_type))

        self.assertTrue(is_intercepted(A.method, container=A))
        func = A.method
        if PY2:
            func = func.__func__
        self.assertIs(interception, func)
        self.assertIs(get_intercepted(A.method, container=A),
            _get_function(intercepted))

        _unapply_interception(joinpoint=A.method, container=A)

        self.assertFalse(is_intercepted(A.method, container=A))
        self.assertIsNone(get_intercepted(A.method, container=A))

    def test_class_container(self):
        class A(object):
            def method(self):
                pass

        class B(A):
            pass

        self.assertEqual(A.method, B.method)

        _apply_interception(
            joinpoint=B.method,
            interception_function=lambda: None,
            container=B)

        self.assertNotEqual(A.method, B.method)

        _unapply_interception(
            joinpoint=B.method, container=B)

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
            joinpoint=b.method,
            interception_function=lambda: None)

        self.assertNotEqual(a.__dict__, b.__dict__)

        _unapply_interception(joinpoint=b.method)

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

        freevar = 1

        func = (lambda: freevar) if PY3 else lambda: None

        interception, intercepted = _apply_interception(
            ApplyInterceptionTest, func)

        self.assertTrue(isinstance(ApplyInterceptionTest, type))

        self.assertTrue(is_intercepted(ApplyInterceptionTest))
        self.assertIs(_get_function(interception), ApplyInterceptionTest)
        self.assertIs(get_intercepted(ApplyInterceptionTest), intercepted)

        _unapply_interception(ApplyInterceptionTest)

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertIsNone(get_intercepted(ApplyInterceptionTest))


if __name__ == '__main__':
    main()
