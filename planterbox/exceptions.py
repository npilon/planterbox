"""Exceptions used to indicate planterbox-related states"""

class MixedStepParametersException(Exception):
    """Raised when a step mixes positional and named parameters."""
    pass


class UnmatchedStepException(Exception):
    """Raised when a step cannot be found to execute a line from a scenario."""
    pass
