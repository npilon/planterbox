planterbox
==========

.. image:: https://api.travis-ci.org/npilon/planterbox.png?branch=master
        :target: https://travis-ci.org/npilon/planterbox

A plugin for running behavior-driven tests using
`gherkin <https://github.com/cucumber/cucumber/wiki/Gherkin>`__ inside
``nose2``.

Usage
-----

To enable ``planterbox`` for your project, you'll want to add the
following lines (or similar) to your ``unittest.cfg``:

.. code:: ini

    [unittest]
    plugins = planterbox

    [planterbox]
    always-on = True

``planterbox`` is compatible with ``nose2.plugins.mp``.

Writing Tests
-------------

``planterbox`` tests exist inside a python package which provides a
context for their execution. You should write your tests in ``.feature``
files in the package directory. ``.feature`` files have access to all
steps defined in or imported into their package's ``__init__.py``. For
example, with the directory structure:

::

    planterbox/
      tests/
        test_feature/
          __init__.py
          basic.feature

If ``__init__.py`` contains:

.. code:: python

    from planterbox import step


    @step(r'I add (\d+) and (\d+)')
    def add(test, a, b):
        a = int(a)
        b = int(b)
        test.result = a + b


    @step(r'the result should be (\d+)')
    def check_result(test, value):
        value = int(value)
        test.assertEqual(test.result, value)

``basic.feature`` could contain:

.. code:: gherkin

    Feature: Basic Tests
        I want to exercise generation of a simple test from a feature.

        Scenario: I need to verify basic arithmetic.
            Given I add 1 and 1
            Then the result should be 2

We could then run this test either by running all of the tests in the
suite with ``nose2`` or run it specifically with
``nose2 planterbox.tests.test_feature:basic.feature``. We could even run
the first scenario specifically with
``nose2 planterbox.tests.test_feature:basic.feature:0``.

Writing Steps
-------------

``planterbox`` steps are python functions decorated with
``@planterbox.step(PATTERN)``. ``PATTERN`` can be a python regular
expression, which must start matching expected step text after the
`gherkin step
prefixes <https://github.com/cucumber/cucumber/wiki/Given-When-Then>`__.

Groups matched within ``PATTERN`` are provided to the decorated function
as arguments. All steps are provided with the ``ScenarioTestCase``
object for the currently executing scenario as their first argument.
Unnamed groups are provided to the step as positional arguments after
this. Named groups will be passed as keyword arguments. ``PATTERN``
cannot mix unnamed and named groups. If any named groups are used, all
groups must be named groups.

All the steps in a feature's package will be available to that feature's
scenario. These steps can be defined in the package or imported from
somewhere else.

Hooks, Setup, and Teardown
--------------------------

``setUpModule`` and ``tearDownModule`` methods in a feature's
``__init__.py`` will be run before and after all features in that
package, respectively. ``planterbox`` provides some extra hooks for
doing preparation or cleanup. Functions can be registered as hooks by
decorating them with ``@planterbox.hook(TIMING, STAGE)``. ``TIMING`` can
be ``'before'`` or ``'after'`` and ``STAGE`` any of ``'feature'``,
``'scenario'``, ``'step'``, ``'failure'``, or ``'error'``.

All hooks are expected to take one argument: the ``TestCase`` subclass
for the active feature.

As with steps, hooks must be directly present in the feature's
``__init__.py`` in order to be run.

Scenario Outlines
-----------------

``planterbox`` supports scenario outlines. These allow you to execute a
scenario multiple times with different values. For example:

.. code:: gherkin

    Feature: Example Tests
        I want to exercise generation of a test with examples from a feature.

        Scenario Outline: I need to verify basic arithmetic with examples.
            Given I add <x> and <y>
            Then the result should be <z>
            Examples:
                x | y | z
                1 | 1 | 2
                1 | 2 | 3
                2 | 1 | 3
                2 | 2 | 4

Your ``'before'`` and ``'after'`` ``'scenario'`` hooks will only run
once for the entire scenario outline.

Invoking Tests
--------------

You can run tests by allowing nose2's autodiscovery to find all of your tests,
or you can specify specific tests to be run on the command line. When
specifying specific tests, you can either specify an entire package,
an entire feature, or individual scenarios. Individual scenarios can be
specified either by index (from 0) or by name.

.. code::

    nose2 planterbox.tests.test_feature
    nose2 planterbox.tests.test_feature:basic.feature planterbox.tests.test_hooks:hooks.feature
    nose2 planterbox.tests.test_feature:basic.feature:1
    nose2 planterbox.tests.test_feature:basic.feature:0
    nose2 planterbox.tests.test_feature:basic.feature:"I need to verify basic arithmetic"
    nose2 planterbox.tests.test_feature:basic.feature:"I need to verify basic arithmetic."

If your feature includes multiple scenarios with the same name, all will be
run when that name is given. Names with a trailing period can be specified with
or without the trailing period.

Validating Tests
----------------

You can use the ``--planterbox-check-only`` flag to verify that your features
are correct without running them::

  nose2 --planterbox-check-only planterbox.tests.test_feature

  ----------------------------------------------------------------------
  Ran 0 tests in 0.000s

  OK

While a failure would produce a traceback::

  nose2 --planterbox-check-only planterbox.tests.test_feature
  Traceback (most recent call last):
    File "planterbox_ve/bin/nose2", line 11, in <module>
      sys.exit(discover())
    File "nose2/main.py", line 306, in discover
      return main(*args, **kwargs)
    File "nose2/main.py", line 100, in __init__
      super(PluggableTestProgram, self).__init__(**kw)
    File "/opt/python/lib/python3.6/unittest/main.py", line 94, in __init__
      self.parseArgs(argv)
    File "nose2/main.py", line 133, in parseArgs
      self.createTests()
    File "nose2/main.py", line 258, in createTests
      self.testNames, self.module)
    File "nose2/loader.py", line 68, in loadTestsFromNames
      for name in event.names]
    File "nose2/loader.py", line 68, in <listcomp>
      for name in event.names]
    File "nose2/loader.py", line 83, in loadTestsFromName
      result = self.session.hooks.loadTestsFromName(event)
    File "nose2/events.py", line 225, in __call__
      result = getattr(plugin, self.method)(event)
    File "nose2/plugins/loader/discovery.py", line 247, in loadTestsFromName
      return Discoverer.loadTestsFromName(self, event)
    File "nose2/plugins/loader/discovery.py", line 84, in loadTestsFromName
      self._find_tests_in_module(event, module, top_level_dir))
    File "nose2/plugins/loader/discovery.py", line 229, in _find_tests_in_module
      event, full_path, top_level_dir):
    File "nose2/plugins/loader/discovery.py", line 161, in _find_tests_in_dir
      event, path, entry_path, top_level):
    File "nose2/plugins/loader/discovery.py", line 176, in _find_tests_in_file
      result = self.session.hooks.handleFile(evt)
    File "nose2/events.py", line 225, in __call__
      result = getattr(plugin, self.method)(event)
    File "planterbox/planterbox/plugin.py", line 106, in handleFile
      feature_path=feature_path,
    File "planterbox/planterbox/plugin.py", line 75, in makeSuiteFromFeature
      config=self.config,
    File "planterbox/planterbox/feature.py", line 81, in __init__
      self.check_scenarios()
    File "planterbox/planterbox/feature.py", line 227, in check_scenarios
      raise UnmatchedStepException("Unmatched steps:\n" + '\n'.join(unmatched))
  planterbox.exceptions.UnmatchedStepException: Unmatched steps:
          Given I bad 1 and 1
