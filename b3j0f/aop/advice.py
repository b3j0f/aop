# -*- coding: utf-8 -*-

from re import compile as re_compile

from uuid import uuid4 as uuid

from functools import wraps

from inspect import getmembers, isroutine

from opcode import opmap

LOAD_CONST = opmap['LOAD_CONST']

from collections import Iterable

from b3j0f.aop.joinpoint import (get_intercepted, _apply_interception,
    _unapply_interception, is_intercepted, get_function)


_ADVICES = '_advices'  #: joinpoint advices attribute name


class AdviceError(Exception):
    """
    Handle Advice errors
    """

    pass


class AdvicesExecutor(object):
    """
    Manage joinpoint execution with Advices.

    Advices are callable objects which take in parameter a AdvicesExecutor.

    AdvicesExecutor provides to advices:
        - the joinpoint,
        - joinpoint call arguments as args and kwargs property,
        - a shared context during interception such as a dictionary.
    """

    __slots__ = (
        'context',  # context execution
        'callee',  # interception joinpoint
        'args',  # callee args
        'kwargs',  # callee kwargs
        '_intercepted',  # intercepted
        '_advices_iterator',  # internal iterator for advices execution
        '_advices')  # advices

    def __init__(
        self,
        joinpoint=None, args=None, kwargs=None, advices=None, context=None
    ):
        """
        Initialize a new AdvicesExecutor with a joinpoint,
        its calling arguments (args and kwargs) and a list of advices
        (callable which take self in parameter).

        If joinpoint, args and kwargs are not None, self AdvicesExecutor is
        used in a static context.

        :param callable joinpoint: joinpoint which is intercepted by input
            advices. is_intercepted(joinpoint) must be True

        :param args: joinpoint call *args argument.
        :type args: tuple of values.

        :param dict kwargs: joinpoint call **kwargs argument

        :param advices: Iterable of advices
            If None, they will be dynamically loaded during proceeding related
            to joinpoint.
        :type advices: Iterable of callables

        :param dict context: execution context
        """

        super(AdvicesExecutor, self).__init__()

        self.intercepted = joinpoint

        self.args = () if args is None else args
        self.kwargs = {} if kwargs is None else kwargs

        self.advices = advices

        self.context = {} if context is None else context

    @property
    def intercepted(self):
        """
        Get intercepted joinpoint.
        """

        return self._intercepted

    @intercepted.setter
    def intercepted(self, value):

        self.callee = value

        # if value is not intercepted, apply self to value
        if value is not None and not is_intercepted(value):
            self.apply_pointcut(value)
        self._intercepted = None if value is None else get_intercepted(value)

    @property
    def advices(self):

        return self._advices

    @advices.setter
    def advices(self, value):

        self._advices = () if value is None else value
        self._advices_iterator = None

    def execute(self, joinpoint=None, args=None, kwargs=None, advices=None):
        """
        Proceed this AdvicesExecutor in calling all advices with this such
        as the only one parameter, and call at the end the joinpoint.
        """

        # initialization of advices interception
        if self._advices_iterator is None:

            # init joinpoint if not None
            if joinpoint is not None:
                self.intercepted = joinpoint

            # init args if not None
            if args is not None:
                self.args = args

            # init kwargs if not None
            if kwargs is not None:
                self.kwargs = kwargs

            # advices are input advices if not None else get_advices(joinpoint)
            if advices is not None:
                self.advices = advices

            elif not self.advices:
                self.advices = get_advices(self.callee)

            # initialize self._advices_iterator
            self._advices_iterator = iter(self._advices)

        try:
            # get next advice
            advice = self._advices_iterator.next()

        except StopIteration:  # if no advice can be applied
            # nonify _advices_iterator for next joinpoint call
            self._advices_iterator = None
            # and call intercepted
            return self._intercepted(*self.args, **self.kwargs)

        else:
            # if has next, apply advice on self
            return advice(self)

    def __call__(self, *args, **kwargs):
        """
        Shortcut to self.execute
        """

        return self.execute(*args, **kwargs)

    def apply_pointcut(self, joinpoint, function=None):
        """
        Apply pointcut on input joinpoint and returns final joinpoint.
        """

        if function is None:
            function = get_function(joinpoint)

        # create a wrapper function which execute an advices executor
        @wraps(function)
        def interception_function(*args, **kwargs):
            """
            Instantiate a AdvicesExecutor and proceeds it.
            """

            # get advicesexecutor from global scope
            # TODO: set advicesexecutor among consts for fast loading
            return advicesexecutor.execute(args=args, kwargs=kwargs)

        # get interception_function
        interception, intercepted = _apply_interception(
            joinpoint, interception_function)

        # and bind it to the interception_function
        interception.func_globals['advicesexecutor'] = self

        self.intercepted = interception

        return interception


