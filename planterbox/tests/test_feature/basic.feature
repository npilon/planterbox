Feature: Basic Tests
    I want to exercise generation of a simple test from a feature.


    Scenario: I need to verify basic arithmetic.
        Scenario Tag: math1, math2
        Given I add 1 and 1
        Then the result should be 2

    Scenario: I verify basic arithmetic with fancy keyword arg patterns
        Scenario Tag: math3
        Given I add x = 1 and y = 1 -> z
        Then I check z == 2
