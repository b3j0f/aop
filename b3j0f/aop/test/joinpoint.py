#!/usr/bin/env python
# -*- coding: utf-8 -*-


from unittest import TestCase, main

from b3j0f.aop.joinpoint import is_intercepted, get_intercepted, \
    _apply_interception, get_function, _unapply_interception, get_joinpoint

from types import MethodType, FunctionType


class GetFunctionTest(TestCase):

    def test_builtin(self):
        _max = get_function(max)

        self.assertIs(_max, None)

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
        self.assertTrue(get_intercepted(min) is None)

        if interception is None:
            interception, intercepted = _apply_interception(
                function, lambda x: None)

        self.assertTrue(isinstance(interception, FunctionType), 'check type')

        self.assertTrue(interception is function, 'check update')
        self.assertTrue(get_intercepted(function) is intercepted)
        self.assertTrue(is_intercepted(function), 'check joinpoint')
        self.assertFalse(interception.__code__ is func_code, 'check __code__')
        self.assertTrue(intercepted.__code__ is func_code, 'check __code__')

        _unapply_interception(function)

        self.assertFalse(is_intercepted(function), 'check is jointpoint')
        self.assertTrue(interception is function, 'check update')
        self.assertTrue(function.__code__ is func_code, 'check update')
        self.assertTrue(get_intercepted(function) is None)

    def test_method(self):
        class A(object):
            def method(self):
                pass

        self.assertTrue(get_intercepted(A.method) is None)
        self.assertFalse(is_intercepted(A.method))

        interception, intercepted = _apply_interception(A.method, lambda: None)

        self.assertTrue(
            isinstance(get_joinpoint(interception), MethodType), 'check type')

        self.assertTrue(is_intercepted(interception), 'check joinpoint')
        self.assertFalse(interception is A.method)  # TODO: check why false xD
        self.assertTrue(get_intercepted(A.method) is intercepted)

        _unapply_interception(A.method)

        self.assertFalse(is_intercepted(interception), 'check not joinpoint')
        self.assertTrue(get_intercepted(A.method) is None)

    def test_builtin(self):

        function = min

        self.assertTrue(get_intercepted(min) is None)
        self.assertFalse(is_intercepted(min))

        interception, intercepted = _apply_interception(min, lambda: None)

        self.assertTrue(isinstance(interception, FunctionType), "check type")

        self.assertTrue(is_intercepted(min), "check joinpoint")
        self.assertTrue(interception is min, 'check update reference')
        self.assertFalse(min is function, 'check update reference')
        self.assertTrue(get_intercepted(min) is intercepted)

        _unapply_interception(interception)

        self.assertFalse(is_intercepted(min), 'check joinpoint')
        self.assertFalse(interception is min, 'check update reference')
        self.assertTrue(min is function, 'check update reference')
        self.assertTrue(get_intercepted(min) is None)

    def test_class(self):

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertTrue(get_intercepted(ApplyInterceptionTest) is None)

        interception, intercepted = _apply_interception(
            ApplyInterceptionTest, lambda: None)

        self.assertTrue(isinstance(ApplyInterceptionTest, type))

        self.assertTrue(is_intercepted(ApplyInterceptionTest))
        self.assertTrue(get_joinpoint(interception) is ApplyInterceptionTest)
        self.assertTrue(get_intercepted(ApplyInterceptionTest) is intercepted)

        _unapply_interception(interception)

        self.assertFalse(is_intercepted(ApplyInterceptionTest))
        self.assertTrue(get_intercepted(ApplyInterceptionTest) is None)


if __name__ == '__main__':
    main()
