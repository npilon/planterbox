"""nose2 plugin for discovering and running planterbox features as tests"""

from collections import defaultdict
import csv
from datetime import datetime
from functools import partial
import logging
import os
import re
from unittest import (
    TestSuite,
)

from nose2.events import (
    Plugin,
)
from nose2.util import (
    name_from_path,
    object_from_name,
    transplant_class,
)

from .feature import (
    FeatureTestCase,
)

log = logging.getLogger('planterbox')


EXAMPLE_TO_FORMAT = re.compile(r'<(.+?)>')
FEATURE_NAME = re.compile(r'\.feature(?:\:.+)?$')


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
                             scenarios_to_run=None):
        MyTestSuite = transplant_class(TestSuite, module.__name__)

        MyFeatureTestCase = transplant_class(FeatureTestCase, module.__name__)

        return MyTestSuite(
            tests=[
                MyFeatureTestCase(
                    feature_path=feature_path,
                    scenarios_to_run=scenarios_to_run,
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
                os.path.dirname(feature_path))[0]
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
        feature_names = [test_name for test_name in event.names if
                         is_feature(test_name)]
        event.names = [test_name for test_name in event.names if
                       not is_feature(test_name)]

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
            feature_package_name, feature_filename,
        ), scenarios_to_run in sorted(by_feature.items()):
            feature_module = object_from_name(feature_package_name)[1]
            feature_path = os.path.join(
                os.path.dirname(feature_module.__file__), feature_filename,
            )

            suite = self.makeSuiteFromFeature(
                module=feature_module,
                feature_path=feature_path,
                scenarios_to_run=scenarios_to_run,
            )
            yield suite


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
            scenario_string = name_parts.pop(-1)
            scenarios_to_run = resolve_scenarios(scenario_string)
            name_parts = tuple(name_parts)
            if name_parts not in by_feature or by_feature[name_parts]:
                # Avoid adding specific scenarios if we've explicitly listed
                #  an entire feature
                by_feature[name_parts].update(scenarios_to_run)
        elif len(name_parts) == 2:
            name_parts = tuple(name_parts)
            scenarios_to_run = None  # So... All!
            by_feature[name_parts] = set()
        else:
            continue

    return by_feature


def resolve_scenarios(scenario_string):
    """Convert a comma-separated string of scenarios into a set of scenarios

    Scenarios can be specified as either scenario names (optionally quoted)
    or scenario indexes."""

    scenario_string = scenario_string.strip()
    if not scenario_string:
        return []

    scenario_parser = csv.reader([scenario_string])
    scenarios = next(scenario_parser)
    scenarios = {
        int(s) if s.isdigit() else s for s in scenarios
    }
    return scenarios
