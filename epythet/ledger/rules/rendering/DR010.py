"""Fixture for DR010: unbalanced inline markup."""


def bad_unclosed_literal():  # ruleid: DR010
    """Do a thing with ``y and a stray * asterisk."""


def bad_bare_star_args():  # ruleid: DR010
    """Call it as f(*args, **kwargs) and see."""


def good_escaped():  # ok: DR010
    """Call it as ``f(*args, **kwargs)`` and see."""


def good_emphasis():  # ok: DR010
    """Do a *thing* with **emphasis** and ``code``."""
