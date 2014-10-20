#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import main

from b3j0f.utils.ut import UTCase
from b3j0f.aop.advice import AdvicesExecutor, Advice, weave, unweave, weave_on

from time import sleep


class AdvicesExecutionTest(UTCase):

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


class AdviceTest(UTCase):

    def setUp(self):

        self.advice = Advice(impl=lambda x: 2)

    def test_apply(self):

        self.assertEqual(self.advice.apply(None), 2)

    def test_enable(self):

        self.assertEqual(self.advice.enable, True)


class WeaveTest(UTCase):

    def setUp(self):

        self.count = 0

    def advicesexecutor(self, advicesexecutor):
        """
        Default interceptor which increments self count
        """

        self.count += 1
        return advicesexecutor.execute()

    def test_builtin(self):

        weave(
            joinpoint=min,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(joinpoint=min, advices=self.advicesexecutor)

        min(5, 2)

        self.assertEqual(self.count, 3)

        unweave(min)

        min(5, 2)

        self.assertEqual(self.count, 3)

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

        unweave(A.a)
        unweave(A)

        A()
        a.a()

        self.assertEqual(self.count, 4)

    def test_function(self):

        def f():
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)
        f()

        self.assertEqual(self.count, 3)

        unweave(f)

        f()

        self.assertEqual(self.count, 3)

    def test_function_args(self):

        def f(a):
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)
        f(1)

        self.assertEqual(self.count, 3)

        unweave(f)

        f(1)

        self.assertEqual(self.count, 3)

    def test_function_varargs(self):

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

        unweave(f)

        f()

        self.assertEqual(self.count, 3)

    def test_function_args_varargs(self):

        def f(a, **args):
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)

        f(1)

        self.assertEqual(self.count, 3)

        unweave(f)

        f(1)

        self.assertEqual(self.count, 3)

    def test_function_kwargs(self):

        def f(**kwargs):
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)
        f()

        self.assertEqual(self.count, 3)

        unweave(f)

        f()

        self.assertEqual(self.count, 3)

    def test_function_args_kwargs(self):

        def f(a, **args):
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)
        f(1)

        self.assertEqual(self.count, 3)

        unweave(f)

        f(1)

        self.assertEqual(self.count, 3)

    def test_function_args_varargs_kwargs(self):

        def f(a, *args, **kwargs):
            pass

        weave(
            joinpoint=f,
            advices=[self.advicesexecutor, self.advicesexecutor])
        weave(
            joinpoint=f,
            advices=self.advicesexecutor)
        f(1)

        self.assertEqual(self.count, 3)

        unweave(f)

        f(1)

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

        unweave(cls)

        cls()

        self.assertEqual(self.count, 6)

        unweave(cls.B)

        cls.B()

        self.assertEqual(self.count, 6)

        unweave(cls.C)

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

    def test_ttl(self):

        def test():
            pass

        weave(joinpoint=test, advices=self.advicesexecutor, ttl=0.1)

        test()

        sleep(0.2)

        test()

        self.assertEqual(self.count, 1)

    def test_cancel_ttl(self):

        def test():
            pass

        _, timer = weave(joinpoint=test, advices=self.advicesexecutor, ttl=0.1)

        timer.cancel()

        sleep(0.2)

        test()

        self.assertEqual(self.count, 1)


class WeaveOnTest(UTCase):

    def setUp(self):

        self.count = 0

    def advicesexecutor(self, advicesexecutor):
        """
        Default interceptor which increments self count
        """

        self.count += 1
        return advicesexecutor.execute()

    def test_builtin(self):

        weave_on(advices=[self.advicesexecutor, self.advicesexecutor])(min)
        weave_on(advices=self.advicesexecutor)(min)

        min(5, 2)

        self.assertEqual(self.count, 3)

        unweave(min)

        min(5, 2)

        self.assertEqual(self.count, 3)

    def test_method(self):

        @weave_on(self.advicesexecutor, pointcut='__init__')
        class A():

            @weave_on(self.advicesexecutor)
            def __init__(self):
                pass

            @weave_on([self.advicesexecutor, self.advicesexecutor])
            def a(self):
                pass

        a = A()
        a.a()

        self.assertEqual(self.count, 4)

    def test_function(self):

        @weave_on(self.advicesexecutor)
        @weave_on([self.advicesexecutor, self.advicesexecutor])
        def f():
            pass

        f()

        self.assertEqual(self.count, 3)

    def test_function_args(self):

        @weave_on(self.advicesexecutor)
        @weave_on([self.advicesexecutor, self.advicesexecutor])
        def f(a):
            pass

        f(1)

        self.assertEqual(self.count, 3)

    def test_function_varargs(self):

        @weave_on(self.advicesexecutor)
        @weave_on([self.advicesexecutor, self.advicesexecutor])
        def f(*args):
            pass

        f()

        self.assertEqual(self.count, 3)

    def test_function_args_varargs(self):

        @weave_on(self.advicesexecutor)
        @weave_on([self.advicesexecutor, self.advicesexecutor])
        def f(a, **args):
            pass

        f(1)

        self.assertEqual(self.count, 3)

    def test_function_kwargs(self):

        @weave_on([self.advicesexecutor, self.advicesexecutor])
        @weave_on(self.advicesexecutor)
        def f(**kwargs):
            pass

        f()

        self.assertEqual(self.count, 3)

    def test_function_args_kwargs(self):

        @weave_on(self.advicesexecutor)
        @weave_on([self.advicesexecutor, self.advicesexecutor])
        def f(a, **args):
            pass

        f(1)

        self.assertEqual(self.count, 3)

    def test_function_args_varargs_kwargs(self):

        @weave_on(self.advicesexecutor)
        @weave_on([self.advicesexecutor, self.advicesexecutor])
        def f(a, *args, **kwargs):
            pass

        f(1)

        self.assertEqual(self.count, 3)

    def _assert_class(self, cls):
        """
        Run assertion tests on input cls
        """

        weave_on(advices=self.advicesexecutor, pointcut='__init__')(cls)
        weave_on(advices=[self.advicesexecutor, self.advicesexecutor])(cls)
        weave_on(advices=self.advicesexecutor, pointcut='__init__')(cls.B)
        weave_on(advices=[self.advicesexecutor, self.advicesexecutor])(cls.B)
        weave_on(advices=self.advicesexecutor, pointcut='__init__')(cls.C)
        weave_on(advices=[self.advicesexecutor, self.advicesexecutor])(cls.C)

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
