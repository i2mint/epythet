"""End-to-end tests for ``validate``: the one-command smoke test, exit codes, formats, CLI grammar."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import cw
from epythet.validation import EXIT_FOR_LEVEL, EXIT_OK, Report, validate, render
from epythet.validation.cli import validate as validate_command
from epythet.validation.model import Finding, levels_for_tier

BAD_MODULE = '''
"""A module with rendering artifacts."""


def leaky(x):
    """Do a thing.
    :param x: the x value
    """


def glued():
    """Do a thing.
    >>> f(1)
    1
    """


def fine(x):
    """Do a thing.

    :param x: the x value

    >>> fine(1)
    """
'''

CLEAN_MODULE = '''
"""A clean module."""


def fine(x):
    """Do a thing.

    :param x: the x value

    >>> fine(1)
    """
'''


def _project(tmp_path: Path, name: str, module_source: str) -> Path:
    project = tmp_path / name
    (project / name).mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        textwrap.dedent(
            f"""
            [project]
            name = "{name}"
            version = "0.0.1"
            """
        )
    )
    (project / name / "__init__.py").write_text('"""The package."""\n')
    (project / name / "mod.py").write_text(module_source)
    return project


@pytest.fixture
def observations(tmp_path):
    return tmp_path / "obs" / "observations.jsonl"


def test_smoke_bad_package_fails_at_parse_level(tmp_path, observations):
    project = _project(tmp_path, "badpkg", BAD_MODULE)
    report = validate(project, level=1, observations_path=observations)
    rules = {f.rule for f in report.findings if f.level == 0.5}
    assert {"DR001", "DR003"} <= rules
    assert report.exit_code() == EXIT_FOR_LEVEL[0.5] == 11
    assert report.levels_run == [0, 0.5]
    assert report.package == "badpkg"
    assert report.objects_checked >= 3
    leaky = next(f for f in report.findings if f.rule == "DR001")
    assert leaky.file == "badpkg/mod.py" and leaky.object == "badpkg.mod.leaky"
    assert leaky.line == 6
    assert observations.exists()
    records = [json.loads(line) for line in observations.read_text().splitlines()]
    assert {r["rule"] for r in records} >= {"DR001", "DR003"}
    assert all(
        r["package"] == "badpkg" and r["package_version"] == "0.0.1" for r in records
    )


def test_clean_package_is_clean_at_parse_level(tmp_path, observations):
    project = _project(tmp_path, "cleanpkg", CLEAN_MODULE)
    report = validate(project, level=1, observations_path=observations)
    assert [f for f in report.findings if f.level == 0.5] == []
    assert report.exit_code() == EXIT_OK
    assert not observations.exists() or observations.read_text() == ""


def test_package_dir_and_import_name_resolve(tmp_path, observations, monkeypatch):
    project = _project(tmp_path, "resolvepkg", CLEAN_MODULE)
    by_dir = validate(
        project / "resolvepkg", level=1, observations_path=observations, observe=False
    )
    assert by_dir.package == "resolvepkg"
    monkeypatch.syspath_prepend(str(project))
    by_name = validate(
        "resolvepkg", level=1, observations_path=observations, observe=False
    )
    assert Path(by_name.package_dir) == (project / "resolvepkg").resolve()


def test_fail_on_threshold_changes_exit_code():
    report = Report("p", "/p", [0, 0.5])
    report.findings = [Finding("DR011", "warning", 0.5, "cite")]
    assert report.exit_code("error") == 0
    assert report.exit_code("warning") == 11
    report.findings.append(Finding("D100", "info", 0, "missing", tool="ruff"))
    assert report.exit_code("info") == 10


def test_levels_2_and_3_are_reserved(tmp_path):
    project = _project(tmp_path, "later", CLEAN_MODULE)
    with pytest.raises(NotImplementedError, match="WP3"):
        validate(project, level=3, observe=False)
    assert levels_for_tier(4) == [0, 0.5, 1, 2, 3]


def test_renderers_agree(tmp_path, observations):
    project = _project(tmp_path, "renderpkg", BAD_MODULE)
    report = validate(project, level=1, observations_path=observations, observe=False)
    table = render(report, "table")
    doc = json.loads(render(report, "json"))
    lines = [json.loads(line) for line in render(report, "jsonl").splitlines()]
    assert "DR001" in table and "DR003" in table
    assert doc["schema_version"] == "1" and doc["levels_run"] == [0, 0.5]
    assert doc["summary"]["error"] >= 2
    assert [f["rule"] for f in doc["findings"]] == [f["rule"] for f in lines]
    assert doc["findings"][0].keys() >= {
        "rule",
        "severity",
        "level",
        "file",
        "line",
        "object",
        "message",
        "fix",
        "autofixable",
    }


def test_cli_grammar():
    parser = cw.mk_parser(validate_command, prog="epythet-validate")
    options = {opt for action in parser._actions for opt in action.option_strings}
    for flag in (
        "--level",
        "--format",
        "--fail-on",
        "--ledger",
        "--style",
        "--no-napoleon",
        "--ignore",
        "--docsrc",
        "--no-observe",
        "--max-per-rule",
        "--output",
    ):
        assert flag in options, sorted(options)
    usage = " ".join(parser.format_usage().split())
    assert usage.endswith("package")


def test_cli_exit_code_and_stderr(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path, "clipkg", BAD_MODULE)
    monkeypatch.setenv("EPYTHET_DATA_DIR", str(tmp_path / "data"))
    code = cw.dispatch(
        validate_command, [str(project), "--level", "1", "--format", "jsonl"]
    )
    out, err = capsys.readouterr()
    assert code == 11
    assert "exit 11" in err
    assert all(json.loads(line)["rule"] for line in out.strip().splitlines())
    code = cw.dispatch(validate_command, [str(project), "--level", "0", "--no-observe"])
    assert code == 0  # ruff/pydoclint findings are below the default error threshold
    assert (tmp_path / "data" / "ledger" / "observations.jsonl").exists()


def test_cli_rejects_unknown_level(tmp_path, capsys):
    code = cw.dispatch(validate_command, [str(tmp_path), "--level", "7"])
    assert code == 2
    assert "--level" in capsys.readouterr().err


def test_python_m_entry_point(tmp_path):
    project = _project(tmp_path, "mainpkg", CLEAN_MODULE)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "epythet.validation",
            str(project),
            "--level",
            "1",
            "--no-observe",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["package"] == "mainpkg"


def test_defs_inside_if_blocks_and_fixture_dirs(tmp_path, observations):
    project = _project(tmp_path, "nestpkg", CLEAN_MODULE)
    (project / "nestpkg" / "cond.py").write_text(
        '"""Conditional defs."""\n\nif True:\n\n    def leaky(x):\n        """Do.\n        :param x: leak\n        """\n'
    )
    data = (
        project / "nestpkg" / "data"
    )  # no __init__.py: not a package, never validated
    data.mkdir()
    (data / "fixture.py").write_text(
        '"""Fixture."""\n\n\ndef bad():\n    """Do.\n    :param x: leak\n    """\n'
    )
    report = validate(project, level=1, observations_path=observations, observe=False)
    leaks = [f for f in report.findings if f.rule == "DR001"]
    assert [f.object for f in leaks] == ["nestpkg.cond.leaky"]
    assert report.objects_checked == 5  # package, mod, mod.fine, cond, cond.leaky


def test_unreadable_file_is_noted(tmp_path, observations):
    project = _project(tmp_path, "brokenpkg", CLEAN_MODULE)
    (project / "brokenpkg" / "broken.py").write_text("def (:\n")
    report = validate(project, level=1, observations_path=observations, observe=False)
    assert any("skipped broken.py" in note for note in report.notes)


def test_explicit_levels_run_parse_only(tmp_path, observations):
    project = _project(tmp_path, "sweeppkg", BAD_MODULE)
    report = validate(
        project, levels=[0.5], observations_path=observations, observe=False
    )
    assert report.levels_run == [0.5]
    assert {f.level for f in report.findings} == {0.5}
    assert "0" not in report.durations


def test_cli_rejects_unknown_style(tmp_path, capsys):
    code = cw.dispatch(validate_command, [str(tmp_path), "--style", "bogus"])
    assert code == 2 and "--style" in capsys.readouterr().err
