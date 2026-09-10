"""Fixture for DR001: RST field list leaked into prose."""


def bad_no_blank_line(x):  # ruleid: DR001
    """Do a thing.
    :param x: the x value
    :return: a thing
    """


def good_blank_line(x):  # ok: DR001
    """Do a thing.

    :param x: the x value
    :return: a thing
    """


def good_no_fields(x):  # ok: DR001
    """Do a thing with x, returning a thing."""
