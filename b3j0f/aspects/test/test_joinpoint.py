#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest

from b3j0f.aspects.joinpoint import _get_joinpoint_function, \
    _apply_interception, _JOINPOINT, _unapply_interception, is_joinpoint

from types import MethodType, FunctionType


class GetJoinpointFunctionTest(unittest.TestCase):

    def test_builtin(self):
        _max = _get_joinpoint_function(max)

        self.assertTrue(_max is None)

    def test_method(self):
        class A:
            def method(self):
                pass

        A_function = _get_joinpoint_function(
            A.method)

        self.assertTrue(
            A_function is A.method.im_func)

        a = A()

        a_function = _get_joinpoint_function(a.method)

        self.assertTrue(a_function is a.method.im_func)
        self.assertTrue(A_function is a_function)

    def test_function(self):

        def function():
            pass

        a_function = _get_joinpoint_function(function)

        self.assertTrue(a_function is function)


class ApplyInterceptionTest(unittest.TestCase):

    def test_function(self, interception=None, function=None):
        if function is None:
            def function():
                pass

        __code__ = function.__code__

        if interception is None:
            interception = _apply_interception(
                function, lambda: None)

        self.assertTrue(type(interception) is FunctionType, 'check type')

        self.assertTrue(interception is function, 'check update')
        self.assertTrue(is_joinpoint(interception), 'check joinpoint')
        self.assertFalse(
            interception.__code__ is __code__, 'check __code__')
        self.assertTrue(
            getattr(interception, _JOINPOINT).__code__ is __code__,
            'check __code__')

        _unapply_interception(function)

        self.assertFalse(is_joinpoint(interception), 'check is jointpoint')
        self.assertTrue(interception is function, 'check update')
        self.assertTrue(function.__code__ is __code__, 'check update')

    def test_method(self):
        class A(object):
            def method(self):
                pass

        interception = _apply_interception(
            A.method, lambda: None)

        self.assertTrue(type(interception) is MethodType, 'check type')

        self.assertTrue(is_joinpoint(interception), 'check joinpoint')
        self.assertFalse(interception is A.method)  # TODO: check why false xD

        _unapply_interception(A.method)

        self.assertFalse(is_joinpoint(interception), 'check not joinpoint')

    def test_builtin(self):

        function = min

        interception = _apply_interception(
            min, lambda: None)

        self.assertTrue(type(interception) is FunctionType, "check type")

        self.assertTrue(is_joinpoint(interception), "check joinpoint")
        self.assertTrue(interception is min, 'check update reference')
        self.assertFalse(min is function, 'check update reference')

        _unapply_interception(interception)

        self.assertFalse(is_joinpoint(interception), 'check joinpoint')
        self.assertFalse(interception is min, 'check update reference')
        self.assertTrue(min is function, 'check update reference')

if __name__ == '__main__':
    unittest.main()
