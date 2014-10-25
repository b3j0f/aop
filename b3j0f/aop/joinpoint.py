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

from types import MethodType

from b3j0f.utils.version import PY2
from b3j0f.utils.reflect import base_elts

__all__ = [
    'get_function', 'JoinpointError', 'get_joinpoint',
    'get_intercepted', 'is_intercepted'
]

#: attribute which binds the intercepted function from the interceptor function
_INTERCEPTED = '_intercepted'

#: attribute which binds an interception function to its parent joinpoint
_JOINPOINT = '_joinpoint'


class JoinpointError(Exception):
    """
    Handle Joinpoint errors
    """

    pass


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
        constructor = getattr(
            joinpoint, '__init__', getattr(
                joinpoint, '__new__', None
            )
        )
        result = get_function(constructor)

    elif isbuiltin(joinpoint):
        result = joinpoint

    # else get callable function
    else:
        call = joinpoint.__call__
        result = getattr(call, _INTERCEPTED, None)

    return result


def _container(container, joinpoint):
    """
    Try to get the right joinpoint container (instance or class).
    """

    result = container

    # get container if not specified but findable
    if container is None and ismethod(joinpoint):
        if getattr(joinpoint, '__self__', None) is not None:
            result = joinpoint.__self__
        elif PY2:
            result = joinpoint.im_class

    return result


def _apply_interception(
    joinpoint, interception_function, container=None, _globals=None
):
    """
    Apply interception on input joinpoint and return the final joinpoint.

    :param function joinpoint: joinpoint on applying the interception_function
    :param function interception_function: interception function to apply on
        joinpoint
    :param container: joinpoint container (instance or class) if not None.

    :return: both interception and intercepted
        - if joinpoint is a builtin function,
            the result is a (wrapper function, builtin).
        - if joinpoint is a function, interception is joinpoint where
            code is intercepted code, and interception is a new function where
            code is joinpoint code.
    :rtype: tuple(callable, function)
    """

    intercepted = joinpoint
    interception = interception_function

    # try to get the right container
    if container is None:
        container = _container(container, joinpoint)

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

    elif container is not None:
        # update container
        intercepted_name = intercepted.__name__
        if ismethod(intercepted):  # in creating eventually a new method
            args = [interception, container]
            if PY2:  # if py2, specify the container class
                # and unbound method type
                if intercepted.__self__ is None:
                    args = [interception, None, container]
                else:
                    args.append(container.__class__)
            # instantiate a new method
            interception = MethodType(*args)

        # set in container the new method
        setattr(container, intercepted_name, interception)

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


def _unapply_interception(joinpoint, container=None):
    """
    Unapply interception on input joinpoint in cleaning it.

    :param routine joinpoint: joinpoint from where removing an interception
        function. is_joinpoint(joinpoint) must be True.
    :param container: joinpoint container.
    """

    joinpoint_function = get_function(joinpoint)

    # get previous joinpoint
    intercepted = getattr(joinpoint_function, _INTERCEPTED)

    # try to get the right container
    if container is None:
        container = _container(container, joinpoint)

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

    elif container is not None:
        # replace the old method
        intercepted_name = intercepted.__name__
        cls = container if isclass(container) else container.__class__
        elts = base_elts(cls=cls, elt=intercepted)
        if elts:  # remove inherited joinpoint
            delattr(container, intercepted_name)
        else:  # or put it
            setattr(container, intercepted_name, intercepted)
        delattr(joinpoint_function, _INTERCEPTED)

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

    if result is not None and ismethod(result):
        result = result.__func__

    return result


def get_joinpoint(function):
    """
    Get parent function joinpoint.
    """

    result = getattr(function, _JOINPOINT, None)

    return result
