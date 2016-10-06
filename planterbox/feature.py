"""TestCase subclass for executing the scenarios from a feature"""

import codecs
from importlib import import_module
from itertools import (
    izip,
)
import logging
import os
import re
import sys
from unittest import (
    TestCase,
    SkipTest,
)

from nose2.util import (
    exc_info_to_string,
)

from .exceptions import (
    HookFailedException,
    MixedStepParametersException,
    UnmatchedStepException,
    UnmatchedSubstitutionException,
)
from .parsing import (
    parse_feature,
)

log = logging.getLogger('planterbox')


EXAMPLE_TO_FORMAT = re.compile(r'<(.+?)>')
FEATURE_NAME = re.compile(r'\.feature(?:\:[\d,]+)?$')


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
                hasattr(maybe_step, '__call__') and
                hasattr(maybe_step, 'planterbox_patterns')
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
                        self.scenario_indexes and
                        i not in self.scenario_indexes
                    ):
                        continue

                    (
                        self.scenario_name,
                        scenario_steps,
                        scenario_examples
                    ) = scenario

                    if scenario_examples:
                        scenario_examples = list(self.load_examples(
                            scenario_examples
                        ))
                        self.original_scenario_name = self.scenario_name
                        self.scenario_example_name(scenario_examples[0])

                    result.startTest(self)

                    try:
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
            run_hooks(module, self, result, 'before', 'scenario')
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
            run_hooks(module, self, result, 'after', 'scenario')
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
        for i, example in enumerate(examples):
            if i != 0:
                result.stopTest(self)
                self.scenario_example_name(example)
                result.startTest(self)
            try:
                example_scenario = substitute_steps(scenario, example)
            except UnmatchedSubstitutionException as uso:
                self.exc_info = FeatureExcInfo.from_exc_info(
                    sys.exc_info(),
                    scenario_index=index,
                    scenario_name=self.scenario_name,
                    completed_steps=[],
                    failed_step=uso.step,
                )
                result.addError(self, self.exc_info)
                continue

            self.run_scenario(
                module=module,
                index=index,
                scenario=example_scenario,
                result=result,
            )

    def scenario_example_name(self, example):
        self.scenario_name = '{} <- {}'.format(
            self.original_scenario_name, unicode(example).strip())

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


def example_row(row):
    """Turn an example row into a tuple, either of names or of values"""

    items = row.split('|')
    return [i.strip() for i in items]


def substitute_step(step):
    """Turn gherkin example syntax into python format string"""
    step = step.replace('{', '{{')
    step = step.replace('}', '}}')
    step = EXAMPLE_TO_FORMAT.sub(r'{\g<1>}', step)
    return step


def substitute_steps(scenario, example):
    """Substitute example values into a scenario to produce runnable steps"""
    try:
        return [
            substitute_step(step).format(**example)
            for step in scenario
        ]
    except KeyError as ke:
        raise UnmatchedSubstitutionException(
            step,
            '"{key}" missing from outline example {example}'.format(
                key=ke.message,
                example=example,
            )
        )


def run_hooks(module, tester, result, timing, stage):
    for symbol in dir(module):
        maybe_hook = getattr(module, symbol)
        maybe_hook_timing = getattr(maybe_hook,
                                    'planterbox_hook_timing', set())
        if (
            hasattr(maybe_hook, '__call__') and
            hasattr(maybe_hook_timing, '__iter__') and
            (timing, stage) in maybe_hook_timing
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
