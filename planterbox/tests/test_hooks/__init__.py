from planterbox import (
    step,
    hook,
)


hooks_run = []


def setUpModule():
    global hooks_run
    hooks_run.append(('setup', 'module'))


def tearDownModule():
    global hooks_run
    hooks_run.append(('teardown', 'module'))
    assert hooks_run == [('setup', 'module'),
                         ('before', 'feature'),
                         ('before', 'scenario'),
                         ('before', 'step'),
                         ('after', 'step'),
                         ('after', 'scenario'),
                         ('after', 'feature'),
                         ('before', 'feature'),
                         ('before', 'scenario'),
                         ('before', 'step'),
                         ('after', 'step'),
                         ('after', 'scenario'),
                         ('after', 'feature'),
                         ('teardown', 'module'),
                         ]


@hook('before', 'feature')
def before_feature_hook(feature_suite):
    global hooks_run
    hooks_run.append(('before', 'feature'))


@hook('before', 'scenario')
def before_scenario_hook(test):
    global hooks_run
    hooks_run.append(('before', 'scenario'))


@hook('before', 'step')
def before_step_hook(step_text):
    global hooks_run
    hooks_run.append(('before', 'step'))


@step(r'I verify that all before hooks have run')
def verify_before_hooks(test):
    global hooks_run
    if len(hooks_run) == 4:
        test.assertEqual(
            hooks_run,
            [('setup', 'module'),
             ('before', 'feature'),
             ('before', 'scenario'),
             ('before', 'step'),
             ],
        )
    elif len(hooks_run) == 10:
        test.assertEqual(
            hooks_run,
            [('setup', 'module'),
             ('before', 'feature'),
             ('before', 'scenario'),
             ('before', 'step'),
             ('after', 'step'),
             ('after', 'scenario'),
             ('after', 'feature'),
             ('before', 'feature'),
             ('before', 'scenario'),
             ('before', 'step'),
             ],
        )
    else:
        test.fail('Unexpected number of hooks run')


@hook('after', 'feature')
def after_feature_hook(feature_suite):
    global hooks_run
    hooks_run.append(('after', 'feature'))
    if len(hooks_run) == 7:
        assert hooks_run == [('setup', 'module'),
                             ('before', 'feature'),
                             ('before', 'scenario'),
                             ('before', 'step'),
                             ('after', 'step'),
                             ('after', 'scenario'),
                             ('after', 'feature'),
                             ]
    elif len(hooks_run) == 13:
        assert hooks_run == [('setup', 'module'),
                             ('before', 'feature'),
                             ('before', 'scenario'),
                             ('before', 'step'),
                             ('after', 'step'),
                             ('after', 'scenario'),
                             ('after', 'feature'),
                             ('before', 'feature'),
                             ('before', 'scenario'),
                             ('before', 'step'),
                             ('after', 'step'),
                             ('after', 'scenario'),
                             ('after', 'feature'),
                             ]
    else:
        assert False


@hook('after', 'scenario')
def after_scenario_hook(test):
    global hooks_run
    hooks_run.append(('after', 'scenario'))


@hook('after', 'step')
def after_step_hook(step_text):
    global hooks_run
    hooks_run.append(('after', 'step'))
