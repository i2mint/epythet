"""Fixture for DQ002: entry point without a runnable example.

Every top-level def of an ``__init__``-less fixture counts as an entry point
only when the package ``__init__`` binds it; the fixture loader treats the
module itself as the package, so top-level defs here are entry points.
"""


def no_example(x):  # ruleid: DQ002
    """Return x, without showing it."""
    return x


def with_example(x):  # ok: DQ002
    """Return x.

    >>> with_example(1)
    1
    """
    return x
