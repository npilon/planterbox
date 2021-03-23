Feature: Example Tests
    I want to exercise generation of a test with examples from a feature.
    I want to exercise using a csv file for examples

    Scenario Outline: I need to verify basic arithmetic with examples.
        Given I squiggly-add {<x>} and {<y>}
        Then the result should be <z>
        Examples:
            x | y | z
            1 | 1 | 2
            1 | 2 | 3
            2 | 1 | 3
            2 | 2 | 4


    Scenario Outline: I want to exercise using a csv file for examples
        Given I squiggly-add {<x>} and {<y>}
        Then the result should be <z>
        Examples: 
            file: /tests/test_feature/examples.csv