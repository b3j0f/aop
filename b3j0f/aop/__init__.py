# -*- coding: utf-8 -*-

"""
Aspect Oriented Programming Library for Python

Provides tools to (un)weave and get advices, and check joinpoint status.
"""

__version__ = "0.5.0"

__all__ = [
    'weave', 'unweave', 'weave_on', 'get_advices',
    'Advice', 'AdvicesExecutor',
    'get_intercepted', 'is_intercepted',
    'Joinpoint', 'JoinpointError'
]

from .joinpoint import (
    Joinpoint, get_intercepted, is_intercepted, JoinpointError
)
from .advice import (
    weave, unweave, weave_on, Advice, get_advices
)
