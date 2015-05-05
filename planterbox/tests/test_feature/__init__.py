from planterbox import step


@step(r'I add (\d+) and (\d+)')
def add(self, a, b):
    a = int(a)
    b = int(b)
    self.result = a + b


@step(r'the result should be (\d+)')
def check_result(self, value):
    value = int(value)
    self.assertEqual(self.result, value)


@step(r'I add x = (?P<x>\d+) and y = (?P<y>\d+) -> (?P<result_name>\w+)')
def add_keywords(self, y, x, result_name):
    y = int(y)
    x = int(x)
    setattr(self, result_name, x + y)


@step(r'I check (?P<result_name>\w+) == (?P<value>\d+)')
def check_result_keyword(self, value, result_name):
    value = int(value)
    self.assertEqual(getattr(self, result_name), value)
