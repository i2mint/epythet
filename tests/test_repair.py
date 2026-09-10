"""``epythet repair``: literal rewriting, the invariants, dry-run diffs, the write gate, the CLI."""

import ast
import importlib.util
import textwrap

import pytest

import cw
from epythet import normalizer as N
from epythet.repair import (
    SOURCE_SAFE_RULES,
    UNSAFE_RULES,
    apply_span_edits,
    repair,
    repair_command,
    repair_source,
    rewrite_docstring_literal,
    rules_for,
    split_literal,
)
from epythet.tools import repair_package

MODULE = '''\
"""Module with artifacts.
Options:
- one
- two
"""
import os  # keep


def glued(x):
    """Do a thing.
    >>> glued(1)
    1
    """
    return x


def fenced():
    """Run it:
    ```python
    fenced()
    ```
    Returns: nothing, which is
    fine.
    ## Notes
    See [docs](https://example.org/d).
    """


def stars(*args, **kwargs):
    """Takes *args and **kwargs in prose. `single` backticks.

    :param args: things
    """


def escaped():
    """Has a \\n newline.
    >>> escaped()
    """


class K:
    'Single quoted'

    def m(self):
        \'\'\'Triple single.
        >>> K().m()
        \'\'\'
'''

EXPECTED_DIFF = '''\
--- a/mod.py
+++ b/mod.py
@@ -1,5 +1,6 @@
 """Module with artifacts.
 Options:
+
 - one
 - two
 """
@@ -8,6 +9,7 @@
 
 def glued(x):
     """Do a thing.
+
     >>> glued(1)
     1
     """
@@ -16,13 +18,18 @@
 
 def fenced():
     """Run it:
-    ```python
-    fenced()
-    ```
-    Returns: nothing, which is
-    fine.
-    ## Notes
-    See [docs](https://example.org/d).
+
+    .. code-block:: python
+
+        fenced()
+
+    Returns:
+        nothing, which is
+        fine.
+
+    .. rubric:: Notes
+
+    See `docs <https://example.org/d>`_.
     """
 
 
@@ -44,5 +51,6 @@
 
     def m(self):
         \'\'\'Triple single.
+
         >>> K().m()
         \'\'\'
'''


def test_source_safe_rules_exclude_only_the_star_escaper():
    assert N.escape_unmatched_stars not in SOURCE_SAFE_RULES
    assert set(N.DEFAULT_RULES) - set(SOURCE_SAFE_RULES) == {N.escape_unmatched_stars}
    assert "escape_unmatched_stars" in UNSAFE_RULES


def test_split_literal_shapes():
    assert split_literal('r"""x"""') == ("r", '"""', "x", '"""')
    assert split_literal("'''y'''") == ("", "'''", "y", "'''")
    assert split_literal('"z"') == ("", '"', "z", '"')
    assert split_literal("f'{x}'") == ("f", "'", "{x}", "'")
    assert split_literal("nope") is None


@pytest.mark.parametrize(
    "literal,expected_reason",
    [
        ('"""Has \\n escape."""', "non-raw literal with backslashes: escapes would change"),
        ("b'''bytes'''", "bytes or f-string literal"),
        ("'One\\n>>> f()'", "non-raw literal with backslashes: escapes would change"),
    ],
)
def test_unsafe_literals_are_refused_with_a_reason(literal, expected_reason):
    new, reason = rewrite_docstring_literal(literal)
    assert new == literal and reason == expected_reason


def test_single_quoted_docstring_that_would_grow_is_refused():
    literal = "'Text\n>>> f()'"  # a (syntactically odd) single-quoted literal spanning lines
    new, reason = rewrite_docstring_literal(literal)
    assert new == literal and reason == "single-quoted docstring would need a triple-quoted rewrite"


def test_rewrite_keeps_margin_and_closing_line():
    literal = '"""Do a thing.\n        >>> f(1)\n        1\n        """'
    new, reason = rewrite_docstring_literal(literal)
    assert reason is None
    assert new == '"""Do a thing.\n\n        >>> f(1)\n        1\n        """'


def test_rewrite_that_would_change_a_doctest_source_is_refused():
    literal = '"""Text\n\n    >>> f()\n    1\n    """'
    tamper = lambda lines: [line.replace("f()", "g()") for line in lines]  # noqa: E731
    new, reason = rewrite_docstring_literal(literal, rules=[tamper])
    assert reason == "the rewrite would change a doctest's source" and new == literal
    # a fence around a doctest keeps its source, so the rewrite goes ahead
    fenced = '"""Text\n    ```\n    >>> inside_fence()\n    ```\n    """'
    assert rewrite_docstring_literal(fenced)[1] is None


