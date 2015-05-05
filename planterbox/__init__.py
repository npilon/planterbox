from functools import partial
from importlib import import_module
import logging
import os
import re
from unittest import (
    TestCase,
    TestSuite,
)

from nose2.events import Plugin

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


class ScenarioTestCase(TestCase):
    pass


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
    fn.planterbox_pattern = re.compile(pattern, re.IGNORECASE)
    return fn


def step(pattern):
    return partial(make_step, pattern)
