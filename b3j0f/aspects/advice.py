#!/usr/bin/env python
# -*- coding: utf-8 -*-


from re import compile as recompile

from uuid import uuid4 as uuid

from functools import wraps

from inspect import ismethod, isfunction, getmembers

from collections import Iterable

from .joinpoint import _get_interception_joinpoint, _apply_interception, \
    _unapply_interception, is_joinpoint, _get_joinpoint_function


class AdviceError(Exception):
        pass

_ADVICES = '_advices'


class JoinpointExecutor(object):
    """
    Manage joinpoint execution with Advices.

    Advices are callable objects which take in parameter a JoinpointExecutor.

    JoinpointExecutor provides to advices:
        - the intercepted joinpoint.
        - joinpoint call arguments as args and kwargs property.
        - a shared context during interception such as a dictionary.
    """

    __slots__ = (
        'context',  # context execution
        '_advices',  # advices
        '_joinpoint',  # joinpoint
        '_interception_joinpoint',  # interception joinpoint
        '_advices_iterator')  # internal iterator for advices execution

    def __init__(self, joinpoint, *advices):
        """
        Initialize a new JoinpointExecutor with a joinpoint,
        its calling arguments and a list of advices.

        :param joinpoint: joinpoint which is intercepted by input advices.
        :type joinpoint: callable

        :param advices: list of advices which could intercept input joinpoint.
            If None, they will be dynamically loaded during proceeding related
            to joinpoint.
        :type advices: list of callables
        """

        # set joinpoint
        self.joinpoint = joinpoint

        # set execution context
        self.context = {}

        self.advices = advices
        # force dynamic advices
        if not advices:
            self._advices_iterator = None

    @property
    def joinpoint(self):
        return self._joinpoint

    @joinpoint.setter
    def joinpoint(self, value):
        self._interception_joinpoint = value
        self._joinpoint = _get_interception_joinpoint(value)
        if self._joinpoint is None:
            self._joinpoint = value

    @property
    def advices(self):
        return self._advices

    @advices.setter
    def advices(self, value):
        self._advices = value
        self._advices_iterator = iter(value)

    def __call__(self, *args, **kwargs):
        """
        Proceed this JoinpointExecutor in calling all advices with this such
        as the only one parameter, and call at the end the joinpoint.
        """

        # check if an iterator is available
        if self._advices_iterator is None:
            # if not, get joinpoint advices
            advices = get_advices(self._interception_joinpoint)
            # and get the advices iterator
            self._advices_iterator = iter(advices if advices else [])

        try:
            # get next advice
            advice = self._advices_iterator.next()

        except StopIteration:
            # if no advice can be applied, call joinpoint
            return self._joinpoint(*args, **kwargs)

        else:
            # if has next, apply advice on self
            return advice(_jpe=self, *args, **kwargs)

    @staticmethod
    def _get_interception_function(joinpoint_function):
        """
        Get an interception function which executes a joinpoint execution.

        :param joinpoint_function: joinpoint_function from where weave advices
        :type joinpoint_function: function

        :return: function which call advices before calling input
            joinpoint_function
        :rtype: function
        """

        @wraps(joinpoint_function)
        def interception_function(*args, **kwargs):
            """
            Instantiate a JoinpointExecutor and proceeds it.
            """

            # get joinpointexecution from global scope
            # TODO: set joinpointexecution among consts or fast loading
            return joinpointexecution(*args, **kwargs)

        # add interception environment in interception globals
        interception_globals = {
            'joinpointexecution': JoinpointExecutor(
                joinpoint=joinpoint_function)
        }
        # update interception_function globals
        interception_function.func_globals.update(interception_globals)

        return interception_function


def _add_advices(joinpoint, *advices):
    """
    Add advices on input joinpoint.

    :param joinpoint: joinpoint from where add advices
    :type joinpoint: joinpoint

    :param advices: advices to weave on input joinpoint
    :type advices: advices
    """

    advices = get_advices(joinpoint)

    advices += advices


def _remove_advices(joinpoint, *advice_ids):
    """
    Remove advices from input element identified by advice_ids and \
    return removed ids.
    """

    result = []

    advices = get_advices(joinpoint)

    for advice in list(advices):

        try:
            advice_ids.remove(advice.uuid)
            result.append(advice.uuid)
            advices.remove(advice)

        except ValueError:
            pass

    return result


def _enable(joinpoint, enable, *advice_ids):
    """
    Enable or disable all joinpoint advices designated by input advice_ids.

    If advice_ids is empty, apply (dis|en)able state to all joinpoint advices.
    """

    advices = get_advices(joinpoint)

    _all = len(advice_ids) == 0

    for advice in advices:
        try:
            if _all or advice_ids.remove(advice.uuid):
                advice.enable = enable
        except ValueError:
            pass


