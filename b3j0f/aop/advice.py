# -*- coding: utf-8 -*-

"""
Provides functions in order to weave/unweave/get advices from callable objects.
"""

from re import compile as re_compile

from uuid import uuid4 as uuid

from inspect import getmembers, isroutine, getargspec, isbuiltin

from functools import wraps

from opcode import opmap

from types import FunctionType

from collections import Iterable

from time import time

try:
    from threading import Timer
except ImportError:
    from dummy_threading import Timer

from b3j0f.aop.joinpoint import (
    get_intercepted, _apply_interception,
    _unapply_interception, is_intercepted, get_function
)
from b3j0f.utils.version import basestring, PY3

__all__ = [
    'AdviceError', 'AdvicesExecutor', 'get_advices',
    'weave', 'unweave', 'weave_on',
    'Advice'
]

# consts for interception loading
LOAD_GLOBAL = opmap['LOAD_GLOBAL']
LOAD_CONST = opmap['LOAD_CONST']

WRAPPER_ASSIGNMENTS = ('__doc__', '__annotations__')

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

    #: lambda function name
    __LAMBDA_NAME__ = (lambda: None).__name__

    #: lambda function interception name
    __INTERCEPTION__ = 'interception'

    #: attribute name for context execution
    CONTEXT = 'context'

    #: attribute name for interception joinpoint
    CALLEE = 'callee'

    #: attribute name for callee args
    ARGS = 'args'

    #: attribute name for callee kwargs
    KWARGS = 'kwargs'

    #: private attribute name for intercepted element
    _INTERCEPTED = '_intercepted'

    #: private attribute name for internal iterator for advices execution
    _ADVICES_ITERATOR = '_advices_iterator'

    #: private attribute name for advices
    _ADVICES = '_advices'

    __slots__ = (
        CONTEXT, CALLEE, ARGS, KWARGS,
        _INTERCEPTED, _ADVICES_ITERATOR, _ADVICES
    )

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
            advice = next(self._advices_iterator)

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

        try:
            # get params from joinpoint
            args, varargs, kwargs, _ = getargspec(function)
        except TypeError:
            # if function is not a python function, create one generic
            @wraps(joinpoint)
            def function(*args, **kwargs):
                pass
            # get params from joinpoint wrapper
            args, varargs, kwargs, _ = getargspec(function)

        # get params from joinpoint
        name = joinpoint.__name__

        # if joinpoint has not name, use 'function'
        if name == AdvicesExecutor.__LAMBDA_NAME__:
            name = AdvicesExecutor.__INTERCEPTION__

        # get join method for reducing concatenation time execution
        join = "".join

        newcodestr = "def %s(" % name
        if args:
            newcodestr = join((newcodestr, "%s" % args[0]))
        for arg in args[1:]:
            newcodestr = join((newcodestr, ", %s" % arg))

        if varargs is not None:
            if args:
                newcodestr = join((newcodestr, ", "))
            newcodestr = join((newcodestr, "*%s" % varargs))

        if kwargs is not None:
            if args or varargs is not None:
                newcodestr = join((newcodestr, ", "))
            newcodestr = join((newcodestr, "**%s" % kwargs))

        newcodestr = join((newcodestr, "):\n"))

        # unique id which will be used for advicesexecutor and kwargs
        generated_id = int(time())

        # if kwargs is None
        if kwargs is None and args:
            kwargs = "kwargs_%s" % generated_id  # generate a name
            # initialize a new dict with args
            newcodestr = join((newcodestr, "   %s = {\n" % kwargs))
            for arg in args:
                newcodestr = join(
                    (newcodestr, "      '%s': %s,\n" % (arg, arg))
                )
            newcodestr = join((newcodestr, "   }\n"))
        else:
            # fill args in kwargs
            for arg in args:
                newcodestr = join(
                    (newcodestr, "   %s['%s'] = %s\n" % (kwargs, arg, arg))
                )

        # advicesexecutor name
        ae = "advicesexecutor_%s" % generated_id

        if varargs:
            newcodestr = join(
                (newcodestr, "   %s.args = %s\n" % (ae, varargs))
            )

        # set kwargs in advicesexecutor
        if kwargs is not None:
            newcodestr = join(
                (newcodestr, "   %s.kwargs = %s\n" % (ae, kwargs))
            )

        # return advicesexecutor proceed result
        proceed = "proceed_%s" % generated_id
        newcodestr = join(
            (newcodestr, "   return %s()\n" % proceed)
        )

        # compile newcodestr
        code = compile(newcodestr, '<string>', 'single')

        _globals = {}

        # define the code with the new function
        exec(code, _globals)

        # get new code
        newco = _globals[name].__code__
        # get new consts list
        newconsts = list(newco.co_consts)

        if PY3:
            newcode = list(newco.co_code)
        else:
            newcode = map(ord, newco.co_code)

        consts_values = {ae: self, proceed: self.execute}

        # change LOAD_GLOBAL to LOAD_CONST
        index = 0
        newcodelen = len(newcode)
        while index < newcodelen:
            if newcode[index] == LOAD_GLOBAL:
                oparg = newcode[index + 1] + (newcode[index + 2] << 8)
                name = newco.co_names[oparg]
                if name in consts_values:
                    pos = len(newconsts)
                    newconsts.append(consts_values[name])
                    newcode[index] = LOAD_CONST
                    newcode[index + 1] = pos & 0xFF
                    newcode[index + 2] = pos >> 8
                    if name == proceed:
                        break  # stop when proceed is encountered
            index += 1

        # get code string
        codestr = bytes(newcode) if PY3 else join(map(chr, newcode))

        # get vargs
        vargs = [
            newco.co_argcount, newco.co_nlocals, newco.co_stacksize,
            newco.co_flags, codestr, tuple(newconsts), newco.co_names,
            newco.co_varnames, newco.co_filename, newco.co_name,
            newco.co_firstlineno, newco.co_lnotab, newco.co_freevars,
            newco.co_cellvars
        ]
        if PY3:
            vargs.insert(1, newco.co_kwonlyargcount)

        # instanciate a new code object
        codeobj = type(newco)(*vargs)
        # instanciate a new function
        if function is None or isbuiltin(function):
            interception_function = FunctionType(codeobj, {})
        else:
            interception_function = type(function)(
                codeobj, function.__globals__, function.__name__,
                function.__defaults__, function.__closure__
            )

        # update wrapping assignments
        for wrapper_assignment in WRAPPER_ASSIGNMENTS:
            try:
                value = getattr(joinpoint, wrapper_assignment)
            except AttributeError:
                pass
            else:
                setattr(interception_function, wrapper_assignment, value)

        # get interception_function
        interception, intercepted = _apply_interception(
            joinpoint=joinpoint, interception_function=interception_function)

        self.intercepted = interception

        return interception


