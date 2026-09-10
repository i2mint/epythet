"""Fixture for DR021: admonition written with a single colon."""


def bad_single_colon():  # ruleid: DR021
    """Do a thing.

    .. note: this text is a comment and never renders.
    """


def good_double_colon():  # ok: DR021
    """Do a thing.

    .. note:: this text renders as a note.
    """


def good_comment_on_purpose():  # ok: DR021
    """Do a thing.

    .. this is a deliberate comment
    """
