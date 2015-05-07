from functools import partial
from itertools import (
    ifilter,
    ifilterfalse,
    izip,
)
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
    name_from_path,
    object_from_name,
    transplant_class,
)

log = logging.getLogger('planterbox')


INDENT = re.compile(r'^\s+')
SCENARIO = re.compile(r'^\s+Scenario(?: Outline)?:')
EXAMPLES = re.compile(r'^\s+Examples:')
EXAMPLE_TO_FORMAT = re.compile(r'<(.+?)>')
FEATURE_NAME = re.compile(r'\.feature(?:\:[\d,]+)?$')


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


def starts_examples(line):
    """Determine if a line signals the start of an example block."""
    return EXAMPLES.match(line)


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
    append_index = 1
    scenario_indent = 0

    for line in lines:
        if not line.strip():
            continue

        if scenario is not None:
            line_indent = indent_level(line)
            if line_indent <= scenario_indent:
                scenario = None
                scenario_indent = 0
            elif starts_examples(line):
                append_index = 2
            else:
                scenario[append_index].append(line)

        if scenario is None:  # Not elif - want to handle end-of-scenario
            if starts_scenario(line):
                scenario = [line, [], []]
                append_index = 1
                scenario_indent = indent_level(line)
                scenarios.append(scenario)
            else:
                feature.append(line)

    return feature, scenarios


class FeatureTestSuite(TestSuite):
    """Create a test suite composed of test cases created from a feature"""

    def __init__(self, world, feature_text, feature_path,
                 scenario_indexes=None):
        super(FeatureTestSuite, self).__init__()
        self.world = world

        feature_text, scenarios = parse_feature(feature_text)
        self.feature_name = feature_text[0].strip().replace(
            'Feature:', ''
        ).strip()
        self.feature_doc = [doc.strip() for doc in feature_text[1:]]
        MyScenarioTestCase = transplant_class(ScenarioTestCase, world.__name__)
        self.addTests([
            MyScenarioTestCase(
                feature_name=self.feature_name,
                feature_doc=self.feature_doc,
                world=self.world,
                scenario=scenario,
                feature_path=feature_path,
                scenario_index=i
            )
            for i, scenario in enumerate(scenarios)
            if scenario_indexes is None or i in scenario_indexes
        ])
        self.feature_hooks_run = False

    def _handleModuleFixture(self, test, result):
        super(FeatureTestSuite, self)._handleModuleFixture(test, result)
        if self.feature_hooks_run is False:
            try:
                run_hooks(self.world, self, result, 'before', 'feature')
                self.feature_hooks_run = True
            except HookFailedException:
                result._moduleSetUpFailed = True
                return

    def run(self, result, debug=False):
        super(FeatureTestSuite, self).run(result, debug)

        try:
            run_hooks(self.world, self, result, 'after', 'feature')
        except HookFailedException:
            return  # Failure already registered


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

    def __init__(self, feature_name, feature_doc, world, scenario,
                 feature_path, scenario_index):
        super(ScenarioTestCase, self).__init__('nota')
        self.feature_name = feature_name
        self.feature_doc = feature_doc
        self.world = world
        self.scenario_name = SCENARIO.sub('', scenario[0]).strip()
        self.scenario = scenario[1]
        self.examples = list(self.load_examples(scenario[2]))
        self.feature_path = feature_path
        self.scenario_index = scenario_index

    def id(self):
        return '{}:{}:{}'.format(
            self.world.__name__,
            os.path.basename(self.feature_path),
            self.scenario_index,
        )

    def load_examples(self, examples):
        if not examples:
            return

        example_header = example_row(examples.pop(0))
        for example in examples:
            example_data = example_row(example)
            yield {
                label: datum for label, datum
                in izip(example_header, example_data)
            }

    def harvest_steps(self):
        """Find all steps that have been imported into this feature's world"""
        return [
            maybe_step for maybe_step
            in [getattr(self.world, name) for name in dir(self.world)]
            if (
                hasattr(maybe_step, '__call__')
                and hasattr(maybe_step, 'planterbox_patterns')
            )
        ]

    def match_step(self, step):
        """Find a matching function for a given step from a scenario"""
        for step_fn in self.step_inventory:
            for pattern in step_fn.planterbox_patterns:
                step_match = pattern.match(step)
                if step_match is not None and step_match.groupdict():
                    if len(step_match.groupdict()) != len(step_match.groups()):
                        raise MixedStepParametersException()
                    return step_fn, step_match.groupdict()
                elif step_match is not None:
                    return step_fn, step_match.groups()

        raise UnmatchedStepException()

    def nota(self):
        """Stub method to satisfy TestCase's obsessive need for a test"""

    def run(self, result=None):
        result.startTest(self)
        self.step_inventory = list(self.harvest_steps())
        self.completed_steps = []
        try:
            run_hooks(self.world, self, result, 'before', 'scenario')
            if self.examples:
                self.run_outline(self.scenario, result)
            else:
                self.run_scenario(self.scenario, result)
            run_hooks(self.world, self, result, 'after', 'scenario')
        except HookFailedException:
            pass  # Failure already registered
        finally:
            result.stopTest(self)

    def run_scenario(self, scenario, result):
        try:
            for step in scenario:
                run_hooks(self.world, step, result, 'before', 'step')
                step_fn, step_arguments = self.match_step(step)
                if isinstance(step_arguments, dict):
                    step_fn(self, **step_arguments)
                else:
                    step_fn(self, *step_arguments)
                self.completed_steps.append(step)
                run_hooks(self.world, step, result, 'after', 'step')
            result.addSuccess(self)
        except KeyboardInterrupt:
            raise
        except HookFailedException:
            pass  # Failure already registered
        except self.failureException:
            result.addFailure(self, FeatureExcInfo.from_exc_info(
                sys.exc_info(),
                self.completed_steps,
                step,
            ))
        except SkipTest as e:
            result.addSkip(self, str(e))
        except:
            result.addError(self, sys.exc_info())

    def run_outline(self, scenario, result):
        for i, example in enumerate(self.examples):
            if i != 0:
                result.stopTest(self)
                result.startTest(self)
            example_scenario = substitute_steps(scenario, example)
            self.completed_steps = []
            self.run_scenario(example_scenario, result)

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


