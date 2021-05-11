"""TestCase subclass for executing the scenarios from a feature"""

from six.moves import (
    cStringIO as StringIO,
)
import csv
from importlib import import_module
import io
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

from six import (
    text_type,
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
from .util import (
    clean_dict_repr,
)

log = logging.getLogger('planterbox')


EXAMPLE_TO_FORMAT = re.compile(r'<(.+?)>')
FEATURE_NAME = re.compile(r'\.feature(?:\:[\d,]+)?$')
FILE_PATH = re.compile(r'^(.+)\/([^\/]+)$')

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

    def __init__(self, feature_path, scenarios_to_run=None, feature_text=None,
                 config=None, tag_list=()):
        super(FeatureTestCase, self).__init__('nota')
        self.feature_path = feature_path
        self.scenarios_to_run = scenarios_to_run
        self.config = config

        if feature_text is None:
            with io.open(feature_path, mode='r', encoding='utf-8') as f:
                feature_text = f.read()

        header_text, self.scenarios = parse_feature(feature_text)
        self.feature_name = header_text[0].strip().replace(
            'Feature:', '',
        ).strip()
        self.feature_doc = [doc.strip() for doc in header_text[1:]]
        self.step_inventory = list(self.harvest_steps())
        self.check_scenarios()
        self.tag_list = check_tag_list(tag_list)


    def id(self):
        if self.scenarios_to_run:
            scenario_string = StringIO()
            csv.writer(
                scenario_string, quoting=csv.QUOTE_NONNUMERIC,
            ).writerow(list(self.scenarios_to_run))
            return self.feature_id() + ':' + scenario_string.getvalue().strip()
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

        if 'Examples file:' in examples[0]:
            if examples[1][-4:] != '.csv':
                raise Exception('Example file must be a csv file.')
            else:
                examples = self.read_file_into_examples(examples[1].strip())

        example_header = example_row(examples[0])

        for example in examples[1:]:
            example_data = example_row(example)
            yield {
                label: datum for label, datum
                in zip(example_header, example_data)
            }


    def read_file_into_examples(self, fname):
        import csv
        import os
        csv_examples = []

        filename = os.path.join(os.path.dirname(self.feature_path), fname.strip())
        print(filename)
        with open(filename) as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                    csv_examples.append(row)

        formatted_list = [' | '.join(example) for example in csv_examples]

        return formatted_list


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
            try:
                for i, scenario in enumerate(self.scenarios):

                    (
                        self.scenario_name,
                        scenario_steps,
                        scenario_examples,
                        scenario_tags,
                    ) = scenario

                    if (not matches_tag(scenario_tags, self.tag_list) or
                        (
                            self.scenarios_to_run and
                            not self.should_run_scenario(i, scenario)
                        )):
                         continue


                    if scenario_examples:
                        scenario_examples = list(
                            self.load_examples(scenario_examples))
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

    def should_run_scenario(self, i, scenario):
        """Decide whether to run this scenario when running a subset"""
        scenario_name = scenario[0].partition(':')[2].strip()

        no_trailing_period = (
            scenario_name[:-1]
            if scenario_name[-1] == '.'
            else scenario_name
        )

        return (
            scenario_name in self.scenarios_to_run or
            no_trailing_period in self.scenarios_to_run or
            i in self.scenarios_to_run
        )

    def check_scenarios(self):
        ''' Verify scenario steps match defined steps'''
        for scenario in (self.scenarios):
            (
                self.scenario_name,
                scenario_steps,
                scenario_examples,
                scenario_tags,
            ) = scenario
            if scenario_examples:
                # Do the example thing
                unmatched = []
                scenario_examples = list(self.load_examples(scenario_examples))
                try:
                    for scenario_example in scenario_examples:
                        substituted_scenario = substitute_steps(scenario_steps, scenario_example)
                        unmatched.extend(self.check_steps(substituted_scenario))
                        break
                except UnmatchedSubstitutionException as ke:
                    raise UnmatchedStepException(ke.args[0])
            else:
                unmatched = self.check_steps(scenario_steps)
            if len(unmatched) > 0:
                # combine all unmatched steps into one string and raise exception with it
                raise UnmatchedStepException("Unmatched steps:\n" + '\n'.join(unmatched))

    def check_steps(self, scenario_steps):
        unmatched = []
        for step in scenario_steps:
            try:
                self.match_step(step)
            except UnmatchedStepException:
                unmatched.append(step)
        return unmatched

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
        except Exception:
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
            self.original_scenario_name, clean_dict_repr(example),
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
                err.scenario_name.strip(),
            ] + [
                '    ' + completed_step.strip() for completed_step
                in err.completed_steps
            ] + [
                '    ' + err.failed_step.strip(),
                exc_info_to_string(err, super(FeatureTestCase, self)),
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
            ke.args[0],
            '"{key}" missing from outline example {example}'.format(
                key=ke.args[0],
                example=clean_dict_repr(example),
            ),
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
        result.addSkip(tester, text_type(e))
        raise HookFailedException('Skipped')
    except Exception as e:
        result.addError(tester, sys.exc_info())
        raise HookFailedException('Error')


def matches_tag(scenario_tags, tag_list):
    ''' If tags indicated on command line, returns True if a Scenario_tag matches
    one given on the command line'''
    if not tag_list:
        return True
    else:
        return set(scenario_tags).intersection(tag_list)


def check_tag_list(tag_list):
    ''' Makes a list of any tags entered on the command line. '''
    tags = []
    if len(tag_list) !=0:
        tags = tag_list[0].split(',')
    return tags