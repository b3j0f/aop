# -*- coding: utf-8 -*-

"""
Module which aims to manage python joinpoint interception.

A joinpoint is just a callable element.

functions allow to weave an interception function on any python callable
object.
"""

from inspect import isbuiltin, ismethod, isclass, isfunction, getmodule, \
    getmembers

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

#: attribute which binds the intercepted function from the interceptor function
_INTERCEPTED = '_intercepted'

#: attribute which binds an interception function to its parent joinpoint
_JOINPOINT = '_joinpoint'

_INTERCEPTORS = '_interceptors'  #: attribute name for interceptors in __dict__


class JoinpointError(Exception):
    """
    Handle Joinpoint errors
    """

    pass

__DICT__ = '__dict__'  #: __dict__ joinpoint attribute name
__SELF__ = '__self__'  #: __self__ class instance attribute name


STATIC__DICTS__ = {}  #: dictionary of __dict__ by static objects


def get_interceptors(joinpoint):
    """
    Get interceptors from input joinpoint.

    :param callable joinpoint: joinpoint from where get interceptors

    :return: list of interceptors.
    :rtype: list
    """

    result = []

    # try to find interceptors into joinpoint such as an instance
    if hasattr(joinpoint, __SELF__):
        # self __dict__ which may contain interceptors
        __dict__ = None
        instance = joinpoint.__self__
        # search among self __dict__ if _INTERCEPTORS exists
        if hasattr(instance, __DICT__):
            __dict__ = instance.__dict__
        # if __dict__ does not exist in __self__, search in STATIC__DICTS__
        elif instance in STATIC__DICTS__:
            __dict__ = STATIC__DICTS__[instance]
        # if __dict__ has been founded, try to get value from key joinpoint
        if __dict__ is not None and joinpoint in __dict__:
            interceptors = __dict__[joinpoint]
            # if interceptors exists, add them to result
            if _INTERCEPTORS in interceptors:
                result += interceptors[_INTERCEPTORS]

    # try to find interceptors into joinpoint such as an type
    # joinpoint __dict__ which may contain interceptors
    __dict__ = None

    # try to get __dict__ from joinpoint
    if hasattr(joinpoint, __DICT__):
        __dict__ = joinpoint.__dict__
    elif joinpoint in STATIC__DICTS__:  # or from STATIC_DICTS__[joinpoint]
        __dict__ = STATIC__DICTS__[joinpoint]
    if __dict__ is not None and _INTERCEPTORS in __dict__:
        result += __dict__[_INTERCEPTORS]

    return result


def add_interceptors(joinpoint, **interceptors):
    """
    Add interceptors in joinpoint.
    """

    # if joinpoint is bound to an instance
    if hasattr(joinpoint, __SELF__):
        __dict__ = None
        instance = joinpoint.__self__
        # if instance has a dict attribute
        if hasattr(instance, __DICT__):
            __dict__ = instance.__dict__
        else:  # get __dict__ from STATIC__DICTS__
            __dict__ = STATIC__DICTS__.setdefault(instance, {})

    # if joinpoint has a __dict__ attribute
    elif hasattr(joinpoint, __DICT__):
        __dict__ = joinpoint.__dict__

    # if joinpoint is in STATIC__DICTS__
    elif joinpoint in STATIC__DICTS__:
        __dict__ = STATIC__DICTS__[joinpoint]

    # if a __dict__ has been founded
    if __dict__ is not None:
        # add input interceptors to local interceptors
        local_interceptors = __dict__.setdefault(joinpoint, [])
        local_interceptors += interceptors


def get_function(joinpoint):
    """
    Get joinpoint function if joinpoint.

    None in other cases.

    :param joinpoint: joinpoint from where getting the joinpoint function.

    :return: function corresponding to input joinpoint or None if it is
        impossible to get a joinpoint function.
    :rtype: function
    """

    result = None

    # ensure joinpoint is callable
    if not callable(joinpoint):
        raise JoinpointError(
            "joinpoint {0} must be a callable element.".format(joinpoint))

    # if joinpoint is a method, get embedded function
    if ismethod(joinpoint):
        result = joinpoint.__func__

    # if joinpoint is a function, result is the joinpoint
    elif isfunction(joinpoint):
        result = joinpoint

    # if joinpoint is a class, result is the constructor function
    elif isclass(joinpoint):
        constructor = getattr(joinpoint, '__init__', joinpoint.__new__)
        result = get_function(constructor)

    elif isbuiltin(joinpoint):
        result = joinpoint

    # else get callable function
    else:
        call = joinpoint.__call__
        result = getattr(call, _INTERCEPTED, None)

    return result


