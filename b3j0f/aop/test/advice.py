#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main

from b3j0f.aop.advice import AdvicesExecutor, Advice, weave


class AdvicesExecutionTest(TestCase):

    def test_execution(self):

        def a():
            return 2

        je = AdvicesExecutor(joinpoint=a)

        result = je.execute()

        self.assertEquals(result, 2, 'check AdvicesExecutor proceed')

        def advice(_jpe):
            proceed = _jpe.execute()

            return proceed, 3

        je.advices = [advice]

        result = je()

        self.assertEquals(result, (2, 3), 'check AdvicesExecutor proceed')


class AdviceTest(TestCase):

    def setUp(self):
        self.advice = Advice(lambda x: 2)

    def test_apply(self):
        self.assertEquals(self.advice.apply(None), 2)

    def test_enable(self):
        self.assertEquals(self.advice.enable, True)
        pass


class WeaveTest(TestCase):

    def setUp(self):
        self.count = 0

    def advicesexecutor(self, advicesexecutor):
        self.count += 1

    def _test_method(self):
        class A():
            def __init__(self):
                pass

            def a(self):
                pass

        weave(
            joinpoint=A.a,
            advices=[self.advicesexecutor, self.advicesexecutor],
            sort=True)
        weave(A.__init__, self.advicesexecutor)
        weave(A, self.advicesexecutor, '__init__')

        a = A()
        a.a()

        self.assertEqual(self.count, 4)

    def test_function(self):

        def f():
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor],
            ordered=True)

        weave(
            joinpoint=f,
            advices=self.advicesexecutor,
            ordered=True)

        f()

        self.assertEqual(self.count, 3)

    def test_class(self):

        class A(object):
            class B(object):
                def b():
                    pass

            def __init__(self):
                pass

            def a(self):
                pass

        weave(A, self.advicesexecutor, '__init__')
        weave(A, [self.advicesexecutor, self.advicesexecutor])

        a = A()
        a.a()

        self.assertEqual(self.count, 3)

if __name__ == '__main__':
    main()
