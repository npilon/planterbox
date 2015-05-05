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
    TestOutcomeEvent,
)
from nose2.util import (
    exc_info_to_string,
)

log = logging.getLogger('planterbox')


INDENT = re.compile(r'^\s+')


def indent_level(line):
    ws_match = INDENT.match(line)
    if ws_match is not None:
        ws = ws_match.group()
        ws = ws.replace('\t', '    ')
        return len(ws)


SCENARIO = re.compile(r'^\s+Scenario:')


def starts_scenario(line):
    return SCENARIO.match(line)


def parse_feature(feature_text):
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

    def run(self, result, debug=False):
        super(FeatureTestSuite, self).run(result, debug)


class MixedStepParametersException(Exception):
    pass


class UnmatchedStepException(Exception):
    pass


class ScenarioTestCase(TestCase):
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
        return [
            maybe_step for maybe_step
            in [getattr(self.world, name) for name in dir(self.world)]
            if (
                hasattr(maybe_step, '__call__')
                and hasattr(maybe_step, 'planterbox_pattern')
            )
        ]

    def match_step(self, step):
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
        except self.failureException as exc:
            self._addStepFailure(result, completed_steps,
                                 step, exc, sys.exc_info())
        except SkipTest as e:
            self._addSkip(result, str(e))
        except:
            result.addError(self, sys.exc_info())
        finally:
            result.stopTest(self)

    def shortDescription(self):
        return '\n'.join(self.feature_doc)

    def _addStepFailure(self, result, completed_steps, step, exc, exc_info):
        event = TestOutcomeEvent(self, result, 'failed', (
            completed_steps,
            step,
            exc,
            exc_info,
        ))
        result.session.hooks.setTestOutcome(event)
        result.session.hooks.testOutcome(event)

    def formatTraceback(self, err):
        completed_steps, step, exc, exc_info = err
        formatted = '\n'.join([
            completed_step.strip() for completed_step in completed_steps
        ] + [
            step.strip(),
            exc_info_to_string(exc_info, super(ScenarioTestCase, self))
        ])
        return formatted

    def __str__(self):
        return "%s (%s)" % (self.scenario_name, self.feature_name)


def import_feature_module(topLevelDirectory, path):
    directory = os.path.dirname(path)
    module_path = os.path.relpath(directory, start=topLevelDirectory)
    module_name = module_path.replace('/', '.')
    return import_module(module_name)


class Planterbox(Plugin):
    configSection = 'planterbox'
    commandLineSwitch = (None, 'with-planterbox',
                         'Load tests from .feature files')

    def __init__(self):
        pass

    def handleFile(self, event):
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
    planterbox_prefix = r'^\s*(?:Given|And|When|Then)\s+'
    fn.planterbox_pattern = re.compile(planterbox_prefix + pattern,
                                       re.IGNORECASE,
                                       )
    return fn


def step(pattern):
    return partial(make_step, pattern)
