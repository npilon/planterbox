Feature: Multiline Tests
    I want to try out a feature with a multiline step.

    Scenario: I need to verify basic arithmetic.
        Given I sum up the following:
            """
            1
            2
            3
            4
            """
        Then the result should be 10


    Scenario: I need to verify basic arithmetic with a named group.
        Given I sum up the following with a named group:
            """
            1
            2
            3
            4
            """
        Then the result should be 10
