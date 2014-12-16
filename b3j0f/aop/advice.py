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

"""
Provides functions in order to weave/unweave/get advices from callable objects.
"""

from re import compile as re_compile

from uuid import uuid4 as uuid

from inspect import (
    getmembers, isroutine
)

from opcode import opmap

try:
    from threading import Timer
except ImportError:
    from dummy_threading import Timer

from b3j0f.aop.joinpoint import (
    get_intercepted, _apply_interception,
    _unapply_interception, is_intercepted, _get_function,
    Joinpoint
)
from b3j0f.utils.version import basestring
from b3j0f.utils.iterable import ensureiterable
from b3j0f.utils.property import (
    put_property, setdefault, get_local_property, del_properties, get_property,
    find_ctx, remove_ctx, get_first_property
)

__all__ = [
    'AdviceError', 'get_advices',
    'weave', 'unweave', 'weave_on',
    'Advice'
]

# consts for interception loading
LOAD_GLOBAL = opmap['LOAD_GLOBAL']
LOAD_CONST = opmap['LOAD_CONST']

WRAPPER_ASSIGNMENTS = ('__doc__', '__annotations__', '__dict__', '__module__')

_ADVICES = '_advices'  #: target advices attribute name


class AdviceError(Exception):
    """
    Handle Advice errors
    """

    pass


class _Joinpoint(Joinpoint):
    """
    Manage target execution with Advices.

    Advices are callable objects which take in parameter a Joinpoint.

    Joinpoint provides to advices:
        - the target,
        - target call arguments as args and kwargs property,
        - a shared context during interception such as a dictionary.
    """

    def get_advices(self, target):

        result = get_advices(target)

        return result


def _add_advices(target, advices, ctx):
    """
    Add advices on input target.

    :param Callable target: target from where add advices.
    :param advices: advices to weave on input target.
    :type advices: routine or list.
    :param bool ordered: ensure advices to add will be done in input order
    """

    joinpoint_advices = setdefault(target, key=_ADVICES, default=[], ctx=ctx)

    if isroutine(advices):
        advices = [advices]

    joinpoint_advices += advices

    put_property(target, key=_ADVICES, value=joinpoint_advices, ctx=ctx)


def _remove_advices(target, advices, ctx):
    """
    Remove advices from input target.

    :param advices: advices to remove. If None, remove all advices.
    """

    target_advices = get_local_property(
        target, key=_ADVICES, ctx=ctx)

    if target_advices is not None:

        if advices is not None:  # remove advices from target_advices
            target_advices = list(
                advice for advice in target_advices if advice not in advices)

        else:
            target_advices = ()

        if target_advices:  # update target advices
            put_property(target, key=_ADVICES, value=target_advices, ctx=ctx)

        else:  # free target advices if necessary
            del_properties(target, keys=_ADVICES, ctx=ctx)
            _unapply_interception(target, ctx=ctx)


def get_advices(target, ctx=None):
    """
    Get element advices.

    None if element is not a target.
    """

    result = get_first_property(target, ctx=ctx, key=_ADVICES, default=[])

    return result


def _namematcher(regex):
    """
    Checks if a target name matches with an input regular expression
    """

    matcher = re_compile(regex)

    def match(target):
        target_name = getattr(target, '__name__', '')
        result = matcher.match(target_name)
        return result

    return match


def _publiccallable(target):
    """
    :return: True iif target is callable and name does not start with '_'
    """

    result = callable(target) \
        and not getattr(target, '__name__', '').startswith('_')

    return result


