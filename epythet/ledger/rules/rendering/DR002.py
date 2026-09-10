"""Fixture for DR002: Google section header left in prose."""


def bad_body_not_indented(x, y):  # ruleid: DR002
    """Do a thing.

    Args:
    x: the x value
    y: the y value
    """


def bad_examples_then_doctest(x):  # ruleid: DR002
    """Do a thing.

    Examples:
    >>> f(1)
    1
    """


def good_indented(x, y):  # ok: DR002
    """Do a thing.

    Args:
        x: the x value
        y: the y value

    Returns:
        A thing.
    """


def good_rst_fields(x):  # ok: DR002
    """Do a thing.

    :param x: the x value
    """