def _add_advices(joinpoint, advices):
    """
    Add advices on input joinpoint.

    :param joinpoint joinpoint: joinpoint from where add advices
    :param advices advices: advices to weave on input joinpoint
    :param bool ordered: ensure advices to add will be done in input order
    """

    joinpoint_advices = getattr(joinpoint, _ADVICES, [])

    for advice in advices:
        joinpoint_advices.append(advice)

    setattr(joinpoint, _ADVICES, joinpoint_advices)


def _remove_advices(joinpoint, advices):
    """
    Remove advices from input joinpoint.

    :param advices: advices to remove. If None, remove all advices.
    """

    joinpoint_advices = getattr(joinpoint, _ADVICES, [])

    if advices is not None:
        joinpoint_advices = list(
            advice for advice in joinpoint_advices if advice not in advices
        )
    else:
        joinpoint_advices = ()

    if joinpoint_advices:  # update joinpoint advices
        setattr(joinpoint, _ADVICES, joinpoint_advices)
    else:  # free joinpoint advices if necessary
        delattr(joinpoint, _ADVICES)
        _unapply_interception(joinpoint)


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
    pointcut_application=None, ttl=None
):
    """
    Weave advices on joinpoint with input pointcut.

    :param callable joinpoint: joinpoint from where checking pointcut and
        weaving advices.
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
        required. AdvicesExecutor().apply_pointcut by default. Such routine has
        to take in parameters a routine called joinpoint and its related
        function called function. Its result is the interception function.
    :param float ttl: time to leave for weaved advices.

    :return: the intercepted functions created from input joinpoint or a tuple
        with intercepted functions and ttl timer.
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
    elif isinstance(pointcut, basestring):
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
        # does not handle not python functions
        if interception_function is not None:
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


def unweave(
    joinpoint, advices=None, pointcut=None, depth=1, public=False
):
    """
    Unweave advices on joinpoint with input pointcut.

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

    # ensure advices is a list if not None
    if advices is not None:

        # initialize advices
        if not isinstance(advices, Iterable):
            advices = [advices]

        elif not isinstance(advices, list):
            advices = list(advices)

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

    _unweave(
        joinpoint=joinpoint, advices=advices, pointcut=pointcut, depth=depth,
        depth_predicate=_publicmembers if public else callable)


def _unweave(
    joinpoint, advices, pointcut, depth, depth_predicate,
):
    """
    Unweave deeply advices in joinpoint.
    """

    # if weaving has to be done
    if isroutine(joinpoint) and (pointcut is None or pointcut(joinpoint)):
        # get joinpoint interception function
        interception_function = get_function(joinpoint)
        # does not handle not python functions
        if interception_function is not None:
            # intercept joinpoint if not intercepted
            if is_intercepted(joinpoint):
            # remove advices to the interception function
                _remove_advices(
                    joinpoint=interception_function, advices=advices)

    # search inside the joinpoint
    elif depth > 0:  # for an object or a class, weave on methods
        for name, member in getmembers(joinpoint, depth_predicate):
            _unweave(
                joinpoint=member, advices=advices, pointcut=pointcut,
                depth=depth - 1, depth_predicate=depth_predicate)


def weave_on(advices, pointcut=None, depth=1):
    """
    Decorator for weaving advices on a callable joinpoint.
    """

    def _weave(joinpoint):
        weave(
            joinpoint=joinpoint, advices=advices, pointcut=pointcut,
            depth=depth)
        return joinpoint

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
