#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from b3j0f.aspects.advice import JoinpointExecutor, Advice, weave


class JoinpointExecutionTest(unittest.TestCase):

    def test_execution(self):

        def a():
            return 2

        je = JoinpointExecutor(joinpoint=a)

        result = je()

        self.assertEquals(result, 2, 'check JoinpointExecutor proceed')

        def advice(_jpe):
            proceed = _jpe()

            return proceed, 3

        je.advices = [advice]

        result = je()

        self.assertEquals(result, (2, 3), 'check JoinpointExecutor proceed')


class AdviceTest(unittest.TestCase):

    def setUp(self):
        self.advice = Advice(lambda x: 2)

    def test_apply(self):
        self.assertEquals(self.advice.apply(None), 2)

    def test_enable(self):
        self.assertEquals(self.advice.enable, True)
        pass


class WeaveTest(unittest.TestCase):

    def setUp(self):
        self.count = 0

    def jpe(self, jpe):
        self.count += 1

    def test_method(self):
        class A():
            def __init__(self):
                pass

            def a(self):
                pass

        weave(A.a, [self.jpe, self.jpe])
        weave(A.__init__, self.jpe)
        weave(A, self.jpe, '__init__')

        a = A()
        a.a()

        self.assertEqual(self.count, 4)

    def test_function(self):

        def f():
            pass

        weave(f, [self.jpe, self.jpe])
        weave(f, self.jpe)

        f()

        self.assertEqual(self.count, 3)

    def test_class(self):

        class A:
            class B(object):
                def b():
                    pass

            def __init__(self):
                pass

            def a(self):
                pass

        weave(A, self.jpe, '__init__')
        weave(A, [self.jpe, self.jpe])

        a = A()
        a.a()

        self.assertEqual(self.count, 3)
