"""Fixture for DR031: commented-out doctest."""


def bad_commented_doctest():  # ruleid: DR031
    """Do a thing.

    # >>> f(1)
    # 1
    """


def good_literal_block():  # ok: DR031
    """Do a thing. Currently disabled::

    >>> f(1)
    1
    """


def good_comment_inside_doctest():  # ok: DR031
    """Do a thing.

    >>> # >>> is how the prompt looks
    >>> f(1)
    1
    """
