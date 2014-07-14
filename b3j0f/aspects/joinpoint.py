#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module which aimes to manage python joinpoint interception.

A joinpoint is just a callable element.

functions allow to weave an interception function on any python callable
object.
"""

from inspect import isbuiltin, ismethod, isclass, isfunction, getmodule, \
    getmembers

# used by python to save function code
_FUNC_CODE = '__code__'

# used to save old code/function for not-builtins/builtins functions
# in interception joinpoint
_JOINPOINT = '_joinpoint'


# manage joinpoint errors
class JoinpointError(Exception):
        pass

# dictionary of not modifiable functions by interception function
_NOT_MODIFIABLE_JOINPOINT_BY_WRAPPERS = {}


def _get_interception_joinpoint(interception):
    """
    Get interception joinpoint.

    :param interception: object from where get joinpoint if it exists.
    :type interception:

    :return: interception joinpoint which is the same type as interception.
    :rtype: type(interception)
    """

    result = getattr(interception, _JOINPOINT, None)

    return result


def _get_joinpoint_function(joinpoint):
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

    # ensure joinpoint is a builtin, a function or a method
    if not callable(joinpoint):
        raise JoinpointError(
            "joinpoint {0} must be a callable element.".format(joinpoint))

    # if joinpoint is builtin, call global wrappers
    if isbuiltin(joinpoint):
        result = _NOT_MODIFIABLE_JOINPOINT_BY_WRAPPERS.get(joinpoint)

    # if joinpoint is a method, get embedded function
    elif ismethod(joinpoint):
        result = joinpoint.im_func

    # if joinpoint is a function, result is the joinpoint
    elif isfunction(joinpoint):
        result = joinpoint

    # if joinpoint is a class, result is the constructor function
    elif isclass(joinpoint):
        constructor = getattr(
            joinpoint, '__init__', getattr(
                joinpoint, '__new__'))
        result = _get_joinpoint_function(constructor)

    # else get callable function
    else:
        call = getattr(joinpoint, '__call__')
        result = _get_interception_joinpoint(call)

    return result

_INTERCEPTED = '_intercepted'


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
        :type joinpoint: a function or a method

        :param interception_function: interception function to apply on
            joinpoint.
        :type interception_function: function

        :rtype: type(joinpoint)

            - if joinpoint is a built-in function, the result is a wrapper
                function.
            - if joinpoint is a function, result is an enriched joinpoint where
                code is updated and old code is saved in the function with the
                _JOINPOINT key.
            - if joinpoint is a method, result is updated method where function
                respects previous procedure.
        """

        result = interception_function

        intercepted = joinpoint

        # if joinpoint is not modifiable
        if _is_not_modifiable(joinpoint):
            # update not modifiable function reference in module with wrapper
            module = getmodule(joinpoint)
            found = False  # check for found function

            # update all references by value
            for name, member in getmembers(
                    module, lambda member: member is joinpoint):
                setattr(module, name, result)
                found = True

            if not found:  # raise Exception if not found
                raise JoinpointError(
                    "Impossible to weave on not modifiable function %s. \
                    Must be contained in module %s" % (joinpoint, module))

            # keep reference between built-in function and its wrapper
            _NOT_MODIFIABLE_JOINPOINT_BY_WRAPPERS[intercepted] \
                = result

        else:  # update code with interception code

            result = intercepted
            intercepted = interception_function

            # switch of code between joinpoint_function and
            # interception_function
            func_code = getattr(result, _FUNC_CODE)
            setattr(result, _FUNC_CODE,
                    getattr(intercepted, _FUNC_CODE))
            setattr(intercepted, _FUNC_CODE, func_code)

            # add interception_globals to joinpoint_function
            result.func_globals[_INTERCEPTED] = intercepted
            intercepted.func_globals[_JOINPOINT] = joinpoint
            # and update joinpoint globals with intercepted function globals
            result.func_globals.update(
                interception_function.func_globals)

        setattr(result, _INTERCEPTED, intercepted)
        result.func_globals[_INTERCEPTED] = intercepted

        if _globals is not None:
            result.func_globals.update(_globals)

        return result


def _unapply_interception(joinpoint):
    """
    Unapply interception on input joinpoint in cleaning it.

    :param joinpoint: joinpoint from where removing an interception function.
        is_joinpoint(joinpoint) must be True.
    :type joinpoint: function or method.
    """

    joinpoint_function = _get_joinpoint_function(joinpoint)

    # get previous joinpoint
    old_joinpoint = getattr(joinpoint_function, _JOINPOINT)

    # if old joinpoint is a built-in
    if _is_not_modifiable(old_joinpoint):
        module = getmodule(old_joinpoint)
        found = False

        # update references to joinpoint to not modifiable element in module
        for name, member in getmembers(module):
            if member is joinpoint:
                setattr(module, name, old_joinpoint)
                found = True

        # if no reference found, raise an Exception
        if not found:
            raise JoinpointError(
                "Impossible to unapply interception on not modifiable element \
                %s. Must be contained in module %s" % (joinpoint, module))

        # delete reference to wrapper from built-in
        del _NOT_MODIFIABLE_JOINPOINT_BY_WRAPPERS[old_joinpoint]
        # remove _JOINPOINT from joinpoint
        delattr(joinpoint, _JOINPOINT)

    else:

        # update old code on joinpoint
        setattr(joinpoint_function, _FUNC_CODE,
                getattr(old_joinpoint, _FUNC_CODE))
        # delete reference to old code
        delattr(joinpoint_function, _JOINPOINT)


def is_joinpoint(element):
    """
    True iif input element is a joinpoint.

    :param element: element to check such as a joinpoint.
    :type element: function or method.

    :return: True iif input element is a joinpoint.
    :rtype: bool
    """

    result = None

    # get joinpoint function from input element
    joinpoint_function = _get_joinpoint_function(element)

    # get _JOINPOINT attribute
    result = hasattr(joinpoint_function, _JOINPOINT)

    return result
