"""Fixture for DR022: bullet list split by mixed markers."""


def bad_mixed_markers():  # ruleid: DR022
    """Do a thing.

    - first item
    - second item
    * third item
    """


def good_one_marker():  # ok: DR022
    """Do a thing.

    - first item
    - second item
    - third item
    """
