from planterbox import (
    step,
    hook,
)


hooks_run = set()


def setUpModule():
    global hooks_run
    hooks_run.add(('setup', 'module'))


def tearDownModule():
    global hooks_run
    hooks_run.add(('teardown', 'module'))
    assert hooks_run == {('setup', 'module'),
                         ('before', 'feature'),
                         ('before', 'scenario'),
                         ('before', 'step'),
                         ('after', 'feature'),
                         ('after', 'scenario'),
                         ('after', 'step'),
                         ('teardown', 'module')
                         }


@hook('before', 'feature')
def before_feature_hook(feature_suite):
    global hooks_run
    hooks_run.add(('before', 'feature'))


@hook('before', 'scenario')
def before_scenario_hook(test):
    global hooks_run
    hooks_run.add(('before', 'scenario'))


@hook('before', 'step')
def before_step_hook(step_text):
    global hooks_run
    hooks_run.add(('before', 'step'))


@step(r'I verify that all before hooks have run')
def verify_before_hooks(test):
    global hooks_run
    assert hooks_run == {('setup', 'module'),
                         ('before', 'feature'),
                         ('before', 'scenario'),
                         ('before', 'step'),
                         }


@hook('after', 'feature')
def after_feature_hook(feature_suite):
    global hooks_run
    hooks_run.add(('after', 'feature'))
    assert hooks_run == {('setup', 'module'),
                         ('before', 'feature'),
                         ('before', 'scenario'),
                         ('before', 'step'),
                         ('after', 'feature'),
                         ('after', 'scenario'),
                         ('after', 'step'),
                         }


@hook('after', 'scenario')
def after_scenario_hook(test):
    global hooks_run
    hooks_run.add(('after', 'scenario'))


@hook('after', 'step')
def after_step_hook(step_text):
    global hooks_run
    hooks_run.add(('after', 'step'))