def get_advices(element):
    """
    Get element advices.

    None if element is not a joinpoint.
    """

    result = None

    if is_joinpoint(element):

        joinpoint_function = _get_joinpoint_function(element)

        if joinpoint_function is not None:
            result = getattr(joinpoint_function, _ADVICES, None)

            if result is None:
                result = []
                setattr(joinpoint_function, _ADVICES, result)

    return result


class NameMatcher(object):
    """
    Checks if a joinpoint name matches with an input regular expression
    """
    __slots__ = ('name_matcher')

    def __init__(self, regex):
        super(NameMatcher, self).__init__()
        self.name_matcher = recompile(regex)

    def __call__(self, joinpoint):

        joinpoint_name = getattr(joinpoint, '__name__', '')
        result = self.name_matcher.match(joinpoint_name)

        return result


def _publicmembers(joinpoint):
    return callable(joinpoint) and not getattr(
        joinpoint, '__name__', '').startswith('_')


def weave(joinpoint, advices, pointcut=None, depth=1, public=False):
    """
    Weave advices on joinpoint with input pointcut.

    :param joinpoint: joinpoint from where checking pointcut and weaving
        advices.
    :type joinpoint: callable

    :param pointcut: condition for weaving advices on joinpointe.
        The condition depends on its type.
    :type pointcut:
        - NoneType: advices are weaved on joinpoint.
        - str: joinpoint name is compared to pointcut regex.
        - function: called with joinpoint in parameter, if True, advices will
            be weaved on joinpoint.

    :param depth: class weaving depthing
    :type depth: int

    :param public: (default True) weave only on public members
    :type public: bool

    :return: the intercepted functions created from input joinpoint.
    """

    if not isinstance(advices, Iterable):
        advices = (advices,)

    # check for not empty advices
    if not advices:
        raise AdviceError(
            "No one advice to weave on input joinpoint {0}".format(joinpoint))

    # do nothing if pointcut is None or is callable
    if pointcut is None or callable(pointcut):
        pass

    # in case of str, use a name matcher
    elif isinstance(pointcut, str):
        pointcut = NameMatcher(pointcut)

    else:
        raise AdviceError(
            "Wrong pointcut to check weaving on {0}. Must be None, \
or be a str or a function/method. Not {1}".
            format(joinpoint, type(pointcut)))

    result = []

    _weave(
        joinpoint, advices, pointcut, depth,
        _publicmembers if public else callable, result)

    return result


def _weave(joinpoint, advices, pointcut, depth, depth_predicate, intercepted):
    """
    Weave deeply advices in joinpoint
    """

    if isfunction(joinpoint):
        weaved_function = _apply_pointcut(
            joinpoint, joinpoint, advices, pointcut)
        intercepted.append(weaved_function)

    elif ismethod(joinpoint):
        weaved_function = _apply_pointcut(
            joinpoint, joinpoint.im_func, advices, pointcut)
        intercepted.append(weaved_function)

    # search inside the joinpoint
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(joinpoint, depth_predicate):
            weaved_functions = _weave(
                member, advices, pointcut, depth - 1, depth_predicate,
                intercepted)
            intercepted += weaved_functions


def _apply_pointcut(joinpoint, function, advices, pointcut=None):
    """
    Apply pointcut on input joinpoint.
    """

    if pointcut is None or pointcut(joinpoint):
        # ensure interception if it does not exist
        if not is_joinpoint(joinpoint):
            interception = JoinpointExecutor._get_interception_function(
                function)
            _apply_interception(
                joinpoint,
                interception)

        _add_advices(joinpoint, *advices)


def unweave(joinpoint, *advices):
    """
    Unweave advices from input joinpoint and returns removed advice ids.

    Input advices are of type Advice or UUID.
    """

    advice_ids = \
        (advice.uuid for advice in advices if isinstance(advice, Advice)) +\
        (advice for advice in advices if isinstance(advice, uuid.UUID))

    _remove_advices(joinpoint, *advice_ids)

    advices = get_advices(joinpoint)

    if not advices:
        _unapply_interception(joinpoint)

    return advice_ids


def weave_on(advices, pointcut=None, depth=1):
    """
    Decorator for weaving advices on a callable joinpoint.
    """

    def _weave(joinpoint):
        weave(
            joinpoint=joinpoint, advices=advices, pointcut=pointcut,
            depth=depth)

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
    def enable(self, enable=None):
        """
        Get self enable state. Change state if input enable is a boolean.

        TODO: change of method execution instead of saving a state.
        """

        if enable is not None:
            self._enable = enable

        return self._enable

    @enable.setter
    def enable(self, value):
        """
        Change of enable status.
        """

        self._enable = value

    def apply(self, joinpointexecution):
        """
        Apply this advice on input joinpointexecution.

        TODO: improve with internal methods instead of conditional test.
        """

        if self._enable:
            result = self._impl(joinpointexecution)
        else:
            result = joinpointexecution.proceed()

        return result

    def __call__(self, joinpointexecution):

        return self.apply(joinpointexecution)

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
