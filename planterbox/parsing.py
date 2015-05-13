"""Functions for parsing a gherkin-formatted file into usable data structures.
"""

import re

INDENT = re.compile(r'^\s+')
SCENARIO = re.compile(r'^\s+Scenario(?: Outline)?:')
EXAMPLES = re.compile(r'^\s+Examples:')


class UnclosedMultilineStepError(Exception):
    """Raised when a multiline step is not properly closed."""
    pass


def indent_level(line):
    """Determine the indent level of a line.

    Indent level is defined as:
    - Number of whitespace characters at the start of the line
    - Tabs count as four spaces.
    """
    ws_match = INDENT.match(line)
    if ws_match is not None:
        ws = ws_match.group()
        ws = ws.replace('\t', '    ')
        return len(ws)


def starts_scenario(line):
    """Determine if a line signals the start of a scenario."""
    return SCENARIO.match(line)


def starts_examples(line):
    """Determine if a line signals the start of an example block."""
    return EXAMPLES.match(line)


def skipline(line):
    """Determine whether a line is something to skip - a comment or blank"""
    stripped_line = line.strip()
    return not stripped_line or stripped_line.startswith('#')


def parse_feature(feature_text):
    """Parse a feature

    Returning a simple data structure containing:
    - One element containing all of the lines from feature name & advisory text
    - One element containing a list of scenarios
        - Each scenario is a list of lines of the scenario, including the name
    """
    lines = feature_text.split('\n')

    feature = []
    scenarios = []
    scenario = None
    append_index = 1
    scenario_indent = 0
    in_multiline = False

    for line in lines:
        if skipline(line):
            continue

        if scenario is not None:
            if in_multiline:
                if line.strip() == '"""':
                    in_multiline = False
                else:
                    scenario[append_index][-1] += '\n' + line
                continue

            if line.strip() == '"""':
                in_multiline = True
                continue

            line_indent = indent_level(line)
            if line_indent <= scenario_indent:
                scenario = None
                scenario_indent = 0
            elif starts_examples(line):
                append_index = 2
            else:
                scenario[append_index].append(line)

        if scenario is None:  # Not elif - want to handle end-of-scenario
            if starts_scenario(line):
                scenario = [line, [], []]
                append_index = 1
                scenario_indent = indent_level(line)
                scenarios.append(scenario)
            else:
                feature.append(line)

    if in_multiline:
        raise UnclosedMultilineStepError()

    return feature, scenarios
