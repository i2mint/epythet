"""Configuration loading: precedence, ``[tool.epythet]`` keys, the legacy 5-tuple."""

import pytest

from epythet.config import ConfigError, DocsConfig, find_package_dir, load_config
from epythet.config_parser import parse_config


def _project(tmp_path, *, pyproject=None, setup_cfg=None, package="pkg"):
    if pyproject is not None:
        (tmp_path / "pyproject.toml").write_text(pyproject)
    if setup_cfg is not None:
        (tmp_path / "setup.cfg").write_text(setup_cfg)
    if package:
        (tmp_path / package).mkdir()
        (tmp_path / package / "__init__.py").write_text('"""Pkg."""\n')
    return tmp_path


PYPROJECT = """
[project]
name = "pkg"
version = "1.0"
description = "A package."
authors = [{name = "Jane Doe"}, {name = "John Roe"}]
[project.urls]
Homepage = "https://github.com/org/pkg"
"""

SETUP_CFG = """
[metadata]
name = pkg
version = 0.9
author = Old Author
copyright = 2020, Old Author
display_name = Old Display
"""


def test_pyproject_fields(tmp_path):
    cfg = load_config(_project(tmp_path, pyproject=PYPROJECT))
    assert cfg.name == "pkg"
    assert cfg.version == "1.0"
    assert cfg.author == "Jane Doe, John Roe"
    assert cfg.description == "A package."
    assert cfg.repo_url == "https://github.com/org/pkg"
    assert cfg.display_name == "pkg"
    assert cfg.copyright == ""
    assert cfg.package_dir == tmp_path / "pkg"
    assert cfg.docsrc_dir == tmp_path / "docsrc"


def test_defaults(tmp_path):
    cfg = load_config(_project(tmp_path, pyproject=PYPROJECT))
    assert cfg.theme == "auto"
    assert cfg.mode == "auto"
    assert cfg.accent == ""
    assert cfg.ignore == ("tests/", "scrap/", "examples/")
    assert cfg.api_generator == "auto"
    assert cfg.agent_outputs is True
    assert cfg.aggregates == ("md",)


def test_tool_epythet_keys(tmp_path):
    cfg = load_config(
        _project(
            tmp_path,
            pyproject=PYPROJECT
            + """
[tool.epythet]
display_name = "Package!"
copyright = "2026, Jane"
theme = "shibuya"
accent = "#ff6600"
mode = "dark"
ignore = ["tests/"]
api_generator = "autoapi"
agent_outputs = false
aggregates = ["md", "pdf"]
[tool.epythet.theme_options]
announcement = "beta"
""",
        )
    )
    assert cfg.display_name == "Package!"
    assert cfg.copyright == "2026, Jane"
    assert cfg.theme == "shibuya"
    assert cfg.accent == "#ff6600"
    assert cfg.mode == "dark"
    assert cfg.ignore == ("tests/",)
    assert cfg.api_generator == "autoapi"
    assert cfg.agent_outputs is False
    assert cfg.aggregates == ("md", "pdf")
    assert cfg.theme_options == {"announcement": "beta"}


def test_pyproject_wins_over_setup_cfg(tmp_path):
    """The 0.1.x precedence bug: setup.cfg silently won when both files existed."""
    cfg = load_config(_project(tmp_path, pyproject=PYPROJECT, setup_cfg=SETUP_CFG))
    assert cfg.version == "1.0"
    assert cfg.author == "Jane Doe, John Roe"


def test_parse_config_resolves_the_project_even_when_given_setup_cfg(tmp_path):
    project = _project(tmp_path, pyproject=PYPROJECT, setup_cfg=SETUP_CFG)
    assert parse_config(project / "setup.cfg") == (
        "pkg",
        "",
        "Jane Doe, John Roe",
        "1.0",
        "pkg",
    )


def test_setup_cfg_only(tmp_path):
    cfg = load_config(_project(tmp_path, setup_cfg=SETUP_CFG))
    assert cfg.legacy_tuple == (
        "pkg",
        "2020, Old Author",
        "Old Author",
        "0.9",
        "Old Display",
    )
    assert parse_config(tmp_path / "setup.cfg") == cfg.legacy_tuple


