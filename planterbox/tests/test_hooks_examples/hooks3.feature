Feature: Example Tests With Hooks
    I want to exercise a test with examples and hooks

    Scenario Outline: I need to make sure before scenario hooks fire before each example
        Given My before hook has been run <x> times
        Then my after hook should have been run <y> times
        Examples:
            x | y
            1 | 0
            2 | 1
            3 | 2
            4 | 3