class Planterbox(Plugin):
    configSection = 'planterbox'
    commandLineSwitch = (None, 'with-planterbox',
                         'Load tests from .feature files')

    def makeSuiteFromFeature(self, world, feature_path,
                             scenario_indexes=None):
        with open(feature_path, mode='r') as feature_file:
            feature_text = feature_file.read()

        MyFeatureTestSuite = transplant_class(FeatureTestSuite, world.__name__)

        return MyFeatureTestSuite(
            world=world,
            feature_text=feature_text,
            feature_path=feature_path,
            scenario_indexes=scenario_indexes,
        )

    def handleFile(self, event):
        """Produce a FeatureTestSuite from a .feature file."""
        feature_path = event.path
        if os.path.splitext(feature_path)[1] != '.feature':
            return

        event.handled = True

        try:
            world_package_name = name_from_path(
                os.path.dirname(feature_path))
            feature_world = object_from_name(world_package_name)[1]
        except:
            return event.loader.failedImport(feature_path)

        return self.makeSuiteFromFeature(
            world=feature_world,
            feature_path=feature_path,
        )

    def registerInSubprocess(self, event):
        event.pluginClasses.insert(0, self.__class__)

    def loadTestsFromNames(self, event):
        is_feature = partial(FEATURE_NAME.search)
        feature_names = list(ifilter(is_feature, event.names))
        event.names = list(ifilterfalse(is_feature, event.names))

        test_suites = [
            self._from_name(name) for name in feature_names
        ]
        if event.names:
            event.extraTests.extend(test_suites)
        else:
            event.handled = True
            return test_suites

    def loadTestsFromName(self, event):
        log.debug(event)
        if FEATURE_NAME.search(event.name) is None:
            return

        event.handled = True

        return self._from_name(event.name)

    def _from_name(self, name):
        name_parts = name.split(':')
        if len(name_parts) == 3:
            scenario_indexes = {int(s) for s in name_parts.pop(-1).split(',')}
        elif len(name_parts) == 2:
            scenario_indexes = None
        else:
            return

        world_package_name, feature_filename = name_parts
        feature_world = object_from_name(world_package_name)[1]
        feature_path = os.path.join(
            os.path.dirname(feature_world.__file__), feature_filename
        )

        suite = self.makeSuiteFromFeature(
            world=feature_world,
            feature_path=feature_path,
            scenario_indexes=scenario_indexes,
        )
        return suite


def make_step(pattern, fn):
    """Inner decorator for making a function usable as a step."""
    planterbox_prefix = r'^\s*(?:Given|And|When|Then)\s+'
    planterbox_patterns = getattr(fn, 'planterbox_patterns', [])
    planterbox_patterns.append(re.compile(planterbox_prefix + pattern,
                                          re.IGNORECASE,
                                          ))
    fn.planterbox_patterns = planterbox_patterns
    return fn


def step(pattern):
    """Decorate a function with a pattern so it can be used as a step."""
    return partial(make_step, pattern)


def example_row(row):
    """Turn an example row into a tuple, either of names or of values"""

    items = row.split('|')
    return [i.strip() for i in items]


def substitute_step(step):
    #  Escape any preexisting {}s
    step = step.replace('{', '{{')
    step = step.replace('}', '}}')
    step = EXAMPLE_TO_FORMAT.sub(r'{\g<1>}', step)
    return step


def substitute_steps(scenario, example):
    return [
        substitute_step(step).format(**example)
        for step in scenario
    ]


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
    if stage not in ('feature', 'scenario', 'step'):
        raise ValueError(stage)

    return partial(make_hook, timing, stage)


class HookFailedException(Exception):
    pass


def run_hooks(world, tester, result, timing, stage):
    for symbol in dir(world):
        maybe_hook = getattr(world, symbol)
        maybe_hook_timing = getattr(maybe_hook,
                                    'planterbox_hook_timing', set())
        if (
            hasattr(maybe_hook, '__call__')
            and hasattr(maybe_hook_timing, '__iter__')
            and (timing, stage) in maybe_hook_timing
        ):
            run_hook(tester, result, maybe_hook)


def run_hook(tester, result, hook):
    try:
        hook(tester)
    except KeyboardInterrupt:
        raise
    except SkipTest as e:
        result.addSkip(tester, unicode(e))
        raise HookFailedException('Skipped')
    except Exception as e:
        result.addError(tester, sys.exc_info())
        raise HookFailedException('Error')