def test_pyproject_without_project_table_falls_back_to_setup_cfg(tmp_path):
    cfg = load_config(
        _project(tmp_path, pyproject="[tool.other]\nx = 1\n", setup_cfg=SETUP_CFG)
    )
    assert cfg.version == "0.9"


def test_missing_config_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(_project(tmp_path))
    with pytest.raises(FileNotFoundError):
        parse_config(tmp_path / "setup.cfg")


def test_unknown_key_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="Unknown"):
        load_config(
            _project(tmp_path, pyproject=PYPROJECT + "[tool.epythet]\ncolour = 'x'\n")
        )


@pytest.mark.parametrize(
    "bad", ['mode = "sepia"', 'api_generator = "pdoc"', 'aggregates = ["docx"]']
)
def test_invalid_values_are_errors(tmp_path, bad):
    with pytest.raises(ConfigError):
        load_config(
            _project(tmp_path, pyproject=PYPROJECT + f"[tool.epythet]\n{bad}\n")
        )


def test_overrides_win_and_none_is_ignored(tmp_path):
    cfg = load_config(
        _project(tmp_path, pyproject=PYPROJECT), ignore=["x/"], theme=None
    )
    assert cfg.ignore == ("x/",)
    assert cfg.theme == "auto"


def test_package_dir_by_convention_src_layout(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-pkg"\n')
    (tmp_path / "src" / "my_pkg").mkdir(parents=True)
    (tmp_path / "src" / "my_pkg" / "__init__.py").write_text("")
    cfg = load_config(tmp_path)
    assert cfg.package_dir == tmp_path / "src" / "my_pkg"
    assert cfg.package_name == "my_pkg"
    assert find_package_dir(tmp_path, "my-pkg") == tmp_path / "src" / "my_pkg"


def test_package_dir_fallback_to_the_single_top_level_package(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "c5-name"\n')
    for d in ("othername", "tests"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "__init__.py").write_text("")
    assert load_config(tmp_path).package_dir == tmp_path / "othername"


def test_package_dir_override(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "pkg"\n[tool.epythet]\npackage_dir = "lib/pkg"\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.package_dir == tmp_path / "lib" / "pkg"


def test_docs_config_is_frozen(tmp_path):
    cfg = DocsConfig(project_dir=tmp_path, name="x")
    with pytest.raises(Exception):
        cfg.name = "y"
    assert cfg.with_overrides(name="y", theme=None).name == "y"


def test_auto_generator_resolves_by_import_probe(tmp_path, capsys):
    from epythet.config import DocsConfig

    good = tmp_path / "good"
    (good / "goodpkg").mkdir(parents=True)
    (good / "goodpkg" / "__init__.py").write_text('"""Imports fine."""\n')
    cfg = DocsConfig(project_dir=good, name="goodpkg", package_dir="goodpkg")
    assert cfg.api_generator == "auto"
    assert cfg.resolved_api_generator == "autosummary"

    bad = tmp_path / "bad"
    (bad / "badpkg").mkdir(parents=True)
    (bad / "badpkg" / "__init__.py").write_text("import a_dependency_that_is_missing\n")
    cfg = DocsConfig(project_dir=bad, name="badpkg", package_dir="badpkg")
    assert cfg.resolved_api_generator == "autoapi"
    assert "a_dependency_that_is_missing" in capsys.readouterr().err

    pinned = DocsConfig(
        project_dir=bad, name="badpkg", package_dir="badpkg", api_generator="autosummary"
    )
    assert pinned.resolved_api_generator == "autosummary"


def test_empty_ignore_override_keeps_default(tmp_path):
    from epythet.cli import quickstart  # the orchestrator applies the rule
    from epythet.config import DEFAULT_IGNORE, split_ignore

    assert split_ignore([""]) == ()
    assert split_ignore(["", " , "]) == ()
    assert DocsConfig(project_dir="/tmp/x", name="x").ignore == DEFAULT_IGNORE
