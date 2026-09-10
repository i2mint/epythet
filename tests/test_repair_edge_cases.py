"""Edge cases from the adversarial review of WP3: encodings, tabs, doctest parsing, gates, layouts."""

import json
import textwrap
from pathlib import Path

import pytest

import cw
from epythet.cli import mk_epythet_parser
from epythet.migrate import convert_fields, field_regions, migrate_style
from epythet.repair import IMPORT_FAILED, repair, repair_source, rewrite_docstring_literal
from epythet.tools import repair_package
from epythet.validation.core import resolve_package
from epythet.validation.rendered import dangling_anchors
from epythet.validation.propose import propose, rule_yaml


def _parse(argv):
    return mk_epythet_parser(prog="epythet").parse_args(argv)


def test_ignore_takes_several_values_on_every_command():
    for command in ("validate", "repair", "migrate-style", "sweep"):
        ns = _parse([command, "p", "-i", "tests", "scrap"])
        assert ns.ignore == ["tests", "scrap"], command


def test_ignore_is_a_path_substring_not_characters(make_project):
    project = make_project("pkg", {"mod.py": '"""M."""\n\n\ndef f():\n    """Do.\n    >>> f()\n    """\n', "tests_helper.py": '"""T."""\n\n\ndef g():\n    """Do.\n    >>> g()\n    """\n'})
    report = repair(project, ignore=["tests_"])
    assert [f.path.name for f in report.files] == ["__init__.py", "mod.py"]


def test_crlf_and_bom_are_preserved(make_project):
    project = make_project("pkg", {"mod.py": "x"})
    path = project / "pkg" / "mod.py"
    source = '﻿"""M."""\r\n\r\n\r\ndef f():\r\n    """Do.\r\n    >>> f()\r\n    """\r\n'
    path.write_bytes(source.encode("utf-8"))
    report = repair(project, write=True, run_doctests=False)
    assert report.changed[0].written
    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf") and b"\n" not in data.replace(b"\r\n", b"")
    assert data.count(b"\r\n") == source.count("\r\n") + 1


def test_tab_indented_docstring_keeps_tabs():
    literal = '"""Do.\n\t>>> f()\n\t1\n\t"""'
    new, reason = rewrite_docstring_literal(literal)
    assert reason is None
    assert new == '"""Do.\n\n\t>>> f()\n\t1\n\t"""'


def test_unparseable_doctest_is_refused_not_crashed():
    literal = '"""Do.\n\n      >>> f()\n    1\n    """'  # output less indented than its prompt
    new, reason = rewrite_docstring_literal(literal)
    assert new == literal and reason.startswith("doctest could not parse")
    result = repair_source('def f():\n    ' + literal + "\n")
    assert result.refused and not result.changed


def test_first_line_one_liner_section_uses_the_leading_newline_form():
    import inspect

    from epythet.repair import split_literal

    literal = '"""Returns: the x\n    doubled.\n    """'
    new, reason = rewrite_docstring_literal(literal)
    assert reason is None
    assert new == '"""\n    Returns:\n        the x\n        doubled.\n    """'
    assert inspect.cleandoc(split_literal(new)[2]) == "Returns:\n    the x\n    doubled."
    assert rewrite_docstring_literal(new)[0] == new  # idempotent


def test_form_feed_earlier_in_the_file_does_not_shift_offsets():
    source = "x = 1\n\x0c\ny = 'é'; z = 2\n\n\ndef f():\n    \"\"\"Do.\n    >>> f()\n    \"\"\"\n"
    result = repair_source(source)
    assert result.applied and result.applied[0].qualname == "f"
    assert result.repaired.startswith("x = 1\n\x0c\ny = 'é'; z = 2\n")


def test_unimportable_module_is_written_but_reported_unverified(make_project):
    project = make_project("pkg", {"mod.py": 'from .nowhere import thing  # noqa\n\n\ndef f():\n    """Do.\n    >>> f()\n    """\n'})
    report = repair(project, write=True)
    changed = report.changed[0]
    assert changed.written and changed.verification[0].startswith("not verified")


def test_doctest_gate_uses_the_dotted_import_so_relative_imports_work(make_project):
    project = make_project(
        "pkg",
        {"helper.py": '"""H."""\nVALUE = 1\n', "mod.py": 'from .helper import VALUE\n\n\ndef f():\n    """Do.\n    >>> f()\n    1\n    """\n    return VALUE\n'},
    )
    report = repair(project, write=True)
    assert report.changed[0].verification == ["doctests: 0 failure(s) before, 0 after"]


