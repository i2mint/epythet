"""Fixture for DR012: Google sections without napoleon (run with napoleon off)."""


def bad_google_no_napoleon(x):  # ruleid: DR012
    """Do a thing.

    Args:
        x: the x value

    Returns:
        A thing.
    """


def good_rst_fields(x):  # ok: DR012
    """Do a thing.

    :param x: the x value
    :returns: a thing
    """


def good_real_definition_list():  # ok: DR012
    """Do a thing.

    term
        definition of the term
    """
