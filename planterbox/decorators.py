"""Decorators used when building a package of planterbox features to define
steps and hooks

Also some private functions used by those decorators.
"""

from functools import partial
import logging
import re

from six import (
    string_types,
)

log = logging.getLogger('planterbox')


EXAMPLE_TO_FORMAT = re.compile(r'<(.+?)>')
FEATURE_NAME = re.compile(r'\.feature(?:\:[\d,]+)?$')


def make_step(pattern, multiline, fn):
    """Inner decorator for making a function usable as a step."""
    planterbox_prefix = r'^\s*(?:Given|And|When|Then|But)\s+'
    planterbox_patterns = getattr(fn, 'planterbox_patterns', [])

    if multiline:
        if isinstance(multiline, string_types):
            pattern = pattern + r'\n(?P<{}>(?:.|\n)+)'.format(multiline)
        else:
            pattern = pattern + r'\n((?:.|\n)+)'

    planterbox_patterns.append(
        re.compile(planterbox_prefix + pattern, re.IGNORECASE))
    fn.planterbox_patterns = planterbox_patterns
    return fn


def step(pattern, multiline=False):
    """Decorate a function with a pattern so it can be used as a step.

    Optional arguments:
    - multiline: If true, this step-pattern will be turned into a multiline
      pattern. This adds a regular expression to the end that captures all
      remaining lines as a single group. If a string, that string will be used
      as the name of the multiline group.
    """
    return partial(make_step, pattern, multiline)


def make_hook(timing, stage, fn):
    """Inner decorator for making a function usable as a hook."""
    planterbox_hook_timing = getattr(fn, 'planterbox_hook_timing', set())
    planterbox_hook_timing.add((timing, stage))
    fn.planterbox_hook_timing = planterbox_hook_timing
    return fn


def hook(timing, stage):
    """Register a function as a hook to be run before or after """

    if timing not in ('before', 'after'):
        raise ValueError(timing)
    if stage not in ('feature', 'scenario', 'step', 'error', 'failure'):
        raise ValueError(stage)

    return partial(make_hook, timing, stage)
