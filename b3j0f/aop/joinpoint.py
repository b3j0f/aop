# -*- coding: utf-8 -*-

"""
Module which aims to manage python joinpoint interception.

A joinpoint is just a callable element.

functions allow to weave an interception function on any python callable
object.
"""

from inspect import isbuiltin, ismethod, isclass, isfunction, getmodule, \
    getmembers

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
        result = joinpoint.im_func

    # if joinpoint is a function, result is the joinpoint
    elif isfunction(joinpoint):
        result = joinpoint

    # if joinpoint is a class, result is the constructor function
    elif isclass(joinpoint):
        constructor = getattr(joinpoint, '__init__', joinpoint.__new__)
        result = get_function(constructor)

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

    # if joinpoint is a bultin
    if isbuiltin(joinpoint):
        # update builtin function reference in module with wrapper
        module = getmodule(joinpoint)
        found = False  # check for found function

        # update all references by value
        for name, member in getmembers(
                module, lambda member: member is joinpoint):
            setattr(module, name, interception_function)
            found = True

        if not found:  # raise Exception if not found
            raise JoinpointError(
                "Impossible to weave on not modifiable function %s. \
                Must be contained in module %s" % (joinpoint, module))

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
    interception_function.func_globals[_INTERCEPTED] = intercepted

    setattr(interception_function, _JOINPOINT, interception)
    interception_function.func_globals[_JOINPOINT] = interception

    if _globals is not None:
        interception_function.func_globals.update(_globals)

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
                %s. Must be contained in module %s" % (joinpoint, module))

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
