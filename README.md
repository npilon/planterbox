# planterbox
A plugin for running behavior-driven tests using [Gherkin](https://github.com/cucumber/cucumber/wiki/Gherkin) inside `nose2`.

## Usage

To enable `planterbox` for your project, you'll want to add the following lines (or similar) to your `unittest.cfg`:

```ini
[unittest]
plugins = planterbox

[planterbox]
always-on = True
```

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