def _add_advices(joinpoint, advices):
    """
    Add advices on input joinpoint.

    :param joinpoint joinpoint: joinpoint from where add advices
    :param advices advices: advices to weave on input joinpoint
    :param bool ordered: ensure advices to add will be done in input order
    """

    _advices = getattr(joinpoint, _ADVICES, [])

    for advice in advices:
        _advices.append(advice)

    setattr(joinpoint, _ADVICES, _advices)


def _remove_advices(joinpoint, *advices):
    """
    Remove advices from input joinpoint.
    """

    _advices = getattr(joinpoint, _ADVICES, ())

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

        joinpoint_function = get_function(element)

        if joinpoint_function is not None:
            result = getattr(joinpoint_function, _ADVICES, ())

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

    return callable(joinpoint) and not getattr(
        joinpoint, '__name__', '').startswith('_')


def weave(
    joinpoint, advices, pointcut=None, depth=1, public=False,
    pointcut_application=None
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

    :param pointcut_application: routine which applies a pointcut when
        required. AdvicesExecutor().apply_pointcut by default. Such routine has
        to take in parameters a routine called joinpoint and its related
        function called function. Its result is the interception function.
    :type pointcut_application: routine

    :return: the intercepted functions created from input joinpoint.
    """

    if pointcut_application is None:
        pointcut_application = AdvicesExecutor().apply_pointcut

    # initialize advices
    if not isinstance(advices, Iterable):
        advices = [advices]

    elif not isinstance(advices, list):
        advices = list(advices)

    # check for not empty advices
    if not advices:
        raise AdviceError(
            "No one advice to weave on input joinpoint {0}".format(joinpoint))

    # initialize pointcut

    # do nothing if pointcut is None or is callable
    if pointcut is None or callable(pointcut):
        pass

    # in case of str, use a name matcher
    elif isinstance(pointcut, str):
        pointcut = _namematcher(pointcut)

    else:
        error_msg = "Wrong pointcut to check weaving on {0}.".format(joinpoint)
        advice_msg = "Must be None, or be a str or a function/method."
        right_msg = "Not {1}".format(type(pointcut))

        raise AdviceError(
            "{0} {1} {2}".format(error_msg, advice_msg, right_msg))

    result = []

    _weave(
        joinpoint=joinpoint, advices=advices, pointcut=pointcut, depth=depth,
        depth_predicate=_publicmembers if public else callable,
        intercepted=result, pointcut_application=pointcut_application)

    return result


def _weave(
    joinpoint, advices, pointcut, depth, depth_predicate, intercepted,
    pointcut_application
):
    """
    Weave deeply advices in joinpoint.
    """

    # if weaving has to be done
    if isroutine(joinpoint) and (pointcut is None or pointcut(joinpoint)):

        # get joinpoint interception function
        interception_function = get_function(joinpoint)
        # intercept joinpoint if not intercepted
        if not is_intercepted(joinpoint):

            interception_function = pointcut_application(
                joinpoint=joinpoint, function=interception_function)
        # add advices to the interception function
        _add_advices(joinpoint=interception_function, advices=advices)

        # append interception function to the intercepted ones
        intercepted.append(interception_function)

    # search inside the joinpoint
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(joinpoint, depth_predicate):
            _weave(
                joinpoint=member, advices=advices, pointcut=pointcut,
                depth=depth - 1, depth_predicate=depth_predicate,
                intercepted=intercepted,
                pointcut_application=pointcut_application)


def unweave(joinpoint, *advices):
    """
    Unweave advices from input joinpoint and returns removed advice ids.

    Input advices are of type Advice or UUID.
    """

    uuids_advices = (adv.uuid for adv in advices if isinstance(adv, Advice))
    uuids_advices = (uid for uid in advices if isinstance(uid, uuid.UUID))

    advice_ids = uuids_advices + uuids_advices

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

        advices = [advice if isinstance(advice, Advice) else Advice(advice)
            for advice in advices]

        weave(
            joinpoint=joinpoint, advices=advices, pointcut=pointcut,
            depth=depth, public=public)

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
