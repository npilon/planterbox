from unittest import TestCase

from mock import Mock, patch


class TestFeatureTestCase(TestCase):
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

        mock_world = Mock()
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
            unicode(test_case), 'A Test Feature (mock:foobar.feature)')

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

        mock_world = Mock()
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
            "Scenario: A Test Scenario <- {'y': '1', 'x': '1', 'z': '2'}"
        )
        self.assertEqual(
            formatted_lines[-2],
            """UnmatchedSubstitutionException: "undefined" missing from \
outline example {'y': '1', 'x': '1', 'z': '2'}"""
        )
