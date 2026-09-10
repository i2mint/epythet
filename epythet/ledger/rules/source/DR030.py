"""Fixture for DR030: docstring starts directly with a doctest."""


def bad_doctest_first():  # ruleid: DR030
    """>>> f(1)
    1
    """


def bad_doctest_after_blank():  # ruleid: DR030
    """
    >>> f(1)
    1
    """


def good_summary_first():  # ok: DR030
    """Do a thing.

    >>> f(1)
    1
    """
