import os.path

from unittest import TestCase


class TestParseFeature(TestCase):
    def test_with_basic(self):
        from . import test_feature
        from planterbox.parsing import parse_feature

        features_dir = os.path.dirname(test_feature.__file__)

        with open(os.path.join(features_dir, 'basic.feature'), mode='r') as f:
            feature_text = f.read()

        features, scenarios = parse_feature(feature_text)

        self.assertEqual(
            [feature.strip() for feature in features],
            ['Feature: Basic Tests',
             'I want to exercise generation of a simple test from a feature.']
        )

        scenario = scenarios[0]
        self.assertEqual(scenario[0].strip(),
                         'Scenario: I need to verify basic arithmetic.')
        self.assertEqual(
            [scen.strip() for scen in scenario[1]],
            ['Given I add 1 and 1',
             'Then the result should be 2']
        )

    def test_with_basic_examples(self):
        from . import test_feature
        from planterbox.parsing import parse_feature

        features_dir = os.path.dirname(test_feature.__file__)
        basic_examples_filename = os.path.join(features_dir,
                                               'basic_examples.feature')

        with open(basic_examples_filename, mode='r') as f:
            feature_text = f.read()

        features, scenarios = parse_feature(feature_text)

        self.assertEqual(
            [feature.strip() for feature in features],
            ['Feature: Basic Tests',
             'I want to exercise generation of a simple test from a feature.']
        )

        scenario = scenarios[0]
        self.assertEqual(scenario[0].strip(),
                         'Scenario: I need to verify basic arithmetic.')
        self.assertEqual(
            [scen.strip() for scen in scenario[1]],
            ['Given I add 1 and 1',
             'Then the result should be 2']
        )
