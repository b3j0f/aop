#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest

from b3j0f.aspects.joinpoint import is_intercepted, get_intercepted, \
    _apply_interception, _function, _unapply_interception

from types import MethodType, FunctionType


class GetFunctionTest(unittest.TestCase):

    def test_builtin(self):
        _max = _function(max)

        self.assertTrue(_max is _max)

    def test_method(self):
        class A:
            def method(self):
                pass

        A_function = _function(A.method)

        self.assertTrue(
            A_function is A.method.im_func)

        a = A()

        a_function = _function(a.method)

        self.assertTrue(a_function is a.method.im_func)
        self.assertTrue(A_function is a_function)

    def test_function(self):

        def function():
            pass

        a_function = _function(function)

        self.assertTrue(a_function is function)


class ApplyInterceptionTest(unittest.TestCase):

    def test_function(self, interception=None, function=None):
        if function is None:
            def function():
                pass

        func_code = function.__code__

        if interception is None:
            interception, intercepted = _apply_interception(function, lambda x: None)

        self.assertTrue(type(interception) is FunctionType, 'check type')

        self.assertTrue(interception is function, 'check update')

        self.assertTrue(is_intercepted(function), 'check joinpoint')
        self.assertFalse(interception.__code__ is func_code, 'check __code__')
        self.assertTrue(intercepted.__code__ is func_code, 'check __code__')

        _unapply_interception(function)

        self.assertFalse(is_intercepted(function), 'check is jointpoint')
        self.assertTrue(interception is function, 'check update')
        self.assertTrue(function.__code__ is func_code, 'check update')

    def test_method(self):
        class A(object):
            def method(self):
                pass

        interception = _apply_interception(A.method, lambda: None)

        self.assertTrue(type(interception) is MethodType, 'check type')

        self.assertTrue(is_intercepted(interception), 'check joinpoint')
        self.assertFalse(interception is A.method)  # TODO: check why false xD

        _unapply_interception(A.method)

        self.assertFalse(is_intercepted(interception), 'check not joinpoint')

    def test_builtin(self):

        function = min

        interception, intercepted = _apply_interception(min, lambda: None)

        self.assertTrue(type(interception) is FunctionType, "check type")

        self.assertTrue(is_intercepted(min), "check joinpoint")
        self.assertTrue(interception is min, 'check update reference')
        self.assertFalse(min is function, 'check update reference')

        _unapply_interception(interception)

        self.assertFalse(is_intercepted(min), 'check joinpoint')
        self.assertFalse(interception is min, 'check update reference')
        self.assertTrue(min is function, 'check update reference')

if __name__ == '__main__':
    unittest.main()
