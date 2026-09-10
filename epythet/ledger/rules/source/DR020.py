"""Fixture for DR020: backslash in a non-raw docstring."""


def bad_windows_path():  # ruleid: DR020
    """Read the file at C:\temp\new and parse it."""


def good_raw_docstring():  # ok: DR020
    r"""Read the file at C:\temp\new and parse it."""


def good_escaped_star():  # ok: DR020
    """Call with \\*args to pass positionals."""


def good_backslash_in_doctest():  # ok: DR020
    """Do a thing.

    >>> print("a\tb")
    a	b
    """
