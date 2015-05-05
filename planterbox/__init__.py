from functools import partial
from importlib import import_module
import logging
import os
import re
import sys
from unittest import (
    TestCase,
    TestSuite,
    SkipTest,
)

from nose2.events import (
    Plugin,
)
from nose2.util import (
    exc_info_to_string,
)

log = logging.getLogger('planterbox')


INDENT = re.compile(r'^\s+')
SCENARIO = re.compile(r'^\s+Scenario:')


def indent_level(line):
    """Determine the indent level of a line.

    Indent level is defined as:
    - Number of whitespace characters at the start of the line
    - Tabs count as four spaces.
    """
    ws_match = INDENT.match(line)
    if ws_match is not None:
        ws = ws_match.group()
        ws = ws.replace('\t', '    ')
        return len(ws)


def starts_scenario(line):
    """Determine if a line signals the start of a scenario."""
    return SCENARIO.match(line)


def parse_feature(feature_text):
    """Parse a feature

    Returning a simple data structure containing:
    - One element containing all of the lines from feature name & advisory text
    - One element containing a list of scenarios
        - Each scenario is a list of lines of the scenario, including the name
    """
    lines = feature_text.split('\n')

    feature = []
    scenarios = []
    scenario = None
    scenario_indent = 0

    for line in lines:
        if not line.strip():
            continue

        if scenario is not None:
            line_indent = indent_level(line)
            if line_indent <= scenario_indent:
                scenario = None
                scenario_indent = 0
            else:
                scenario.append(line)

        if scenario is None:  # Not elif - want to handle end-of-scenario
            if starts_scenario(line):
                scenario = [line]
                scenario_indent = indent_level(line)
                scenarios.append(scenario)
            else:
                feature.append(line)

    return feature, scenarios


class FeatureTestSuite(TestSuite):
    """Create a test suite composed of test cases created from a feature"""

    def __init__(self, world_module, feature_text):
        super(FeatureTestSuite, self).__init__()
        self.world_module = world_module

        feature_text, scenarios = parse_feature(feature_text)
        self.feature_name = feature_text[0].strip().replace(
            'Feature:', ''
        ).strip()
        self.feature_doc = [doc.strip() for doc in feature_text[1:]]
        self.addTests([
            ScenarioTestCase(self.feature_name, self.feature_doc,
                             self.world_module, scenario)
            for scenario in scenarios
        ])


class MixedStepParametersException(Exception):
    """Raised when a step mixes positional and named parameters."""
    pass


class UnmatchedStepException(Exception):
    """Raised when a step cannot be found to execute a line from a scenario."""
    pass


class FeatureExcInfo(tuple):
    """exc_info plus extra information used by ScenarioTestCase"""

    @classmethod
    def from_exc_info(cls, exc_info, completed_steps, step):
        self = FeatureExcInfo(exc_info)
        self.completed_steps = completed_steps
        self.step = step
        return self


class ScenarioTestCase(TestCase):
    """A test case generated from a scenario in a feature file."""

    def __init__(self, feature_name, feature_doc, world, scenario):
        super(ScenarioTestCase, self).__init__('nota')
        self.feature_name = feature_name
        self.feature_doc = feature_doc
        self.world = world
        self.scenario_name = scenario[0].strip().replace(
            'Scenario:', ''
        ).strip()
        self.scenario = scenario[1:]
        self.step_inventory = self.harvest_steps()

    def harvest_steps(self):
        """Find all steps that have been imported into this feature's world"""
        return [
            maybe_step for maybe_step
            in [getattr(self.world, name) for name in dir(self.world)]
            if (
                hasattr(maybe_step, '__call__')
                and hasattr(maybe_step, 'planterbox_pattern')
            )
        ]

    def match_step(self, step):
        """Find a matching function for a given step from a scenario"""
        for step_fn in self.step_inventory:
            step_match = step_fn.planterbox_pattern.match(step)
            if step_match is not None:
                if step_match.groupdict():
                    if len(step_match.groupdict()) != len(step_match.groups()):
                        raise MixedStepParametersException()
                    return step_fn, step_match.groupdict()
                else:
                    return step_fn, step_match.groups()

        raise UnmatchedStepException()

    def nota(self):
        """Stub method to satisfy TestCase's obsessive need for a test"""

    def run(self, result=None):
        result.startTest(self)
        completed_steps = []
        try:
            for step in self.scenario:
                step_fn, step_arguments = self.match_step(step)
                if isinstance(step_arguments, dict):
                    step_fn(self, **step_arguments)
                else:
                    step_fn(self, *step_arguments)
                completed_steps.append(step)
            result.addSuccess(self)
        except KeyboardInterrupt:
            raise
        except self.failureException:
            result.addFailure(self, FeatureExcInfo.from_exc_info(
                sys.exc_info(),
                completed_steps,
                step,
            ))
        except SkipTest as e:
            self._addSkip(result, str(e))
        except:
            result.addError(self, sys.exc_info())
        finally:
            result.stopTest(self)

    def shortDescription(self):
        return '\n'.join(self.feature_doc)

    def formatTraceback(self, err):
        """Format containing both feature info and traceback info"""
        if isinstance(err, FeatureExcInfo):
            formatted = '\n'.join([
                completed_step.strip() for completed_step
                in err.completed_steps
            ] + [
                err.step.strip(),
                exc_info_to_string(err, super(ScenarioTestCase, self))
            ])
            return formatted
        else:
            return exc_info_to_string(err, super(ScenarioTestCase, self))

    def __str__(self):
        """Display a test's name as Scenario (Feature)"""
        return "%s (%s)" % (self.scenario_name, self.feature_name)


def import_feature_module(topLevelDirectory, path):
    """Find and import the module for the package containing a .feature"""
    directory = os.path.dirname(path)
    module_path = os.path.relpath(directory, start=topLevelDirectory)
    module_name = module_path.replace('/', '.')
    return import_module(module_name)


class Planterbox(Plugin):
    configSection = 'planterbox'
    commandLineSwitch = (None, 'with-planterbox',
                         'Load tests from .feature files')

    def handleFile(self, event):
        """Produce a FeatureTestSuite from a .feature file."""
        path = event.path
        if os.path.splitext(path)[1] != '.feature':
            return

        event.handled = True

        feature_module = import_feature_module(event.topLevelDirectory, path)

        with open(path, mode='r') as feature_file:
            feature_text = feature_file.read()

        return FeatureTestSuite(
            world_module=feature_module,
            feature_text=feature_text,
        )


def make_step(pattern, fn):
    """Inner decorator for making a function usable as a step."""
    planterbox_prefix = r'^\s*(?:Given|And|When|Then)\s+'
    fn.planterbox_pattern = re.compile(planterbox_prefix + pattern,
                                       re.IGNORECASE,
                                       )
    return fn


def step(pattern):
    """Decorate a function with a pattern so it can be used as a step."""
    return partial(make_step, pattern)