def weave(
    target, advices, pointcut=None, ctx=None, depth=1, public=False,
    pointcut_application=None, ttl=None
):
    """
    Weave advices on target with input pointcut.

    :param callable target: target from where checking pointcut and
        weaving advices.
    :param advices: advices to weave on target.
    :param ctx: target ctx (class or instance).
    :param pointcut: condition for weaving advices on joinpointe.
        The condition depends on its type.
    :type pointcut:
        - NoneType: advices are weaved on target.
        - str: target name is compared to pointcut regex.
        - function: called with target in parameter, if True, advices will
            be weaved on target.
    :param int depth: class weaving depthing
    :param bool public: (default True) weave only on public members
    :param routine pointcut_application: routine which applies a pointcut when
        required. _Joinpoint().apply_pointcut by default. Such routine has
        to take in parameters a routine called target and its related
        function called function. Its result is the interception function.
    :param float ttl: time to leave for weaved advices.

    :return: the intercepted functions created from input target or a tuple
        with intercepted functions and ttl timer.
    :rtype: list
    """

    # initialize advices
    advices = ensureiterable(advices, iterable=list)

    # check for not empty advices
    if not advices:
        raise AdviceError(
            "No one advice to weave on input target {0}".format(target))

    # initialize pointcut

    # do nothing if pointcut is None or is callable
    if pointcut is None or callable(pointcut):
        pass

    # in case of str, use a name matcher
    elif isinstance(pointcut, basestring):
        pointcut = _namematcher(pointcut)

    else:
        error_msg = "Wrong pointcut to check weaving on {0}.".format(target)
        advice_msg = "Must be None, or be a str or a function/method."
        right_msg = "Not {1}".format(type(pointcut))

        raise AdviceError(
            "{0} {1} {2}".format(error_msg, advice_msg, right_msg))

    result = []

    if ctx is None:
        ctx = find_ctx(elt=target)

    _weave(
        target=target, advices=advices, pointcut=pointcut,
        ctx=ctx, depth=depth,
        depth_predicate=_publiccallable if public else callable,
        intercepted=result, pointcut_application=pointcut_application)

    if ttl is not None:
        kwargs = {
            'target': target,
            'advices': advices,
            'pointcut': pointcut,
            'depth': depth,
            'public': public,
            'ctx': ctx
        }
        timer = Timer(ttl, unweave, kwargs=kwargs)
        timer.start()

        result = result, timer

    return result


def _weave(
    target, advices, pointcut, ctx, depth, depth_predicate,
    intercepted, pointcut_application
):
    """
    Weave deeply advices in target.
    """

    # if weaving has to be done
    if isroutine(target) and (pointcut is None or pointcut(target)):
        # get target interception function
        interception_function = _get_function(target)
        # does not handle not python functions
        if interception_function is not None:
            # intercept target if not intercepted
            if not is_intercepted(target):
                # instantiate a new joinpoint if pointcut_application is None
                if pointcut_application is None:
                    pointcut_application = _Joinpoint().apply_pointcut
                interception_function = pointcut_application(
                    target=target, function=interception_function,
                    ctx=ctx)
            # add advices to the interception function

            _add_advices(
                target=interception_function, advices=advices, ctx=ctx)

            # append interception function to the intercepted ones
            intercepted.append(interception_function)

    # search inside the target
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(target, depth_predicate):
            _weave(
                target=member, advices=advices, pointcut=pointcut,
                ctx=target,
                depth=depth - 1, depth_predicate=depth_predicate,
                intercepted=intercepted,
                pointcut_application=pointcut_application)


def unweave(
    target, advices=None, pointcut=None, ctx=None, depth=1, public=False,
):
    """
    Unweave advices on target with input pointcut.

    :param callable target: target from where checking pointcut and
        weaving advices.

    :param pointcut: condition for weaving advices on joinpointe.
        The condition depends on its type.
    :type pointcut:
        - NoneType: advices are weaved on target.
        - str: target name is compared to pointcut regex.
        - function: called with target in parameter, if True, advices will
            be weaved on target.

    :param ctx: target ctx (class or instance).
    :param int depth: class weaving depthing
    :param bool public: (default True) weave only on public members

    :return: the intercepted functions created from input target.
    """

    # ensure advices is a list if not None
    if advices is not None:

        advices = ensureiterable(advices, iterable=list)

    # initialize pointcut

    # do nothing if pointcut is None or is callable
    if pointcut is None or callable(pointcut):
        pass

    # in case of str, use a name matcher
    elif isinstance(pointcut, basestring):
        pointcut = _namematcher(pointcut)

    else:
        error_msg = "Wrong pointcut to check weaving on {0}.".format(target)
        advice_msg = "Must be None, or be a str or a function/method."
        right_msg = "Not {1}".format(type(pointcut))

        raise AdviceError(
            "{0} {1} {2}".format(error_msg, advice_msg, right_msg))

    # get the right ctx
    if ctx is None:
        ctx = find_ctx(ctx, target)

    _unweave(
        target=target, advices=advices, pointcut=pointcut,
        ctx=ctx,
        depth=depth, depth_predicate=_publiccallable if public else callable)


