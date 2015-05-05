from unittest import TestCase

from mock import Mock


class TestScenarioTestCase(TestCase):
    def test_error_output(self):
        from planterbox import FeatureTestSuite, step

        test_feature = """Feature: A Test Feature
            Scenario: A Test Scenario
                When I fail a test
        """

        @step(r'I fail a test')
        def fail_test(test):
            test.fail('Expected Failure')

        mock_world = Mock()
        mock_world.fail_test = fail_test

        test_suite = FeatureTestSuite(mock_world, test_feature)

        test_case = test_suite._tests[0]

        def mock_hook(event):
            self.test_event = event

        mock_hooks = Mock(
            setTestOutcome=Mock(
                side_effect=mock_hook,
            ),
            testOutcome=Mock(
                side_effect=mock_hook,
            ),
        )
        mock_result = Mock(session=Mock(hooks=mock_hooks))

        test_case.run(mock_result)

        formatted = test_case.formatTraceback(self.test_event.exc_info)

        formatted_lines = formatted.split('\n')

        self.assertEqual(formatted_lines[0], 'When I fail a test')
        self.assertEqual(formatted_lines[-2],
                         'AssertionError: Expected Failure')
        self.assertEqual(unicode(test_case),
                         'A Test Scenario (A Test Feature)')
