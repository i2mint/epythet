"""Level 1: warning-stream parsing, classification, and (when Sphinx is installed) a real build."""

import shutil
import textwrap
from pathlib import Path

import pytest

from epythet.validation import load_ledger, validate
from epythet.validation.build import (
    SphinxBackend,
    parse_warning_line,
    parse_warning_stream,
    warnings_to_findings,
)

STREAM = """\
/p/dol/dol/appendable.py:docstring of dol.appendable:3: WARNING: Definition list ends without a blank line; unexpected unindent. [docutils]
/p/dol/dol/base.py:docstring of dol.base.Store.__getitem__:7: WARNING: Inline emphasis start-string without end-string. [docutils]
/p/dol/docsrc/module_docs/dol.rst:4: WARNING: duplicate object description of dol.Store, other instance in module_docs/dol/base, use :no-index: for one of them
/p/dol/dol/base.py:docstring of dol.base.Store:3: WARNING: Title underline too short.
/p/dol/docsrc/index.rst:12: WARNING: image file not readable: missing.png [image.not_readable]
reading sources... [ 10%] index
WARNING: toctree contains reference to nonexisting document 'nope' [toc.not_readable]
"""


def test_parse_warning_stream_shapes():
    warnings = list(parse_warning_stream(STREAM, project_dir=Path("/p/dol")))
    assert len(warnings) == 6
    first = warnings[0]
    assert (first.file, first.object, first.line, first.type) == (
        "dol/appendable.py",
        "dol.appendable",
        3,
        "docutils",
    )
    assert warnings[2].type is None and "duplicate object" in warnings[2].message
    assert warnings[5].file is None and warnings[5].type == "toc.not_readable"


def test_classification_maps_to_ledger_rules():
    ledger = load_ledger()
    findings = warnings_to_findings(
        parse_warning_stream(STREAM, project_dir=Path("/p/dol")), ledger
    )
    by_rule = {}
    for f in findings:
        by_rule.setdefault(f.rule, []).append(f)
    assert len(by_rule["DR015"]) == 2
    assert len(by_rule["DR025"]) == 1
    assert len(by_rule["DR024"]) == 1
    assert len(by_rule["DR034"]) == 2  # underline + toctree: the catch-all
    assert all(f.level == 1 for f in findings)
    assert by_rule["DR015"][0].object == "dol.appendable"


def test_missing_docsrc_is_a_build_finding(tmp_path):
    result = SphinxBackend(sphinx_build=["true"]).build_warnings(tmp_path)
    assert result.returncode != 0 and "docsrc" in result.log


sphinx = pytest.importorskip("sphinx")


def _docs_project(tmp_path: Path) -> Path:
    project = tmp_path / "buildpkg"
    (project / "buildpkg").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "buildpkg"\nversion = "0.1"\n'
    )
    (project / "buildpkg" / "__init__.py").write_text(
        '"""The package."""\n\n\ndef f(x):\n    """Do a *thing with x."""\n'
    )
    docsrc = project / "docsrc"
    docsrc.mkdir()
    (docsrc / "conf.py").write_text(
        textwrap.dedent(
            """
            import os, sys
            sys.path.insert(0, os.path.abspath(".."))
            project = "buildpkg"
            extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
            html_theme = "basic"
            """
        )
    )
    (docsrc / "index.rst").write_text(
        "buildpkg\n========\n\n.. automodule:: buildpkg\n   :members:\n"
    )
    return project


def test_real_build_reports_docutils_warning(tmp_path):
    project = _docs_project(tmp_path)
    report = validate(
        project, level=2, observe=False, backend=SphinxBackend(outdir=tmp_path / "out")
    )
    assert 1 in report.levels_run
    build = [f for f in report.findings if f.level == 1]
    assert any(f.rule == "DR015" and "emphasis" in f.message.lower() for f in build), (
        report.findings
    )
    assert report.exit_code() in (11, 12)
    assert report.sphinx_version == sphinx.__version__