def _unweave(target, advices, pointcut, ctx, depth, depth_predicate):
    """
    Unweave deeply advices in target.
    """

    # if weaving has to be done
    if isroutine(target) and (pointcut is None or pointcut(target)):
        # get target interception function
        interception_function = _get_function(target)
        # does not handle not python functions
        if interception_function is not None:
            # intercept target if not intercepted
            if is_intercepted(target):
            # remove advices to the interception function
                _remove_advices(
                    target=interception_function,
                    advices=advices,
                    ctx=ctx)

    # search inside the target
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(target, depth_predicate):
            _unweave(
                target=member, advices=advices, pointcut=pointcut,
                ctx=target,
                depth=depth - 1, depth_predicate=depth_predicate)


def weave_on(advices, pointcut=None, ctx=None, depth=1, ttl=None):
    """
    Decorator for weaving advices on a callable target.

    :param pointcut: condition for weaving advices on joinpointe.
        The condition depends on its type.
    :param ctx: target ctx (instance or class).
    :type pointcut:
        - NoneType: advices are weaved on target.
        - str: target name is compared to pointcut regex.
        - function: called with target in parameter, if True, advices will
            be weaved on target.

    :param depth: class weaving depthing
    :type depth: int

    :param public: (default True) weave only on public members
    :type public: bool
    """

    def __weave(target):

        weave(
            target=target, advices=advices, pointcut=pointcut,
            ctx=ctx, depth=depth, ttl=ttl)

        return target

    return __weave


class Advice(object):
    """
    Advice class which aims to embed an advice function with disabling proprety
    """

    __slots__ = ('_impl', '_enable', '_uid')

    def __init__(self, impl, uid=None, enable=True):

        self._impl = impl
        self._enable = enable
        self._uid = uuid() if uid is None else uid

    @property
    def uid(self):
        return self._uid

    @property
    def enable(self):
        """
        Get self enable state. Change state if input enable is a boolean.

        TODO: change of method execution instead of saving a state.
        """

        return self._enable

    @enable.setter
    def enable(self, value):
        """
        Change of enable status.
        """

        self._enable = value

    def apply(self, joinpoint):
        """
        Apply this advice on input joinpoint.

        TODO: improve with internal methods instead of conditional test.
        """

        if self._enable:
            result = self._impl(joinpoint)
        else:
            result = joinpoint.proceed()

        return result

    @staticmethod
    def set_enable(target, enable=True, advice_ids=None):
        """
        Enable or disable all target Advices designated by input advice_ids.

        If advice_ids is None, apply (dis|en)able state to all advices.
        """

        advices = get_advices(target)

        for advice in advices:
            try:
                if isinstance(Advice) \
                        and (advice_ids is None or advice.uuid in advice_ids):
                    advice.enable = enable
            except ValueError:
                pass

    @staticmethod
    def weave(target, advices, pointcut=None, depth=1, public=False):
        """
        Weave advices such as Advice objects.
        """

        advices = (advice if isinstance(advice, Advice) else Advice(advice)
            for advice in advices)

        weave(
            target=target, advices=advices, pointcut=pointcut,
            depth=depth, public=public)

    @staticmethod
    def unweave(target, *advices):
        """
        Unweave advices from input target.
        """

        advices = (advice if isinstance(advice, Advice) else Advice(advice)
            for advice in advices)

        unweave(target=target, *advices)

    def __call__(self, joinpoint):
        """
        Shortcut for self apply.
        """
        return self.apply(joinpoint)

    def __hash__(self):
        """
        Return self uid hash.
        """

        result = hash(self._uid)

        return result

    def __eq__(self, other):
        """
        Compare with self uid.
        """

        result = isinstance(other, Advice) and other._uid == self._uid

        return result
