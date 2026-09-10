"""Fixture for DR008: bullet list glued to the preceding paragraph."""


def bad_no_blank_line():  # ruleid: DR008
    """Do a thing.

    Main use cases:
    - property caching
    - method caching
    """


def bad_continuation_unindented():  # ruleid: DR008
    """Do a thing.

    - first item
    that continues unindented
    - second item
    """


def good_blank_line():  # ok: DR008
    """Do a thing.

    Main use cases:

    - property caching
    - method caching
    """


def good_minus_in_prose():  # ok: DR008
    """Compute a - b and
    return it - nothing else.
    """
