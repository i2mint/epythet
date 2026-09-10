"""Fixture for DR005: heading underline leaked into prose."""


def bad_short_underline():  # ruleid: DR005
    """Do a thing.

    Section
    ==
    Body text.
    """


def good_full_underline():  # ok: DR005
    """Do a thing.

    Section
    =======

    Body text.
    """


def good_dashes_in_prose():  # ok: DR005
    """Do a thing -- with a dash -- in prose, and an a == b comparison."""
