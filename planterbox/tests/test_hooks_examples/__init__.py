from planterbox import (
    step,
    hook,
)


@hook('before', 'scenario')
def before_scenario_hook(test):
    if not hasattr(test, 'before_runs'):
        test.before_runs = 0
        test.after_runs = 0
    test.before_runs += 1


@hook('after', 'scenario')
def after_scenario_hook(test):
    test.after_runs += 1


@step(r'My before hook has been run (\d+) times')
def verify_before_hooks(test, num_runs):
    test.assertEqual(test.before_runs, int(num_runs))


@step(r'My after hook should have been run (\d+) times')
def verify_after_hooks(test, num_runs):
    test.assertEqual(test.after_runs, int(num_runs))
