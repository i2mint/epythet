"""Fixture for DQ001: public object without a docstring."""


def undocumented(x):  # ruleid: DQ001
    return x


def documented(x):  # ok: DQ001
    """Return x unchanged."""
    return x


class Blank:  # ruleid: DQ001
    pass
