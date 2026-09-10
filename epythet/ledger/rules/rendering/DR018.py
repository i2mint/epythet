"""Fixture for DR018: directive content silently deleted."""


def bad_unknown_directive():  # ruleid: DR018
    """Do a thing.

    .. codeblock:: python

        oops = 1
    """


def good_code_block():  # ok: DR018
    """Do a thing.

    .. code-block:: python

        fine = 1
    """


def good_note():  # ok: DR018
    """Do a thing.

    .. note::

        Something to note.
    """
