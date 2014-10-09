#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main

from b3j0f.aop.advice import AdvicesExecutor, Advice, weave


class AdvicesExecutionTest(TestCase):

    def setUp(self):

        def a():
            return 2

        self.je = AdvicesExecutor(joinpoint=a)

    def test_execution(self):

        result = self.je.execute()

        self.assertEqual(result, 2, 'check AdvicesExecutor proceed')

    def test_add_advices(self):

        def advice(jpe):

            proceed = jpe.execute()

            return proceed, 3

        self.je.advices = [advice]

        result = self.je()

        self.assertEqual(result, (2, 3), 'check AdvicesExecutor proceed')


class AdviceTest(TestCase):

    def setUp(self):

        self.advice = Advice(impl=lambda x: 2)

    def test_apply(self):

        self.assertEqual(self.advice.apply(None), 2)

    def test_enable(self):

        self.assertEqual(self.advice.enable, True)


class WeaveTest(TestCase):

    def setUp(self):

        self.count = 0

    def advicesexecutor(self, advicesexecutor):
        """
        Default interceptor which increments self count
        """

        self.count += 1
        return advicesexecutor.execute()

    def test_method(self):

        class A():
            def __init__(self):
                pass

            def a(self):
                pass

        weave(
            joinpoint=A.a,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(joinpoint=A.__init__, advices=self.advicesexecutor)
        weave(joinpoint=A, advices=self.advicesexecutor, pointcut='__init__')

        a = A()
        a.a()

        self.assertEqual(self.count, 4)

    def test_function(self):

        def f(*args):
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)
        f()

        self.assertEqual(self.count, 3)

    def _assert_class(self, cls):
        """
        Run assertion tests on input cls
        """

        weave(joinpoint=cls, advices=self.advicesexecutor, pointcut='__init__')
        weave(
            joinpoint=cls,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(joinpoint=cls.B,
            advices=self.advicesexecutor, pointcut='__init__')
        weave(
            joinpoint=cls.B,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=cls.C, advices=self.advicesexecutor, pointcut='__init__')
        weave(
            joinpoint=cls.C,
            advices=[self.advicesexecutor, self.advicesexecutor])

        cls()
        cls.B()
        cls.C()

        self.assertEqual(self.count, 6)

    def test_class(self):

        class A(object):

            class B(object):
                def __init__(self):
                    pass

            class C(object):
                pass

            def __init__(self):
                pass

        self._assert_class(A)

    def test_namespace(self):

        class A:

            class B:
                def __init__(self):
                    pass

            class C:
                pass

            def __init__(self):
                pass

        self._assert_class(A)


if __name__ == '__main__':
    main()
