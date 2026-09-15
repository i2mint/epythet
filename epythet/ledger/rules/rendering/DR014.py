"""Fixture for DR014: prose used as a definition term."""


def bad_deeper_continuation():  # ruleid: DR014
    """Do a thing.

    A paragraph that continues
        with a deeper indented line.
    """


def good_same_indent():  # ok: DR014
    """Do a thing.

    A paragraph that continues
    with a line at the same indent.
    """


def good_real_definition_list():  # ok: DR014
    """Do a thing.

    term
        definition of the term
    """


def bad_entry_points_over_indented_block():  # ruleid: DR014
    """Do a thing.

    Main entry points:
        thing: the one to start with
        other: the second one
    """


def good_entry_points_blank_line_then_list():  # ok: DR014
    """Do a thing.

    Main entry points:

    - ``thing``: the one to start with
    - ``other``: the second one
    """
