"""Fixture for DR028: field with no closing colon."""


def bad_missing_colon():  # ruleid: DR028
    """Do a thing.

    :returns
    :raises ValueError
    """


def good_fields():  # ok: DR028
    """Do a thing.

    :returns: a thing
    :raises ValueError: when x is bad
    """
