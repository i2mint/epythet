"""Fixture for DR019: table collapsed to nothing."""


def bad_unequal_borders():  # ruleid: DR019
    """Do a thing.

    ===  ===
    a    b
    ===  ===
    1    2
    ===  =====
    """


def good_table():  # ok: DR019
    """Do a thing.

    ===  ===
    a    b
    ===  ===
    1    2
    ===  ===
    """


def good_heading():  # ok: DR019
    """Do a thing.

    Section
    =======

    Body text.
    """
