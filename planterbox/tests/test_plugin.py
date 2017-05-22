import mock
import os.path
import unittest

from planterbox.plugin import (
    normalize_names,
    Planterbox,
    resolve_scenarios,
)


class TestResolveScenarios(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(resolve_scenarios(''), [])

    def test_empty_string_and_whitespace(self):
        self.assertEqual(resolve_scenarios('       \t'), [])

    def test_some_numbers(self):
        self.assertEqual(resolve_scenarios('5,2,4,5'), {2, 4, 5})

    def test_some_names(self):
        self.assertEqual(
            resolve_scenarios('foo,"bar","foo,bar",garply'),
            {'foo', 'bar', 'foo,bar', 'garply'},
        )

    def test_some_mixed(self):
        self.assertEqual(
            resolve_scenarios('5,foo,2,4,"foo,bar",5'),
            {2, 4, 5, 'foo', 'foo,bar'},
        )


class TestNormalizeNames(unittest.TestCase):
    def test_single_feature(self):
        self.assertEqual(
            normalize_names(['example.package:test.feature']),
            {('example.package', 'test.feature'): set()},
        )

    def test_many_features(self):
        self.assertEqual(
            normalize_names([
                'example.package:test.feature',
                'example.package:test2.feature',
                'example2.package:test.feature',
            ]),
            {
                ('example.package', 'test.feature'): set(),
                ('example.package', 'test2.feature'): set(),
                ('example2.package', 'test.feature'): set(),
            },
        )

    def test_single_feature_index_scenario(self):
        self.assertEqual(
            normalize_names(['example.package:test.feature:0']),
            {('example.package', 'test.feature'): {0}},
        )

    def test_single_feature_name_scenario(self):
        self.assertEqual(
            normalize_names(['example.package:test.feature:A Test Scenario']),
            {('example.package', 'test.feature'): {'A Test Scenario'}},
        )

    def test_single_feature_index_many_scenarios(self):
        self.assertEqual(
            normalize_names(['example.package:test.feature:3,0,5']),
            {('example.package', 'test.feature'): {0, 3, 5}},
        )

    def test_single_feature_index_many_scenarios_many_args(self):
        self.assertEqual(
            normalize_names([
                'example.package:test.feature:3,5',
                'example.package:test.feature:0',
            ]),
            {('example.package', 'test.feature'): {0, 3, 5}},
        )

    def test_single_feature_override_first(self):
        self.assertEqual(
            normalize_names([
                'example.package:test.feature',
                'example.package:test.feature:0',
            ]),
            {('example.package', 'test.feature'): set()},
        )

    def test_single_feature_override_later(self):
        self.assertEqual(
            normalize_names([
                'example.package:test.feature:3,5',
                'example.package:test.feature',
            ]),
            {('example.package', 'test.feature'): set()},
        )

    def test_many_features_mixed_index_and_name(self):
        self.assertEqual(
            normalize_names([
                'example.package:test.feature:0,2',
                'example.package:test.feature:42,"foobar"',
                'example2.package:test.feature:garply',
            ]),
            {
                ('example.package', 'test.feature'): {0, 2, 42, 'foobar'},
                ('example2.package', 'test.feature'): {'garply'},
            },
        )


class TestPlanterboxPlugin(unittest.TestCase):
    def setUp(self):
        import planterbox.tests.test_feature as test_feature
        self.test_feature = test_feature
        self.test_feature_path = os.path.dirname(os.path.abspath(
            test_feature.__file__,
        ))

        import planterbox.tests.test_hooks as test_hooks
        self.test_hooks = test_hooks
        self.test_hooks_path = os.path.dirname(os.path.abspath(
            test_hooks.__file__,
        ))

        plugin_patcher = mock.patch.multiple(
            'planterbox.plugin.Planterbox',
            makeSuiteFromFeature=mock.DEFAULT,
            # Short-circuit nose2 attempting to register this instance
            addOption=mock.DEFAULT,
        )
        patched_plugin = plugin_patcher.start()
        self.addCleanup(plugin_patcher.stop)
        self.mock_msff = patched_plugin['makeSuiteFromFeature']
        self.pp = Planterbox()

    def test_single_feature(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            name='planterbox.tests.test_feature:test.feature',
        )
        self.pp.loadTestsFromName(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run=set(),
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_single_feature_names(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=['planterbox.tests.test_feature:test.feature'],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run=set(),
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_many_features(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=[
                'planterbox.tests.test_feature:test.feature',
                'planterbox.tests.test_feature:test2.feature',
                'planterbox.tests.test_hooks:test.feature',
            ],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.assertEqual(
            self.mock_msff.mock_calls,
            [
                mock.call(
                    feature_path=os.path.join(
                        self.test_feature_path, 'test.feature',
                    ),
                    scenarios_to_run=set(),
                    module=self.test_feature,
                ),
                mock.call(
                    feature_path=os.path.join(
                        self.test_feature_path, 'test2.feature',
                    ),
                    scenarios_to_run=set(),
                    module=self.test_feature,
                ),
                mock.call(
                    feature_path=os.path.join(
                        self.test_hooks_path, 'test.feature',
                    ),
                    scenarios_to_run=set(),
                    module=self.test_hooks,
                ),
            ],
        )
        self.assertTrue(mock_event.handled)

    def test_single_feature_index_scenario(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=['planterbox.tests.test_feature:test.feature:0'],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run={0},
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_single_feature_index_many_scenarios(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=['planterbox.tests.test_feature:test.feature:3,0,5'],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run={0, 3, 5},
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_single_feature_index_many_scenarios_many_args(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=[
                'planterbox.tests.test_feature:test.feature:3,5',
                'planterbox.tests.test_feature:test.feature:0',
            ],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run={0, 3, 5},
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_single_feature_override_first(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=[
                'planterbox.tests.test_feature:test.feature',
                'planterbox.tests.test_feature:test.feature:0',
            ],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run=set(),
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_single_feature_override_later(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=[
                'planterbox.tests.test_feature:test.feature:3,5',
                'planterbox.tests.test_feature:test.feature',
            ],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.mock_msff.assert_called_once_with(
            feature_path=os.path.join(
                self.test_feature_path, 'test.feature',
            ),
            scenarios_to_run=set(),
            module=self.test_feature,
        )
        self.assertTrue(mock_event.handled)

    def test_many_features_mixed_index_and_name(self):
        mock_event = mock.Mock()
        mock_event.configure_mock(
            names=[
                'planterbox.tests.test_feature:test.feature:0,2',
                'planterbox.tests.test_feature:test.feature:42,"foobar"',
                'planterbox.tests.test_hooks:test.feature:garply',
            ],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.assertEqual(
            self.mock_msff.mock_calls,
            [
                mock.call(
                    feature_path=os.path.join(
                        self.test_feature_path, 'test.feature',
                    ),
                    scenarios_to_run={0, 2, 42, 'foobar'},
                    module=self.test_feature,
                ),
                mock.call(
                    feature_path=os.path.join(
                        self.test_hooks_path, 'test.feature',
                    ),
                    scenarios_to_run={'garply'},
                    module=self.test_hooks,
                ),
            ],
        )
        self.assertTrue(mock_event.handled)

    def test_many_features_skip_non_feature_names(self):
        mock_event = mock.Mock(
            handled=False,
            extraTests=[],
        )
        mock_event.configure_mock(
            names=[
                'planterbox.tests.test_feature:test.feature:0,2',
                'planterbox.tests.test_plugin',
                'planterbox.tests.test_feature:test.feature:42,"foobar"',
                'planterbox.tests.test_hooks:test.feature:garply',
            ],
        )
        self.pp.loadTestsFromNames(mock_event)
        self.assertEqual(
            self.mock_msff.mock_calls,
            [
                mock.call(
                    feature_path=os.path.join(
                        self.test_feature_path, 'test.feature',
                    ),
                    scenarios_to_run={0, 2, 42, 'foobar'},
                    module=self.test_feature,
                ),
                mock.call(
                    feature_path=os.path.join(
                        self.test_hooks_path, 'test.feature',
                    ),
                    scenarios_to_run={'garply'},
                    module=self.test_hooks,
                ),
            ],
        )
        self.assertFalse(mock_event.handled)
        self.assertEqual(len(mock_event.extraTests), 2)
        self.assertEqual(mock_event.names, ['planterbox.tests.test_plugin'])
