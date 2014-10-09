#!/usr/bin/env python
# -*- coding: utf-8 -*-


from unittest import TestCase, main

from b3j0f.aop.joinpoint import is_intercepted, get_intercepted, \
    _apply_interception, get_function, _unapply_interception, get_joinpoint

from types import MethodType, FunctionType


class GetFunctionTest(TestCase):

    def test_builtin(self):
        _max = get_function(max)

        self.assertIs(_max, max)

    def test_method(self):
        class A:
            def method(self):
                pass

        A_function = get_function(A.method)

        self.assertIs(A_function, A.method.im_func)

        a = A()

        a_function = get_function(a.method)

        self.assertIs(a_function, a.method.im_func)
        self.assertIs(A_function, a_function)

    def test_function(self):

        def function():
            pass

        a_function = get_function(function)

        self.assertIs(a_function, function)


class ApplyInterceptionTest(TestCase):

    def test_function(self, interception=None, function=None):
        if function is None:
            def function():
                pass

        func_code = function.__code__

        self.assertFalse(is_intercepted(function), 'check joinpoint')
        self.assertIs(get_intercepted(min), None)

        if interception is None:
            interception, intercepted = _apply_interception(
                function, lambda x: None)

        self.assertTrue(isinstance(interception, FunctionType), 'check type')

        self.assertIs(interception, function, 'check update')
        self.assertIs(get_intercepted(function), intercepted)
        self.assertTrue(is_intercepted(function), 'check joinpoint')
        self.assertIsNot(interception.__code__, func_code, 'check __code__')
        self.assertIs(intercepted.__code__, func_code, 'check __code__')

        _unapply_interception(function)

        self.assertFalse(is_intercepted(function), 'check is jointpoint')
        self.assertIs(interception, function, 'check update')
        self.assertIs(function.__code__, func_code, 'check update')
        self.assertIsNone(get_intercepted(function))

    def test_method(self):
        class A(object):
            def method(self):
                pass

        self.assertIsNone(get_intercepted(A.method))
        self.assertFalse(is_intercepted(A.method))

        interception, intercepted = _apply_interception(A.method, lambda: None)

        self.assertTrue(
            isinstance(get_joinpoint(interception), MethodType), 'check type')

        self.assertTrue(is_intercepted(interception), 'check joinpoint')
        self.assertIsNot(interception, A.method)  # TODO: check why false xD
        self.assertIs(get_intercepted(A.method), intercepted)

        _unapply_interception(A.method)

        self.assertFalse(is_intercepted(interception), 'check not joinpoint')
        self.assertIsNone(get_intercepted(A.method))

    def test_builtin(self):

        function = min

        self.assertIsNone(get_intercepted(min))
        self.assertFalse(is_intercepted(min))

        interception, intercepted = _apply_interception(min, lambda: None)

        self.assertTrue(isinstance(interception, FunctionType), "check type")

        self.assertTrue(is_intercepted(min), "check joinpoint")
        self.assertIs(interception, min, 'check update reference')
        self.assertIsNot(min, function, 'check update reference')
        self.assertIs(get_intercepted(min), intercepted)

        _unapply_interception(interception)

        self.assertFalse(is_intercepted(min), 'check joinpoint')
        self.assertIsNot(interception, min, 'check update reference')
        self.assertIs(min, function, 'check update reference')
        self.assertIsNone(get_intercepted(min))

    def test_class(self):

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertIsNone(get_intercepted(ApplyInterceptionTest))

        interception, intercepted = _apply_interception(
            ApplyInterceptionTest, lambda: None)

        self.assertTrue(isinstance(ApplyInterceptionTest, type))

        self.assertTrue(is_intercepted(ApplyInterceptionTest))
        self.assertIs(get_joinpoint(interception), ApplyInterceptionTest)
        self.assertIs(get_intercepted(ApplyInterceptionTest), intercepted)

        _unapply_interception(interception)

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertIsNone(get_intercepted(ApplyInterceptionTest))


if __name__ == '__main__':
    main()
