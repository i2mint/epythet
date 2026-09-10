"""Fixture for DR003: doctest rendered as prose."""


def bad_no_blank_line():  # ruleid: DR003
    """Do a thing.
    >>> f(1)
    1
    """


def bad_after_prose():  # ruleid: DR003
    """Do a thing.

    You can slice with negatives
    >>> s[2:-2]
    [2, 3]
    """


def good_blank_line():  # ok: DR003
    """Do a thing.

    >>> f(1)
    1
    """


def good_prose_mentions_prompt():  # ok: DR003
    """Do a thing; lines starting with the >>> prompt are examples."""
