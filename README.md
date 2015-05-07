# planterbox
A plugin for running behavior-driven tests using [gherkin](https://github.com/cucumber/cucumber/wiki/Gherkin) inside `nose2`.

## Usage

To enable `planterbox` for your project, you'll want to add the following lines (or similar) to your `unittest.cfg`:

```ini
[unittest]
plugins = planterbox

[planterbox]
always-on = True
```

`planterbox` is compatible with `nose2.plugins.mp`.

## Writing Tests

`planterbox` tests exist inside a python package which provides a context or "world" for their execution.
You should write your tests in `.feature` files in the package directory.
`.feature` files have access to all steps defined in or imported into their package's `__init__.py`.
For example, with the directory structure:

```
planterbox/
  tests/
    test_feature/
      __init__.py
      basic.feature
```

If `__init__.py` contains:

```python
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
```

`basic.feature` could contain:

```gherkin
Feature: Basic Tests
    I want to exercise generation of a simple test from a feature.

    Scenario: I need to verify basic arithmetic.
        Given I add 1 and 1
        Then the result should be 2
```

We could then run this test either by running all of the tests in the suite with `nose2` or run it specifically with `nose2 planterbox.tests.test_feature:basic.feature`.
We could even run the first scenario specifically with `nose2 planterbox.tests.test_feature:basic.feature:0`.

## Writing Steps

`planterbox` steps are python functions decorated with `@planterbox.step(PATTERN)`.
`PATTERN` can be a python regular expression, which must start matching expected step text after the [gherkin step prefixes](https://github.com/cucumber/cucumber/wiki/Given-When-Then).

Groups matched within `PATTERN` are provided to the decorated function as arguments.
All steps are provided with the `TestCase` object for the currently executing scenario as their first argument.
Unnamed groups are provided to the step as positional arguments after this.
Named groups will be passed as keyword arguments.
`PATTERN` cannot mix unnamed and named groups.
If any named groups are used, all groups must be named groups.

All the steps in a feature's package will be available to that feature's scenario.
These steps can be defined in the package or imported from somewhere else.
