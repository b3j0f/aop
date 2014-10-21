# -*- coding: utf-8 -*-

"""
Aspect Oriented Programming Library for Python

Provides tools to (un)weave and get advices, and check joinpoint status.
"""

__version__ = "0.4.6"

__all__ = [
    'weave', 'unweave', 'weave_on', 'get_advices',
    'Advice', 'AdvicesExecutor',
    'get_joinpoint', 'get_intercepted', 'is_intercepted'
]

from .advice import (
    weave, unweave, weave_on, Advice, AdvicesExecutor, get_advices
)
from .joinpoint import get_joinpoint, get_intercepted, is_intercepted
