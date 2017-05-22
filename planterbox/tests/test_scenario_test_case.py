from unittest import TestCase

from mock import Mock, patch

from six import (
    text_type,
)


class TestFeatureTestCase(TestCase):
    def tearDown(self):
        if hasattr(self, 'exc_info'):
            del self.exc_info

    def test_error_output(self):
        from planterbox.feature import FeatureTestCase
        from planterbox import step

        test_feature = """Feature: A Test Feature
            Scenario: A Test Scenario
                When I fail a test
        """

        @step(r'I fail a test')
        def fail_test(test):
            test.fail('Expected Failure')

        mock_world = Mock(
            return_value=None,
        )
        mock_world.__name__ = 'mock'
        mock_world.fail_test = fail_test

        test_case = FeatureTestCase(
            feature_path='foobar.feature',
            feature_text=test_feature,
        )
        test_case.__module__ = 'mock'

        def mock_addFailure(result, exc):
            self.exc_info = exc

        mock_result = Mock(addFailure=Mock(side_effect=mock_addFailure))

        with patch('planterbox.feature.import_module',
                   Mock(return_value=mock_world)):
            test_case.run(mock_result)

        formatted = test_case.formatTraceback(self.exc_info)

        formatted_lines = formatted.split('\n')

        self.assertEqual(formatted_lines[0], 'Scenario: A Test Scenario')
        self.assertEqual(formatted_lines[1], '    When I fail a test')
        self.assertEqual(
            formatted_lines[-2], 'AssertionError: Expected Failure')
        self.assertEqual(
            text_type(test_case), 'A Test Feature (mock:foobar.feature)')

    def test_outline_error(self):
        from planterbox.feature import FeatureTestCase

        test_feature = """Feature: A Test Feature
            Scenario: A Test Scenario
                When I reference an <undefined> example
                Then the rest of this test doesn't matter
                Examples:
                    x | y | z
                    1 | 1 | 2
        """

        mock_world = Mock(
            return_value=None,
        )
        mock_world.__name__ = 'mock'

        test_case = FeatureTestCase(
            feature_path='foobar.feature',
            feature_text=test_feature,
        )
        test_case.__module__ = 'mock'

        def mock_addError(result, exc):
            self.exc_info = exc

        mock_result = Mock(addError=Mock(side_effect=mock_addError))

        with patch('planterbox.feature.import_module',
                   Mock(return_value=mock_world)):
            test_case.run(mock_result)

        formatted = test_case.formatTraceback(self.exc_info)

        formatted_lines = formatted.split('\n')

        self.assertEqual(
            formatted_lines[0],
            "Scenario: A Test Scenario <- {'x': '1', 'y': '1', 'z': '2'}",
        )
        self.assertIn(
            """UnmatchedSubstitutionException: "undefined" missing from \
outline example {'x': '1', 'y': '1', 'z': '2'}""",
            formatted_lines[-2],
        )

    def test_specific_scenario_index(self):
        from planterbox.feature import FeatureTestCase
        from planterbox import step

        test_feature = """Feature: A Test Feature
            Scenario: A Skipped Scenario
                When I fail because I shouldn't be here

            Scenario: A Test Scenario
                When I test a thing
        """

        @step(r"I fail because I shouldn't be here")
        def fail_test(test):
            test.fail('Ran wrong scenairo')

        mock_world = Mock(
            spec=['test_thing', 'fail_test'],
            return_value=None,
        )
        mock_world.__name__ = 'mock'
        mock_world.test_thing = step(r'I test a thing')(Mock(
            planterbox_patterns=[],
        ))
        mock_world.fail_test = fail_test

        test_case = FeatureTestCase(
            feature_path='foobar.feature',
            feature_text=test_feature,
            scenarios_to_run=[1],
        )
        test_case.__module__ = 'mock'

        def mock_addFailure(result, exc):
            self.exc_info = exc

        mock_result = Mock(addFailure=Mock(side_effect=mock_addFailure))

        with patch('planterbox.feature.import_module',
                   Mock(return_value=mock_world)):
            test_case.run(mock_result)

        if hasattr(self, 'exc_info'):
            formatted = test_case.formatTraceback(self.exc_info)

            self.fail(formatted)

        mock_world.test_thing.assert_called_once()

    def test_specific_scenario_name(self):
        from planterbox.feature import FeatureTestCase
        from planterbox import step

        test_feature = """Feature: A Test Feature
            Scenario: A Skipped Scenario
                When I fail because I shouldn't be here

            Scenario: A Test Scenario
                When I test a thing
        """

        @step(r"I fail because I shouldn't be here")
        def fail_test(test):
            test.fail('Ran wrong scenairo')

        mock_world = Mock(
            spec=['test_thing', 'fail_test'],
            return_value=None,
        )
        mock_world.__name__ = 'mock'
        mock_world.test_thing = step(r'I test a thing')(Mock(
            planterbox_patterns=[],
        ))
        mock_world.fail_test = fail_test

        test_case = FeatureTestCase(
            feature_path='foobar.feature',
            feature_text=test_feature,
            scenarios_to_run=['A Test Scenario'],
        )
        test_case.__module__ = 'mock'

        def mock_addFailure(result, exc):
            self.exc_info = exc

        mock_result = Mock(addFailure=Mock(side_effect=mock_addFailure))

        with patch('planterbox.feature.import_module',
                   Mock(return_value=mock_world)):
            test_case.run(mock_result)

        if hasattr(self, 'exc_info'):
            formatted = test_case.formatTraceback(self.exc_info)

            self.fail(formatted)

        mock_world.test_thing.assert_called_once()

    def test_specific_scenario_name_no_period(self):
        from planterbox.feature import FeatureTestCase
        from planterbox import step

        test_feature = """Feature: A Test Feature
            Scenario: A Skipped Scenario.
                When I fail because I shouldn't be here

            Scenario: A Test Scenario.
                When I test a thing
        """

        @step(r'I test a thing')
        def test_thing(test):
            pass

        @step(r"I fail because I shouldn't be here")
        def fail_test(test):
            test.fail('Ran wrong scenairo')

        mock_world = Mock(
            spec=['test_thing', 'fail_test'],
            return_value=None,
        )
        mock_world.__name__ = 'mock'
        mock_world.test_thing = step(r'I test a thing')(Mock(
            planterbox_patterns=[],
        ))
        mock_world.fail_test = fail_test

        test_case = FeatureTestCase(
            feature_path='foobar.feature',
            feature_text=test_feature,
            scenarios_to_run=['A Test Scenario'],
        )
        test_case.__module__ = 'mock'

        def mock_addFailure(result, exc):
            self.exc_info = exc

        mock_result = Mock(addFailure=Mock(side_effect=mock_addFailure))

        with patch('planterbox.feature.import_module',
                   Mock(return_value=mock_world)):
            test_case.run(mock_result)

        if hasattr(self, 'exc_info'):
            formatted = test_case.formatTraceback(self.exc_info)

            self.fail(formatted)

        mock_world.test_thing.assert_called_once()

    def test_specific_scenario_name_multiples(self):
        from planterbox.feature import FeatureTestCase
        from planterbox import step

        test_feature = """Feature: A Test Feature
            Scenario: A Skipped Scenario.
                When I fail because I shouldn't be here

            Scenario: A Test Scenario.
                When I test a thing

            Scenario: A Test Scenario.
                When I test a thing
        """

        @step(r'I test a thing')
        def test_thing(test):
            pass

        @step(r"I fail because I shouldn't be here")
        def fail_test(test):
            test.fail('Ran wrong scenairo')

        mock_world = Mock(
            spec=['test_thing', 'fail_test'],
            return_value=None,
        )
        mock_world.__name__ = 'mock'
        mock_world.test_thing = step(r'I test a thing')(Mock(
            planterbox_patterns=[],
        ))
        mock_world.fail_test = fail_test

        test_case = FeatureTestCase(
            feature_path='foobar.feature',
            feature_text=test_feature,
            scenarios_to_run=['A Test Scenario'],
        )
        test_case.__module__ = 'mock'

        def mock_addFailure(result, exc):
            self.exc_info = exc

        mock_result = Mock(addFailure=Mock(side_effect=mock_addFailure))

        with patch('planterbox.feature.import_module',
                   Mock(return_value=mock_world)):
            test_case.run(mock_result)

        if hasattr(self, 'exc_info'):
            formatted = test_case.formatTraceback(self.exc_info)

            self.fail(formatted)

        self.assertEqual(mock_world.test_thing.call_count, 2)
