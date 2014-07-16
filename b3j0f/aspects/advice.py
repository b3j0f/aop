#!/usr/bin/env python
# -*- coding: utf-8 -*-

from re import compile as recompile

from uuid import uuid4 as uuid

from functools import wraps

from inspect import ismethod, isfunction, getmembers

from collections import Iterable

from .joinpoint import get_intercepted, _apply_interception, \
    _unapply_interception, is_intercepted, _function


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
        'callee',  # interception joinpoint
        '_advices_iterator',  # internal iterator for advices execution
        'args',
        'kwargs')

    def __init__(self, *advices):
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
        self.callee = value
        self._joinpoint = get_intercepted(value)
        if self._joinpoint is None:
            self._joinpoint = value

    @property
    def advices(self):
        return self._advices

    @advices.setter
    def advices(self, value):
        self._advices = value
        self._advices_iterator = iter(value)

    def _execute(self, args, kwargs):
        """
        Start to execute this JoinpointExecutor.
        Must be called at the beginning of self execution.
        """

        self.args = args
        self.kwargs = kwargs

        # check if an iterator is available
        if self._advices_iterator is None:
            # if not, get joinpoint advices
            advices = get_advices(self.callee)
            # and get the advices iterator
            self._advices_iterator = iter(advices if advices else [])

        # call self
        self()

    def execute(self):
        """
        Proceed this JoinpointExecutor in calling all advices with this such
        as the only one parameter, and call at the end the joinpoint.
        """

        try:
            # get next advice
            advice = self._advices_iterator.next()

        except StopIteration:
            # if no advice can be applied, call joinpoint
            return self._joinpoint(*self.args, **self.kwargs)

        else:
            # if has next, apply advice on self
            return advice(self)

    def __call__(self):
        """
        Shortcut to self.execute
        """

        return self.execute()

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
        def interception(*args, **kwargs):
            """
            Instantiate a JoinpointExecutor and proceeds it.
            """

            # get joinpointexecution from global scope
            # TODO: set joinpointexecution among consts for fast loading
            return joinpointexecution._execute(args, kwargs)

        # add interception environment in interception globals
        interception_globals = {
            'joinpointexecution': JoinpointExecutor(
                joinpoint=joinpoint_function)
        }
        # update interception globals
        interception.func_globals.update(interception_globals)

        return interception


def _add_advices(joinpoint, advices, ordered):
    """
    Add advices on input joinpoint.

    :param joinpoint: joinpoint from where add advices
    :type joinpoint: joinpoint

    :param advices: advices to weave on input joinpoint
    :type advices: advices

    :param ordered: ensure advices to add will be done in input order or not
    :type ordered: bool
    """

    _advices = getattr(joinpoint, _ADVICES, None)

    if not _advices:
        _advices = [] if ordered else set()

    if ordered:
        for advice in advices:
            _advices.append(advice)
    else:
        for advice in advices:
            _advices.add(advice)

    setattr(joinpoint, _ADVICES, _advices)


def _remove_advices(joinpoint, *advices):
    """
    Remove advices from input joinpoint.
    """

    _advices = getattr(joinpoint, _ADVICES)

    if _advices:
        _advices = (advice for advice in _advices if advice not in advices)

    setattr(joinpoint, _ADVICES, _advices)


def get_advices(element):
    """
    Get element advices.

    None if element is not a joinpoint.
    """

    result = None

    if is_intercepted(element):

        joinpoint_function = _function(element)

        if joinpoint_function is not None:
            result = getattr(joinpoint_function, _ADVICES, None)

            if result is None:
                result = ()
            else:
                result = tuple(result)

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


def weave(
    joinpoint, advices, pointcut=None, depth=1, public=False, ordered=True
):
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

    :param ordered: (default True) ensure input advices order at runtime
    :type ordered: bool

    :return: the intercepted functions created from input joinpoint.
    """

    # initialize advices
    if not isinstance(advices, Iterable):
        advices = [advices] if ordered else {advices}

    elif not ordered and not isinstance(advices, set):
        advices = set(advices)

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
        joinpoint=joinpoint, advices=advices, pointcut=pointcut, depth=depth,
        depth_predicate=_publicmembers if public else callable,
        intercepted=result, ordered=ordered)

    return result


def _weave(
    joinpoint, advices, pointcut, depth, depth_predicate, intercepted, ordered
):
    """
    Weave deeply advices in joinpoint
    """

    if isfunction(joinpoint):
        weaved_function = _apply_pointcut(
            joinpoint=joinpoint, function=joinpoint, advices=advices,
            pointcut=pointcut, ordered=ordered)
        intercepted.append(weaved_function)

    elif ismethod(joinpoint):
        weaved_function = _apply_pointcut(
            joinpoint=joinpoint, function=joinpoint.im_func, advices=advices,
            pointcut=pointcut, ordered=ordered)
        intercepted.append(weaved_function)

    # search inside the joinpoint
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(joinpoint, depth_predicate):
            weaved_functions = _weave(
                joinpoint=member, advices=advices, pointcut=pointcut,
                depth=depth - 1, depth_predicate=depth_predicate,
                intercepted=intercepted, ordered=ordered)
            intercepted += weaved_functions


def _apply_pointcut(joinpoint, function, advices, pointcut, ordered):
    """
    Apply pointcut on input joinpoint.
    """

    if pointcut is None or pointcut(joinpoint):
        # ensure interception if it does not exist
        if not is_intercepted(joinpoint):
            interception = JoinpointExecutor._get_interception_function(
                function)
            interception = _apply_interception(joinpoint, interception)
            interception.func_globals['joinpointexecution'].joinpoint = \
                function

        _add_advices(joinpoint=joinpoint, advices=advices, ordered=ordered)


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

    def apply(self, joinpointexecution):
        """
        Apply this advice on input joinpointexecution.

        TODO: improve with internal methods instead of conditional test.
        """

        if self._enable:
            result = self._impl(joinpointexecution)
        else:
            result = joinpointexecution.execute()

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

        advices = [advice if isinstance(advice, Advice) else Advice(advice)
            for advice in advices]

        weave(
            joinpoint=joinpoint, advices=advices, pointcut=pointcut,
            depth=depth, public=public)

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
