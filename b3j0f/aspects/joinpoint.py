#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module which aims to manage python joinpoint interception.

A joinpoint is just a callable element.

functions allow to weave an interception function on any python callable
object.
"""

from inspect import isbuiltin, ismethod, isclass, isfunction, getmodule, \
    getmembers

# used by python to save function code
_FUNC_CODE = '__code__'

# attribute which binds the intercepted function from the interceptor function
_INTERCEPTED = '_intercepted'


class JoinpointError(Exception):
    pass


def _function(joinpoint):
    """
    Get joinpoint function if joinpoint.

    None in other cases.

    :param joinpoint: joinpoint from where getting the joinpoint function.
    :type joinpoint: object

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
        result = _function(constructor)

    # else get callable function
    else:
        call = joinpoint.__call__
        result = getattr(call, _INTERCEPTED, None)

    return result


def _is_not_modifiable(joinpoint):
    """
    Check if joinpoint is modifiable or requires to create a wrapper in order
    to ensure its interception.

    :return: True iif input joinpoint can not be modified.
    :rtype: bool
    """

    result = isbuiltin(joinpoint) or hasattr(joinpoint, '__slots__')

    return result


def _apply_interception(joinpoint, interception_function, _globals=None):
    """
    Apply interception on input joinpoint and return the final joinpoint.

    :param joinpoint: joinpoint on applying the interception_function
    :type joinpoint: function

    :param interception_function: interception function to apply on
        joinpoint.
    :type interception_function: function

    :return: both interception and intercepted functions
        - if joinpoint is not a modifiable function,
            the result is a (wrapper function, joinpoint).
        - if joinpoint is a function, interception is joinpoint where
            code is intercepted code, and interception is a new function where
            code is joinpoint code.
    :rtype: tuple(function, function)
    """

    intercepted = joinpoint
    interception = interception_function

    # if joinpoint is not modifiable
    if _is_not_modifiable(joinpoint):
        # update not modifiable function reference in module with wrapper
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

        interception = joinpoint
        intercepted = interception_function

        # switch of code between joinpoint_function and
        # interception_function
        func_code = getattr(intercepted, _FUNC_CODE)
        setattr(intercepted, _FUNC_CODE, getattr(interception, _FUNC_CODE))
        setattr(interception, _FUNC_CODE, func_code)

    # add intercepted into interception globals and attributes
    setattr(interception, _INTERCEPTED, intercepted)
    interception.func_globals[_INTERCEPTED] = intercepted

    if _globals is not None:
        interception.func_globals.update(_globals)

    return interception, intercepted


def _unapply_interception(joinpoint):
    """
    Unapply interception on input joinpoint in cleaning it.

    :param joinpoint: joinpoint from where removing an interception function.
        is_joinpoint(joinpoint) must be True.
    :type joinpoint: routine.
    """

    joinpoint_function = _function(joinpoint)

    # get previous joinpoint
    intercepted = getattr(joinpoint_function, _INTERCEPTED)

    # if old joinpoint is a not modifiable resource
    if _is_not_modifiable(intercepted):
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
        setattr(joinpoint_function, _FUNC_CODE,
            getattr(intercepted, _FUNC_CODE))
        # and delete the _INTERCEPTED attribute
        delattr(joinpoint_function, _INTERCEPTED)


def is_intercepted(element):
    """
    True iif input element is intercepted.

    :param element: element to check such as an intercepted element.
    :type element: object.

    :return: True iif input element is intercepted.
    :rtype: bool
    """

    result = False

    # get interception function from input element
    interception_function = _function(element)

    if interception_function is not None:
        # has _INTERCEPTED attribute ?
        result = hasattr(interception_function, _INTERCEPTED)

    return result


def get_intercepted(joinpoint):
    """
    Get intercepted function from input joinpoint.

    :param joinpoint: joinpoint from where getting the intercepted function
    :type joinpoint: joinpoint

    :raise JoinpointError: if joinpoint is not a joinpoint
    """

    interception = _function(joinpoint)

    result = getattr(interception, _INTERCEPTED, None)

    if result is None:
        raise JoinpointError('joinpoint %s must be a joinpoint' % joinpoint)

    return result
