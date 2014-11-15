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
    put_property, setdefault, get_first_property, del_properties, find_ctx
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

_ADVICES = '_advices'  #: joinpoint advices attribute name


class AdviceError(Exception):
    """
    Handle Advice errors
    """

    pass


class _Joinpoint(Joinpoint):
    """
    Manage joinpoint execution with Advices.

    Advices are callable objects which take in parameter a Joinpoint.

    Joinpoint provides to advices:
        - the joinpoint,
        - joinpoint call arguments as args and kwargs property,
        - a shared context during interception such as a dictionary.
    """

    def get_advices(self, target):

        result = get_advices(target)

        return result


def _add_advices(joinpoint, advices):
    """
    Add advices on input joinpoint.

    :param joinpoint joinpoint: joinpoint from where add advices
    :param advices advices: advices to weave on input joinpoint
    :param bool ordered: ensure advices to add will be done in input order
    """

    joinpoint_advices = setdefault(joinpoint, key=_ADVICES, default=[])

    for advice in advices:
        joinpoint_advices.append(advice)

    put_property(joinpoint, key=_ADVICES, value=joinpoint_advices)


def _remove_advices(joinpoint, advices, container):
    """
    Remove advices from input joinpoint.

    :param advices: advices to remove. If None, remove all advices.
    """

    joinpoint_advices = get_first_property(joinpoint, key=_ADVICES, default=[])

    if advices is not None:
        joinpoint_advices = list(
            advice for advice in joinpoint_advices if advice not in advices)

    else:
        joinpoint_advices = ()

    if joinpoint_advices:  # update joinpoint advices
        put_property(joinpoint, key=_ADVICES, value=joinpoint_advices)

    else:  # free joinpoint advices if necessary
        del_properties(joinpoint, keys=_ADVICES)
        _unapply_interception(joinpoint, container=container)


def get_advices(element):
    """
    Get element advices.

    None if element is not a joinpoint.
    """

    result = None

    if is_intercepted(element):

        joinpoint_function = _get_function(element)

        if joinpoint_function is not None:
            result = setdefault(joinpoint_function, key=_ADVICES, default=())

        result = tuple(result)

    return result


def _namematcher(regex):
    """
    Checks if a joinpoint name matches with an input regular expression
    """

    matcher = re_compile(regex)

    def match(joinpoint):
        joinpoint_name = getattr(joinpoint, '__name__', '')
        result = matcher.match(joinpoint_name)
        return result

    return match


def _publicmembers(joinpoint):

    return callable(joinpoint) \
            and not getattr(joinpoint, '__name__', '').startswith('_')


def weave(
    joinpoint, advices, pointcut=None, container=None, depth=1, public=False,
    pointcut_application=None, ttl=None
):
    """
    Weave advices on joinpoint with input pointcut.

    :param callable joinpoint: joinpoint from where checking pointcut and
        weaving advices.
    :param advices: advices to weave on joinpoint.
    :param container: joinpoint container (class or instance).
    :param pointcut: condition for weaving advices on joinpointe.
        The condition depends on its type.
    :type pointcut:
        - NoneType: advices are weaved on joinpoint.
        - str: joinpoint name is compared to pointcut regex.
        - function: called with joinpoint in parameter, if True, advices will
            be weaved on joinpoint.
    :param int depth: class weaving depthing
    :param bool public: (default True) weave only on public members
    :param routine pointcut_application: routine which applies a pointcut when
        required. Joinpoint().apply_pointcut by default. Such routine has
        to take in parameters a routine called joinpoint and its related
        function called function. Its result is the interception function.
    :param float ttl: time to leave for weaved advices.

    :return: the intercepted functions created from input joinpoint or a tuple
        with intercepted functions and ttl timer.
    :rtype: list
    """

    if pointcut_application is None:
        pointcut_application = Joinpoint().apply_pointcut

    # initialize advices
    advices = ensureiterable(advices, iterable=list)

    # check for not empty advices
    if not advices:
        raise AdviceError(
            "No one advice to weave on input joinpoint {0}".format(joinpoint))

    # initialize pointcut

    # do nothing if pointcut is None or is callable
    if pointcut is None or callable(pointcut):
        pass

    # in case of str, use a name matcher
    elif isinstance(pointcut, basestring):
        pointcut = _namematcher(pointcut)

    else:
        error_msg = "Wrong pointcut to check weaving on {0}.".format(joinpoint)
        advice_msg = "Must be None, or be a str or a function/method."
        right_msg = "Not {1}".format(type(pointcut))

        raise AdviceError(
            "{0} {1} {2}".format(error_msg, advice_msg, right_msg))

    result = []

    if container is None:
        container = find_ctx(container, joinpoint)

    _weave(
        joinpoint=joinpoint, advices=advices, pointcut=pointcut,
        container=container, depth=depth,
        depth_predicate=_publicmembers if public else callable,
        intercepted=result, pointcut_application=pointcut_application)

    if ttl is not None:
        kwargs = {
            'joinpoint': joinpoint,
            'advices': advices,
            'pointcut': pointcut,
            'depth': depth,
            'public': public
        }
        timer = Timer(ttl, unweave, kwargs=kwargs)
        timer.start()

        result = result, timer

    return result


