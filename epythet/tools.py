"""Tools to manipulate documentation elements

>>> docs = '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''
>>>
>>>
>>> new_docs = add_newlines_before_doctests_when_missing(docs)
>>> assert new_docs == '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''

"""

import re
from typing import Iterable

blank_line = re.compile(r"\s*$").match
beginning_of_doctest = re.compile(r"\s*>>>").match


def _ensure_lines(x):
    if isinstance(x, str):
        return x.split("\n")
    return x


# Pattern: BufferStats and append_output_to_input (in lined)
def tag_doctest_blocks_not_preceeded_by_new_lines_alt_2(lines: Iterable[str]):
    """Yields (line, True/False) pairs. True when line is a >>> without newlines before,

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it. To render well through Sphinx, code blocks must be separated from earlier
    text by a blank (only spaces) line.

    This function diagnoses that.
    """


def binary_transition(transitions, state, symbol):
    """Binary state machine transition computation. Computes next state.

    :param transitions: Transition "matrix", in the form of:
        {True: state_inverting_symbols, False: state_inverting_symbols}
    :param state: Current state. True or False
    :param symbol: Incoming symbol
    :return: New state

    >>> transitions = {False: {1, 2}, True: {3}}
    >>> binary_transition(transitions, False, 3)
    False
    >>> binary_transition(transitions, False, 1)
    True
    >>> binary_transition(transitions, True, 1)
    True
    >>> binary_transition(transitions, True, 2)
    True
    >>> binary_transition(transitions, True, 3)
    False
    """
    if symbol in transitions[state]:  # if symbol is in the set of triggering symbols...
        return not state  # reverse the state
    else:
        return state  # else just remain in the same state


# Pattern: BufferStats and append_output_to_input (in lined)
def tag_doctest_blocks_not_preceeded_by_new_lines(lines):
    """Yields (line, True/False) pairs. True when line is a >>> without newlines before,

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it. To render well through Sphinx, code blocks must be separated from earlier
    text by a blank (only spaces) line.

    This function diagnoses that.

    It uses three finite (binary) state machines.
    """

    def line_kind(line):
        if beginning_of_doctest(line):
            return "code_start"
        elif blank_line(line):
            return "blank_line"
        else:
            return "normal_line"

    code_transitions = {True: {"blank_line"}, False: {"code_start"}}

    previous_normal_transitions = {
        True: {"blank_line", "code_start"},
        False: {"normal_line"},
    }

    code, prev_normal, prev_code = False, False, False

    for line in _ensure_lines(lines):
        kind = line_kind(line)
        code = binary_transition(code_transitions, code, kind)
        yield line, code & prev_normal & ~prev_code
        prev_normal = binary_transition(previous_normal_transitions, prev_normal, kind)
        prev_code = binary_transition(code_transitions, prev_code, kind)


def diagnose_doctest_code_blocks(code_string: str):
    """
    Yields lines the start code block and need attention,

    >>> docs = '''
    ... The doctest won't render correctly if it's not preceeded by a blank line:
    ...     >>> like_this
    ...
    ... But with a blank line before a block of doctests, it's fine
    ...
    ... >>> okay
    ...
    ...     Is also detected in indentations
    ...     >>> this_doctest_is_too_close_to_text
    ...     SOME_OUTPUT
    ...     >>> but_this_is_fine
    ...     since it's within a doctest block
    ...
    ... '''
    >>> it = diagnose_doctest_code_blocks(docs)

    You would usually run `next(it)` to check on the first problem, repair, and rerun.
    (Oh, and it's important to rerun, because the line numbers won't be valid anymore
    once you edit the source code_string!).

    But, to doctest this we'll do this:

    >>> list(it)
    [(3, '    >>> like_this'), (10, '    >>> this_doctest_is_too_close_to_text')]

    """

    lines = code_string.split("\n")
    for line_num, (line, needs_attention) in enumerate(
        tag_doctest_blocks_not_preceeded_by_new_lines(lines), 1
    ):
        if needs_attention:
            yield line_num, line


def lines_with_two_new_lines_before_doctests(lines: Iterable[str]):
    r"""Yields the input lines, but interleaving an empty ('') line if a code block
    starts with out an empty line preceeding it

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it.
    """
    for line, needs_attention in tag_doctest_blocks_not_preceeded_by_new_lines(lines):
        if needs_attention:
            yield ""
            yield line
        else:
            yield line


def add_newlines_before_doctests_when_missing(code_string: str):
    r"""Returns the code_string with newlines inserted before code blocks when missing./

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it.

    >>> docs = '''
    ... The doctest won't render correctly if it's not preceeded by a blank line:
    ...     >>> like_this
    ...
    ... But with a blank line before a block of doctests, it's fine
    ...
    ... >>> okay
    ...
    ...     Is also detected in indentations
    ...     >>> this_doctest_is_too_close_to_text
    ...     SOME_OUTPUT
    ...     >>> but_this_is_fine
    ...     since it's within a doctest block
    ...
    ... '''
    >>>
    >>>
    >>> new_docs = add_newlines_before_doctests_when_missing(docs)
    >>> assert new_docs == '''
    ... The doctest won't render correctly if it's not preceeded by a blank line:
    ...
    ...     >>> like_this
    ...
    ... But with a blank line before a block of doctests, it's fine
    ...
    ... >>> okay
    ...
    ...     Is also detected in indentations
    ...
    ...     >>> this_doctest_is_too_close_to_text
    ...     SOME_OUTPUT
    ...     >>> but_this_is_fine
    ...     since it's within a doctest block
    ...
    ... '''


    """
    lines = code_string.split("\n")
    return "\n".join(lines_with_two_new_lines_before_doctests(lines))