def test_refused_count_is_stable_across_passes(make_project):
    project = make_project("pkg", {"mod.py": 'def f(*args):\n    """Takes *args.\n    >>> f()\n    """\n'})
    dry = repair(project)
    assert dry.counts()["docstrings_refused"] == 1  # rewritten (blank line) but DR010 remains
    repair(project, write=True, run_doctests=False)
    assert repair(project).counts()["docstrings_refused"] == 1


def test_repair_package_accepts_a_plain_directory(tmp_path, capsys):
    (tmp_path / "a.py").write_text('def f():\n    """Do.\n    >>> f()\n    """\n')
    assert repair_package(str(tmp_path)) == 1
    assert "a.py" in capsys.readouterr().out


# --------------------------------------------------------------------------
# migrate-style
# --------------------------------------------------------------------------

pytest.importorskip("docstring_parser")


def test_untyped_return_has_no_stray_colon():
    assert convert_fields(":param x: the x\n:returns: y", to="google") == "Args:\n    x: the x\n\nReturns:\n    y"


def test_two_field_blocks_are_left_alone_with_a_reason(make_project):
    source = '"""M."""\n\n\ndef f(x, y):\n    """Do.\n\n    :param x: the x\n\n    >>> f(1, 2)\n\n    :param y: the y\n    :returns: z\n    """\n'
    assert len(field_regions(source.splitlines())) == 2
    project = make_project("pkg", {"mod.py": source})
    report = migrate_style(project)
    assert not report.changed
    reasons = [e.reason for f, e in report.refused]
    assert reasons == ["2 separate field blocks; converting one would mix styles"]


# --------------------------------------------------------------------------
# propose, sweep, level 2
# --------------------------------------------------------------------------


def test_proposed_rule_yaml_quotes_every_scalar():
    import yaml

    proposal = {
        "title": "t: with colon # and hash",
        "namespace": "semantics",
        "severity": "info",
        "precision": "low",
        "detector": {"kind": "regex", "node": "paragraph", "pattern": "x"},
        "message": "m",
        "fix": {"hint": "h", "strategy": "x\nseverity: error"},
        "example_bad": "b",
        "example_good": "g",
    }
    data = yaml.safe_load(rule_yaml("DS009", proposal, source="s"))
    assert data["severity"] == "info" and data["fix"]["strategy"] == "x\nseverity: error"


def test_propose_rejects_examples_with_both_triple_quotes(tmp_path):
    reply = {
        "schema_version": "1", "model": "m", "prompt_hash": "0123456789abcdef", "findings": [],
        "proposed_rules": [{
            "title": "T", "namespace": "semantics", "severity": "info", "precision": "low",
            "detector": {"kind": "regex", "node": "paragraph", "pattern": "bad"},
            "message": "m", "example_bad": 'bad """ and \'\'\'', "example_good": "good",
        }],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(reply))
    result = propose(path, overlay=tmp_path / "overlay")
    assert not result.written and "triple quotes" in result.rejected[0]
    assert not list((tmp_path / "overlay").iterdir())


def test_src_layout_manifest_entry_resolves(tmp_path):
    project = tmp_path / "proj"
    (project / "src" / "thing").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\nname = "thing"\nversion = "1"\n')
    (project / "src" / "thing" / "__init__.py").write_text('"""T."""\n')
    resolved = resolve_package(project / "src")
    assert resolved.package_dir == project / "src" / "thing" and resolved.project_dir == project


def test_theme_skip_links_are_not_dangling_anchors():
    html = '<a class="skip-link" href="#content">Skip</a><a href="#id1">x</a>'
    assert dangling_anchors(html) == ["#id1"]


def test_backend_without_render_is_a_warning_not_a_crash(make_project, tmp_path):
    from epythet.validation import load_ledger
    from epythet.validation.build import BuildResult
    from epythet.validation.rendered import run_render_level

    class WarningsOnly:
        name = "mkdocs-ish"

        def versions(self):
            return {}

        def build_warnings(self, project_dir):
            return BuildResult(returncode=0)

    findings, _, artifacts = run_render_level(tmp_path, load_ledger(), backend=WarningsOnly(), outdir=tmp_path / "o")
    assert [f.rule for f in findings] == ["NO_RENDER"] and findings[0].severity == "warning"
