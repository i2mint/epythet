"""Fixture for DR017: parameter list written as a definition list."""


def bad_params_as_definitions(x, y):  # ruleid: DR017
    """Do a thing.

    x
        the x value
    y
        the y value
    """


def good_fields(x, y):  # ok: DR017
    """Do a thing.

    :param x: the x value
    :param y: the y value
    """
