"""Fixture for DR032: docutils reported a problem."""


def bad_unclosed_emphasis():  # ruleid: DR032
    """Do a thing with a stray *asterisk in prose."""


def good_clean():  # ok: DR032
    """Do a thing.

    :param x: the x value

    >>> f(1)
    1
    """
