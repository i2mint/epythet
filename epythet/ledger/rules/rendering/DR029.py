"""Fixture for DR029: Google section header with its body on the same line."""


def bad_returns_one_liner():  # ruleid: DR029
    """Do a thing.

    Returns: A subclass of store_cls with two additional methods.
    """


def bad_args_one_liner(x):  # ruleid: DR029
    """Do a thing.

    Args: x, the x value.
    """


def good_returns_section():  # ok: DR029
    """Do a thing.

    Returns:
        A subclass of store_cls with two additional methods.
    """


def good_note_in_prose():  # ok: DR029
    """Do a thing.

    Note: a note in prose is fine; napoleon ignores it and so does this rule.
    """
