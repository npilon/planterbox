from planterbox import step


@step(r'I squiggly-add {(\d+)} and {(\d+)}')
@step(r'I add (\d+) and (\d+)')
def add(test, a, b):
    a = int(a)
    b = int(b)
    test.result = a + b


@step(r'the result should be (\d+)')
def check_result(test, value):
    value = int(value)
    test.assertEqual(test.result, value)


@step(r'I add x = (?P<x>\d+) and y = (?P<y>\d+) -> (?P<result_name>\w+)')
def add_keywords(test, y, x, result_name):
    y = int(y)
    x = int(x)
    setattr(test, result_name, x + y)


@step(r'I check (?P<result_name>\w+) == (?P<value>\d+)')
def check_result_keyword(test, value, result_name):
    value = int(value)
    test.assertEqual(getattr(test, result_name), value)


@step(r'I sum up the following with a named group:', multiline='numbers')
@step(r'I sum up the following:', multiline=True)
def sum_up(test, numbers):
    numbers = [int(i) for i in numbers.split('\n') if i]
    test.result = sum(numbers)
