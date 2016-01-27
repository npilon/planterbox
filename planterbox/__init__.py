import codecs
from collections import defaultdict
from datetime import datetime
from functools import partial
from importlib import import_module
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

from .parsing import (
    parse_feature,
)

log = logging.getLogger('planterbox')


EXAMPLE_TO_FORMAT = re.compile(r'<(.+?)>')
FEATURE_NAME = re.compile(r'\.feature(?:\:[\d,]+)?$')


class MixedStepParametersException(Exception):
    """Raised when a step mixes positional and named parameters."""
    pass


class UnmatchedStepException(Exception):
    """Raised when a step cannot be found to execute a line from a scenario."""
    pass


class FeatureExcInfo(tuple):
    """exc_info plus extra information used by ScenarioTestCase"""

    @classmethod
    def from_exc_info(cls, exc_info, scenario_index,
                      scenario_name, completed_steps,
                      failed_step):
        self = FeatureExcInfo(exc_info)
        self.scenario_index = scenario_index
        self.scenario_name = scenario_name
        self.completed_steps = completed_steps
        self.failed_step = failed_step
        return self


class FeatureTestCase(TestCase):
    """A test case generated from the scenarios in a feature file."""

    def __init__(self, feature_path, scenario_indexes=None, feature_text=None,
                 config=None):
        super(FeatureTestCase, self).__init__('nota')
        self.feature_path = feature_path
        self.scenario_indexes = scenario_indexes
        self.config = config

        if feature_text is None:
            with codecs.open(feature_path, mode='r', encoding='utf-8') as f:
                feature_text = f.read()

        header_text, self.scenarios = parse_feature(feature_text)
        self.feature_name = header_text[0].strip().replace(
            'Feature:', ''
        ).strip()
        self.feature_doc = [doc.strip() for doc in header_text[1:]]

    def id(self):
        if self.scenario_indexes:
            return self.feature_id() + ':' + ','.join(
                [unicode(i) for i in self.scenario_indexes]
            )
        else:
            return self.feature_id()

    def feature_id(self):
        return '{}:{}'.format(
            self.__module__,
            os.path.basename(self.feature_path),
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
        """Find all steps that have been imported into this feature's module"""
        module = import_module(self.__module__)
        return [
            maybe_step for maybe_step
            in [getattr(module, name) for name in dir(module)]
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

        raise UnmatchedStepException(step)

    def nota(self):
        """Stub method to satisfy TestCase's obsessive need for a test"""

    def run(self, result=None):
        module = import_module(self.__module__)
        try:
            run_hooks(module, self, result, 'before', 'feature')
            self.step_inventory = list(self.harvest_steps())
            try:
                for i, scenario in enumerate(self.scenarios):
                    if (
                        self.scenario_indexes
                        and i not in self.scenario_indexes
                    ):
                        continue

                    (self.scenario_name,
                     scenario_steps,
                     scenario_examples) = scenario
                    result.startTest(self)

                    try:
                        run_hooks(module, self, result, 'before', 'scenario')
                        if scenario_examples:
                            self.run_outline(
                                module=module,
                                index=i,
                                scenario=scenario_steps,
                                examples=scenario_examples,
                                result=result,
                            )
                        else:
                            self.run_scenario(
                                module=module,
                                index=i,
                                scenario=scenario_steps,
                                result=result,
                            )
                        run_hooks(module, self, result, 'after', 'scenario')
                    except HookFailedException:
                        pass  # Failure already registered
                    finally:
                        result.stopTest(self)
                        del self.scenario_name
            finally:
                run_hooks(module, self, result, 'after', 'feature')
        except HookFailedException:
            return  # Failure already registered.

    def run_scenario(self, module, index, scenario, result):
        completed_steps = []
        self.scenario_index = index
        self.step = None
        self.step_function = None
        try:
            for step in scenario:
                step_fn, step_arguments = self.match_step(step)
                self.step = step
                self.step_function = step_fn
                run_hooks(module, self, result, 'before', 'step')
                if isinstance(step_arguments, dict):
                    step_fn(self, **step_arguments)
                else:
                    step_fn(self, *step_arguments)
                completed_steps.append(step)
                run_hooks(module, self, result, 'after', 'step')
            result.addSuccess(self)
        except KeyboardInterrupt:
            raise
        except HookFailedException:
            pass  # Failure already registered
        except self.failureException:
            self.exc_info = FeatureExcInfo.from_exc_info(
                sys.exc_info(),
                scenario_index=index,
                scenario_name=self.scenario_name,
                completed_steps=completed_steps,
                failed_step=step,
            )
            result.addFailure(self, self.exc_info)
            run_hooks(module, self, result, 'after', 'failure')
            del self.exc_info
        except SkipTest as e:
            result.addSkip(self, str(e))
        except:
            self.exc_info = FeatureExcInfo.from_exc_info(
                sys.exc_info(),
                scenario_index=index,
                scenario_name=self.scenario_name,
                completed_steps=completed_steps,
                failed_step=step,
            )
            result.addError(self, self.exc_info)
            run_hooks(module, self, result, 'after', 'error')
            del self.exc_info
        finally:
            del self.scenario_index
            del self.step
            del self.step_function

    def run_outline(self, module, index, scenario, examples, result):
        examples = list(self.load_examples(examples))
        original_scenario_name = self.scenario_name
        for i, example in enumerate(examples):
            if i != 0:
                result.stopTest(self)
                self.scenario_name = '{} <- {}'.format(
                    original_scenario_name, unicode(example))
                result.startTest(self)
            example_scenario = substitute_steps(scenario, example)
            self.run_scenario(
                module=module,
                index=index,
                scenario=example_scenario,
                result=result,
            )

    def shortDescription(self):
        if getattr(self, 'scenario_name', None):
            return self.scenario_name
        else:
            return self.feature_doc[0] if self.feature_doc else None

    def formatTraceback(self, err):
        """Format containing both feature info and traceback info"""
        if isinstance(err, FeatureExcInfo):
            formatted = '\n'.join([
                err.scenario_name.strip()
            ] + [
                '    ' + completed_step.strip() for completed_step
                in err.completed_steps
            ] + [
                '    ' + err.failed_step.strip(),
                exc_info_to_string(err, super(FeatureTestCase, self))
            ])
            return formatted
        else:
            return exc_info_to_string(err, super(FeatureTestCase, self))

    def __str__(self):
        """Display a test's name as the Feature's name"""
        return '{} ({})'.format(self.feature_name, self.id())


class Planterbox(Plugin):
    configSection = 'planterbox'
    commandLineSwitch = (None, 'with-planterbox',
                         'Load tests from .feature files')

    def register(self):
        super(Planterbox, self).register()
        if 'start_time' not in self.config._mvd:

            start_datetime = datetime.now()

            self.config._mvd['start_date']\
                = [start_datetime.strftime("%Y-%m-%d")]
            self.config._mvd['start_time']\
                = [start_datetime.strftime("%H_%M_%S")]
            self.config._items.append(('start_date',
                                       start_datetime.strftime("%Y-%m-%d")))
            self.config._items.append(('start_time',
                                       start_datetime.strftime("%H_%M_%S")))

    def makeSuiteFromFeature(self, module, feature_path,
                             scenario_indexes=None):
        MyTestSuite = transplant_class(TestSuite, module.__name__)

        MyFeatureTestCase = transplant_class(FeatureTestCase, module.__name__)

        return MyTestSuite(
            tests=[
                MyFeatureTestCase(
                    feature_path=feature_path,
                    scenario_indexes=scenario_indexes,
                    config=self.config,
                ),
            ],
        )

    def handleFile(self, event):
        """Produce a FeatureTestSuite from a .feature file."""
        feature_path = event.path
        if os.path.splitext(feature_path)[1] != '.feature':
            return

        event.handled = True

        try:
            feature_package_name = name_from_path(
                os.path.dirname(feature_path))
            feature_module = object_from_name(feature_package_name)[1]
        except:
            return event.loader.failedImport(feature_path)

        return self.makeSuiteFromFeature(
            module=feature_module,
            feature_path=feature_path,
        )

    def registerInSubprocess(self, event):
        event.pluginClasses.insert(0, self.__class__)

    def loadTestsFromNames(self, event):
        is_feature = partial(FEATURE_NAME.search)
        feature_names = list(ifilter(is_feature, event.names))
        event.names = list(ifilterfalse(is_feature, event.names))

        test_suites = list(self._from_names(feature_names))
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

        features = list(self._from_names([event.name]))

        return features[0]

    def _from_names(self, names):
        by_feature = normalize_names(names)

        for (
            feature_package_name, feature_filename
        ), scenario_indexes in sorted(by_feature.iteritems()):
            feature_module = object_from_name(feature_package_name)[1]
            feature_path = os.path.join(
                os.path.dirname(feature_module.__file__), feature_filename
            )

            suite = self.makeSuiteFromFeature(
                module=feature_module,
                feature_path=feature_path,
                scenario_indexes=scenario_indexes,
            )
            yield suite


def make_step(pattern, multiline, fn):
    """Inner decorator for making a function usable as a step."""
    planterbox_prefix = r'^\s*(?:Given|And|When|Then|But)\s+'
    planterbox_patterns = getattr(fn, 'planterbox_patterns', [])

    if multiline:
        if isinstance(multiline, basestring):
            pattern = pattern + r'\n(?P<{}>(?:.|\n)+)'.format(multiline)
        else:
            pattern = pattern + r'\n((?:.|\n)+)'

    planterbox_patterns.append(re.compile(
        planterbox_prefix + pattern, re.IGNORECASE
    ))
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
    if stage not in ('feature', 'scenario', 'step', 'error', 'failure'):
        raise ValueError(stage)

    return partial(make_hook, timing, stage)


class HookFailedException(Exception):
    pass


def run_hooks(module, tester, result, timing, stage):
    for symbol in dir(module):
        maybe_hook = getattr(module, symbol)
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


def normalize_names(names):
    """Normalize a sequence of feature test names.

    Aims to:
    - Collect together separate entries referring to different scenarios in
      the same feature.
    - Order the resulting names in a predictable manner.
    """

    by_feature = defaultdict(set)
    for name in sorted(names):
        name_parts = name.split(':')
        if len(name_parts) == 3:
            scenario_indexes = {int(s) for s in name_parts.pop(-1).split(',')}
            name_parts = tuple(name_parts)
            if name_parts not in by_feature or by_feature[name_parts]:
                by_feature[name_parts].update(scenario_indexes)
        elif len(name_parts) == 2:
            name_parts = tuple(name_parts)
            scenario_indexes = None
            by_feature[name_parts] = set()
        else:
            continue

    return by_feature