def _apply_interception(joinpoint, interception_function, _globals=None):
    """
    Apply interception on input joinpoint and return the final joinpoint.

    :param function joinpoint: joinpoint on applying the interception_function

    :param interception_function: interception function to apply on joinpoint
    :type interception_function: function

    :return: both interception object and intercepted functions
        - if joinpoint is a builtin function,
            the result is a (wrapper function, builtin).
        - if joinpoint is a function, interception is joinpoint where
            code is intercepted code, and interception is a new function where
            code is joinpoint code.
    :rtype: tuple(callable, function)
    """

    intercepted = joinpoint
    interception = interception_function

    # if joinpoint is a builtin
    if isbuiltin(joinpoint) or getmodule(joinpoint) is __builtin__:
        # update builtin function reference in module with wrapper
        module = getmodule(joinpoint)
        found = False  # check for found function

        if module is not None:
            # update all references by value
            for name, member in getmembers(
                    module, lambda member: member is joinpoint):
                setattr(module, name, interception_function)
                found = True

            if not found:  # raise Exception if not found
                raise JoinpointError(
                    "Impossible to weave on not modifiable function {0}. \
                    Must be contained in module {1}".format(joinpoint, module))

    else:  # update code with interception code
        joinpoint_function = get_function(joinpoint)
        interception = joinpoint
        intercepted = interception_function
        # switch of code between joinpoint_function and
        # interception_function
        joinpoint_function.__code__, interception_function.__code__ = \
            interception_function.__code__, joinpoint_function.__code__

    # add intercepted into interception_function globals and attributes
    interception_function = get_function(interception)

    setattr(interception_function, _INTERCEPTED, intercepted)
    interception_function.__globals__[_INTERCEPTED] = intercepted

    setattr(interception_function, _JOINPOINT, interception)
    interception_function.__globals__[_JOINPOINT] = interception

    if _globals is not None:
        interception_function.__globals__.update(_globals)

    return interception_function, intercepted


def _unapply_interception(joinpoint):
    """
    Unapply interception on input joinpoint in cleaning it.

    :param routine joinpoint: joinpoint from where removing an interception
        function. is_joinpoint(joinpoint) must be True.
    """

    joinpoint_function = get_function(joinpoint)

    # get previous joinpoint
    intercepted = getattr(joinpoint_function, _INTERCEPTED)

    # if old joinpoint is a not modifiable resource
    if isbuiltin(intercepted):
        module = getmodule(intercepted)
        found = False

        # update references to joinpoint to not modifiable element in module
        for name, member in getmembers(module):
            if member is joinpoint:
                setattr(module, name, intercepted)
                found = True

        # if no reference found, raise an Exception
        if not found:
            raise JoinpointError(
                "Impossible to unapply interception on not modifiable element \
                {0}. Must be contained in module {1}".format(
                    joinpoint, module))

    else:
        # update old code on joinpoint
        joinpoint_function.__code__ = intercepted.__code__
        # and delete the _INTERCEPTED attribute
        delattr(joinpoint_function, _INTERCEPTED)


def is_intercepted(element):
    """
    True iif input element is intercepted.

    :param element: element to check such as an intercepted element.

    :return: True iif input element is intercepted.
    :rtype: bool
    """

    result = False

    # get interception function from input element
    interception_function = get_function(element)

    if interception_function is not None:
        # has _INTERCEPTED attribute ?
        result = hasattr(interception_function, _INTERCEPTED)

    return result


def get_intercepted(joinpoint):
    """
    Get intercepted function from input joinpoint.

    :param joinpoint joinpoint: joinpoint from where getting the intercepted
        function

    :return: joinpoint intercepted function.
        None if no intercepted function exist
    :rtype: function or NoneType
    """

    interception = get_function(joinpoint)

    result = getattr(interception, _INTERCEPTED, None)

    return result


def get_joinpoint(function):
    """
    Get parent function joinpoint.
    """

    result = getattr(function, _JOINPOINT, None)

    return result
