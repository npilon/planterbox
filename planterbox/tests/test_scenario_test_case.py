from unittest import TestCase, TestSuite

from mock import Mock, patch


class TestFeatureTestCase(TestCase):
    def test_error_output(self):
        from planterbox import FeatureTestCase, step

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

        with patch('planterbox.import_module', Mock(return_value=mock_world)):
            test_case.run(mock_result)

        formatted = test_case.formatTraceback(self.exc_info)

        formatted_lines = formatted.split('\n')

        self.assertEqual(formatted_lines[0], 'Scenario: A Test Scenario')
        self.assertEqual(formatted_lines[1], '    When I fail a test')
        self.assertEqual(
            formatted_lines[-2], 'AssertionError: Expected Failure')
        self.assertEqual(
            unicode(test_case), 'A Test Feature (mock:foobar.feature)')