def test_repair_source_dry_run_matches_the_golden_diff(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text(MODULE)
    result = repair_source(MODULE, rules=rules_for("code-block"), path=path)
    assert result.diff() == EXPECTED_DIFF
    assert [e.qualname for e in result.applied] == ["<module>", "glued", "fenced", "K.m"]
    refused = {e.qualname: e.reason for e in result.refused}
    assert refused == {"escaped": "non-raw literal with backslashes: escapes would change"}


def test_repair_source_keeps_the_ast_outside_docstrings():
    result = repair_source(MODULE, rules=rules_for("code-block"))
    assert result.changed
    before, after = ast.parse(MODULE), ast.parse(result.repaired)
    for tree in (before, after):
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                node.value = ""
    assert ast.dump(before) == ast.dump(after)
    assert "import os  # keep" in result.repaired


def test_repair_source_reports_unfixable_findings_when_revalidating():
    from epythet.validation.ledger import PARSE_KINDS, load_ledger

    rules = load_ledger().of_kind(*PARSE_KINDS)
    result = repair_source(MODULE, rules=rules_for("code-block"), ledger_rules=rules)
    by_name = {e.qualname: e for e in result.edits}
    assert "DR010" in by_name["stars"].remaining and not by_name["stars"].applied
    assert by_name["fenced"].fixed == ["DR004", "DR006", "DR029"]
    assert by_name["glued"].fixed == ["DR003"]
    assert {e.qualname for e in result.refused} == {"stars", "escaped"}


def test_fence_style_literal():
    literal = '"""Run:\n    ```bash\n    pip install x\n    ```\n    Done.\n    """'
    new, _ = rewrite_docstring_literal(literal, rules=rules_for("literal"))
    assert new == '"""Run::\n\n        pip install x\n\n    Done.\n    """'


def test_repair_dry_run_writes_nothing(make_project):
    project = make_project("rpkg", {"mod.py": MODULE})
    report = repair(project)
    assert report.counts() == {"files": 2, "files_changed": 1, "docstrings_rewritten": 4, "docstrings_refused": 2, "files_written": 0}
    assert (project / "rpkg" / "mod.py").read_text() == MODULE
    assert report.diff() == EXPECTED_DIFF


def test_repair_write_is_verified_and_idempotent(make_project):
    project = make_project("rpkg", {"mod.py": MODULE})
    report = repair(project, write=True)
    changed = report.changed
    assert len(changed) == 1 and changed[0].written
    assert changed[0].verification == ["doctests: 0 failure(s) before, 0 after"]
    repaired = (project / "rpkg" / "mod.py").read_text()
    assert repaired != MODULE and ">>> glued(1)" in repaired
    again = repair(project, write=True)
    assert again.counts()["docstrings_rewritten"] == 0
    assert (project / "rpkg" / "mod.py").read_text() == repaired


def test_repair_write_restores_a_file_whose_doctests_got_worse(make_project, monkeypatch):
    project = make_project("rpkg", {"mod.py": MODULE})
    calls = iter([(0, 0, "ok"), (1, 2, "***Test Failed*** 2 failures.")])
    monkeypatch.setattr("epythet.repair._doctest_failures", lambda *a, **k: next(calls))
    report = repair(project, write=True)
    assert not report.changed[0].written
    assert report.changed[0].verification[0].startswith("restored: doctest failures went from 0 to 2")
    assert (project / "rpkg" / "mod.py").read_text() == MODULE


def test_repair_accepts_a_single_file(make_project):
    project = make_project("rpkg", {"mod.py": MODULE, "clean.py": '"""Clean."""\n'})
    report = repair(project / "rpkg" / "clean.py")
    assert report.counts()["files"] == 1 and not report.changed


def test_repair_package_delegates_and_keeps_its_shape(make_project, capsys):
    project = make_project("rpkg", {"mod.py": MODULE})
    total = repair_package(str(project / "rpkg"))
    out = capsys.readouterr().out
    assert total == 4
    assert out.startswith("---> This is just a diagnosis: No files are being written to")
    assert "mod.py" in out and "#problems: 4" in out
    assert (project / "rpkg" / "mod.py").read_text() == MODULE
    assert repair_package(str(project / "rpkg"), write_to_files=True) == 4
    assert repair_package(str(project / "rpkg")) == 0


def test_repair_command_exit_codes(make_project, capsys):
    project = make_project("rpkg", {"mod.py": MODULE})
    repair_command(str(project))
    out = capsys.readouterr().out
    assert "+++ b/mod.py" in out and "needs a hand" in out and "dry run" in out
    with pytest.raises(cw.CommandError) as info:
        repair_command(str(project), fence_style="nope")
    assert info.value.code == 2
    with pytest.raises(cw.CommandError) as info:
        repair_command(str(project / "missing"))
    assert info.value.code == 2


@pytest.mark.skipif(importlib.util.find_spec("libcst") is None, reason="needs libcst")
def test_libcst_applier_matches_span_applier():
    from epythet.repair import apply_with_libcst

    span = repair_source(MODULE, rules=rules_for("code-block"), applier=apply_span_edits)
    cst = repair_source(MODULE, rules=rules_for("code-block"), applier=apply_with_libcst)
    assert span.repaired == cst.repaired
