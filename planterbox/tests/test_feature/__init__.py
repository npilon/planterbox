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
