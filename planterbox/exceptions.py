"""Exceptions used to indicate planterbox-related states"""


class HookFailedException(Exception):
    """Propagate and summarize failure of a hook"""
    pass


class MixedStepParametersException(Exception):
    """Raised when a step mixes positional and named parameters."""
    pass


class UnmatchedStepException(Exception):
    """Raised when a step cannot be found to execute a line from a scenario."""
    pass


class UnmatchedSubstitutionException(Exception):
    """Raised when a named value from an outline can't be found in a step"""

    def __init__(self, step, *args, **kwargs):
        self.step = step
        super(UnmatchedSubstitutionException, self).__init__(*args, **kwargs)