def _weave(
    target, advices, pointcut, container, depth, depth_predicate,
    intercepted, pointcut_application, ctx
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
                interception_function = pointcut_application(
                    target=target, function=interception_function,
                    container=container)
            # add advices to the interception function

            _add_advices(target=interception_function, advices=advices)

            # append interception function to the intercepted ones
            intercepted.append(interception_function)

    # search inside the target
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(target, depth_predicate):
            _weave(
                target=member, advices=advices, pointcut=pointcut,
                container=target,
                depth=depth - 1, depth_predicate=depth_predicate,
                intercepted=intercepted,
                pointcut_application=pointcut_application)


def unweave(
    target, advices=None, pointcut=None, container=None,
    depth=1, public=False,
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

    :param container: target container (class or instance).
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

    # get the right container
    if container is None:
        container = find_ctx(container, target)

    _unweave(
        target=target, advices=advices, pointcut=pointcut,
        container=container,
        depth=depth, depth_predicate=_publicmembers if public else callable)


def _unweave(
    target, advices, pointcut, container, depth, depth_predicate, ctx
):
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
                    container=container)

    # search inside the target
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(target, depth_predicate):
            _unweave(
                target=member, advices=advices, pointcut=pointcut,
                container=target,
                depth=depth - 1, depth_predicate=depth_predicate)


def weave_on(advices, pointcut=None, container=None, depth=1, ttl=None):
    """
    Decorator for weaving advices on a callable joinpoint.

    :param pointcut: condition for weaving advices on joinpointe.
        The condition depends on its type.
    :param container: joinpoint container (instance or class).
    :type pointcut:
        - NoneType: advices are weaved on joinpoint.
        - str: joinpoint name is compared to pointcut regex.
        - function: called with joinpoint in parameter, if True, advices will
            be weaved on joinpoint.

    :param depth: class weaving depthing
    :type depth: int

    :param public: (default True) weave only on public members
    :type public: bool
    """

    def _weave(target):
        weave(
            target=target, advices=advices, pointcut=pointcut,
            container=container, depth=depth, ttl=ttl)
        return target

    return _weave


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
    def uuid(self):
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

    def apply(self, advicesexecutor):
        """
        Apply this advice on input advicesexecutor.

        TODO: improve with internal methods instead of conditional test.
        """

        if self._enable:
            result = self._impl(advicesexecutor)
        else:
            result = advicesexecutor.execute()

        return result

    @staticmethod
    def set_enable(joinpoint, enable=True, advice_ids=None):
        """
        Enable or disable all joinpoint Advices designated by input advice_ids.

        If advice_ids is None, apply (dis|en)able state to all advices.
        """

        advices = get_advices(joinpoint)

        for advice in advices:
            try:
                if isinstance(Advice) \
                        and (advice_ids is None or advice.uuid in advice_ids):
                    advice.enable = enable
            except ValueError:
                pass

    @staticmethod
    def weave(joinpoint, advices, pointcut=None, depth=1, public=False):
        """
        Weave advices such as Advice objects.
        """

        advices = (advice if isinstance(advice, Advice) else Advice(advice)
            for advice in advices)

        weave(
            joinpoint=joinpoint, advices=advices, pointcut=pointcut,
            depth=depth, public=public)

    @staticmethod
    def unweave(joinpoint, *advices):
        """
        Unweave advices from input joinpoint.
        """

        advices = (advice if isinstance(advice, Advice) else Advice(advice)
            for advice in advices)

        unweave(joinpoint=joinpoint, *advices)

    def __call__(self, advicesexecutor):

        return self.apply(advicesexecutor)

    def __hash__(self):
        """
        Return self uuid hash.
        """

        result = hash(self._uid)

        return result

    def __eq__(self, other):
        """
        Compare with self uuid.
        """

        result = isinstance(other, Advice) and other._uid == self._uid

        return result
