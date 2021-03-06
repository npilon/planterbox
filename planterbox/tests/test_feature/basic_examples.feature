Feature: Basic Tests
    # Some comments that shouldn't be included in feature text
    I want to exercise generation of a simple test from a feature.

    Scenario: I need to verify basic arithmetic.
        # A note about this scenario that isn't a step
        Given I add 1 and 1
        Then the result should be 2

    Scenario: I verify basic arithmetic with fancy keyword arg patterns
        Given I add x = 1 and y = 1 -> z
        # Comment on why we're doing this check.
        Then I check z == 2
