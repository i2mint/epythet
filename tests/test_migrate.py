"""``epythet migrate-style``: field regions, round-trip safety, Google/NumPy output, doctests untouched."""

import importlib.util

import pytest

import cw
from epythet.migrate import convert_fields, field_region, migrate_style, migrate_style_command, rst_fields_to_sections

pytestmark = pytest.mark.skipif(importlib.util.find_spec("docstring_parser") is None, reason="needs docstring_parser")

MODULE = '''\
"""Module."""


def add(x, y=0):
    """Add two numbers.

    :param x: the first, which
        wraps
    :type x: int
    :param y: the second
    :returns: their sum
    :rtype: int
    :raises ValueError: if negative

    >>> add(1, 2)
    3
    """
    return x + y


def kw(x, **opts):
    """Keyword case, must be left alone.

    :param x: the x
    :keyword verbose: chatty
    """


class K:
    def m(self, a):
        """Method.

        :param a: the a

        After prose.
        """
'''

GOOGLE_ADD = '''\
    """Add two numbers.

    Args:
        x (int): the first, which
            wraps
        y: the second

    Returns:
        int: their sum

    Raises:
        ValueError: if negative

    >>> add(1, 2)
    3
    """
'''


def test_field_region_bounds():
    lines = ["Summary.", "", ":param x: the x", "    more", "", ":returns: y", "", "Then prose.", ":param late: no"]
    assert field_region(lines) == (2, 6)
    assert field_region(["No fields."]) is None
    assert field_region([":param x: x", "    >>> not_a_continuation()"]) == (0, 1)


def test_convert_fields_google_and_numpy():
    region = ":param x: the x value\n:type x: int\n:returns: x doubled\n:rtype: int"
    assert convert_fields(region, to="google") == "Args:\n    x (int): the x value\n\nReturns:\n    int: x doubled"
    numpy = convert_fields(region, to="numpy")
    assert numpy.startswith("Parameters\n----------\nx : int\n    the x value")


def test_convert_fields_refuses_what_does_not_round_trip():
    assert convert_fields(":param x: the x\n:keyword verbose: chatty", to="google") is None
    assert convert_fields(":var foo: bar", to="google") is None
    assert convert_fields("no fields here", to="google") is None
    with pytest.raises(ValueError):
        convert_fields(":param x: x", to="epydoc")


def test_rule_converts_only_the_region_and_keeps_doctests():
    rule = rst_fields_to_sections("google")
    lines = MODULE.splitlines()
    out = rule([":param a: the a", "", "After prose.", "", ">>> f()", "1"])
    assert out == ["Args:", "    a: the a", "", "After prose.", "", ">>> f()", "1"]
    assert rule(["Nothing."]) == ["Nothing."]


def test_migrate_style_dry_run_diff(make_project):
    project = make_project("mpkg", {"mod.py": MODULE})
    report = migrate_style(project)
    assert report.counts()["docstrings_rewritten"] == 2
    repaired = report.changed[0].repaired
    assert GOOGLE_ADD in repaired
    assert "        Args:\n            a: the a\n\n        After prose." in repaired
    assert ":keyword verbose: chatty" in repaired  # left alone
    assert (project / "mpkg" / "mod.py").read_text() == MODULE  # dry run


def test_migrate_style_write_then_idempotent(make_project):
    project = make_project("mpkg", {"mod.py": MODULE})
    report = migrate_style(project, write=True)
    assert report.changed[0].written
    assert migrate_style(project, write=True).counts()["docstrings_rewritten"] == 0


def test_migrate_style_to_numpy(make_project):
    project = make_project("mpkg", {"mod.py": MODULE})
    report = migrate_style(project, to="numpy")
    assert "    Parameters\n    ----------\n    x : int\n" in report.changed[0].repaired


def test_migrate_style_command_rejects_bad_target(make_project):
    project = make_project("mpkg", {"mod.py": MODULE})
    with pytest.raises(cw.CommandError) as info:
        migrate_style_command(str(project), to="epydoc")
    assert info.value.code == 2
