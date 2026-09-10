"""Normalizer rules: fixture docstrings in, expected docstrings out.

Each ``tests/normalizer_fixtures/<case>.in`` is a docstring as autodoc hands it
to the ``autodoc-process-docstring`` event; ``<case>.out`` is what the
normalizer must produce. Cases ending in ``_untouched`` pin the promise that
code (doctests, literal blocks, inline literals) and well-formed sections are
never rewritten. Every fixture must also be a fixed point: normalizing the
output again changes nothing.
"""

from pathlib import Path

import pytest

from epythet.normalizer import (
    DEFAULT_RULES,
    line_contexts,
    normalize_docstring,
    normalize_text,
    sphinx_process_docstring,
)

FIXTURES = Path(__file__).parent / "normalizer_fixtures"
CASES = sorted(p.stem for p in FIXTURES.glob("*.in"))


def _case(name):
    return (FIXTURES / f"{name}.in").read_text(), (FIXTURES / f"{name}.out").read_text()


@pytest.mark.parametrize("name", CASES)
def test_fixture(name):
    given, expected = _case(name)
    assert normalize_text(given) == expected


@pytest.mark.parametrize("name", CASES)
def test_fixture_is_a_fixed_point(name):
    _, expected = _case(name)
    assert normalize_text(expected) == expected


@pytest.mark.parametrize("name", [c for c in CASES if c.endswith("_untouched")])
def test_untouched_cases_are_identity(name):
    given, expected = _case(name)
    assert given == expected, "an *_untouched fixture must have identical in/out"


def test_every_rule_is_a_pure_list_function():
    lines = ["Text", ">>> 1", "1"]
    for rule in DEFAULT_RULES:
        copy = list(lines)
        out = rule(copy)
        assert isinstance(out, list)
        assert copy == lines, f"{rule.__name__} mutated its input"


def test_line_contexts_keep_doctest_output_in_the_block():
    contexts = line_contexts([">>> f()", "3", "still output", "", "prose"])
    assert contexts == ["doctest", "doctest", "doctest", "blank", "prose"]


def test_sphinx_hook_rewrites_in_place_and_ignores_options():
    class App:
        class config:
            epythet_normalizer_rules = None

    lines = ["Text", ">>> 1", "1"]
    sphinx_process_docstring(App(), "function", "f", None, object(), lines)
    assert lines == ["Text", "", ">>> 1", "1"]


def test_custom_rule_set():
    lines = normalize_docstring(["Text", ">>> 1"], rules=[])
    assert lines == ["Text", ">>> 1"]


def test_rules_from_conf_may_be_dotted_paths_and_empty_disables():
    class App:
        class config:
            epythet_normalizer_rules = ["epythet.normalizer:escape_unmatched_stars"]

    lines = ["Text *args", ">>> 1"]
    sphinx_process_docstring(App(), "function", "f", None, None, lines)
    assert lines == ["Text \\*args", ">>> 1"]  # only the named rule ran
    App.config.epythet_normalizer_rules = []
    lines = ["Text", ">>> 1"]
    sphinx_process_docstring(App(), "function", "f", None, None, lines)
    assert lines == ["Text", ">>> 1"]
