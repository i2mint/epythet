"""Smoke test: a small package with every documented convention builds end to end.

This is the one-command test in code form: ``quickstart`` on a fresh project with
no per-repo configuration must produce the landing page from the README (badge,
relative image, GitHub alert), a nested API tree, both docstring styles rendered,
normalized doctests, the agent outputs and the aggregate. It runs Sphinx twice
(HTML, then the Markdown pass for the twins), so it takes a few seconds.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from epythet import PageSpec, quickstart
from epythet.build import BuildError, build, make
from epythet.config import ConfigError, load_config
from epythet.scaffold import make_docsrc, scaffold
from epythet.templates import CONF_SHIM_MARKER

README = """\
# demo

[![PyPI](https://img.shields.io/pypi/v/demo.svg)](https://pypi.org/project/demo/)

![logo](misc/logo.png)

> [!NOTE]
> A GitHub alert.

```mermaid
graph LR; a --> b
```

## Install

```bash
pip install demo
```
"""

PYPROJECT = """\
[project]
name = "demo"
version = "0.1.0"
description = "A demo package."
authors = [{name = "Jane Doe"}]
[project.urls]
Homepage = "https://github.com/org/demo"
"""

INIT = '''"""The demo package: top-level docstring."""

from demo.core import add  # facade re-export
'''

CORE = '''"""Core functions, with the docstring habits epythet normalizes."""


def add(x: int, y: int) -> int:
    """Add two numbers.

    Args:
        x: the first number
        y: the second number

    Returns: the sum of both, which is
    an integer.

    Works with *args and **kwargs too. Example:
    >>> add(1, 2)
    3
    """
    return x + y


def sub(x, y):
    """Subtract.

    :param x: the first number
    :param y: the second number
    :return: x minus y

    ```python
    sub(3, 1)
    ```
    """
    return x - y
'''

DEEP = '''"""A module in a subpackage, to prove the tree nests."""


def deep():
    """Return the string ``deep``.

    >>> deep()
    'deep'
    """
    return "deep"
'''

TEST_MODULE = (
    '"""Should be ignored: it lives under tests/."""\n\ndef helper():\n    return 1\n'
)


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("demo")
    (root / "pyproject.toml").write_text(PYPROJECT)
    (root / "README.md").write_text(README)
    (root / "misc").mkdir()
    (root / "misc" / "logo.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    pkg = root / "demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(INIT)
    (pkg / "core.py").write_text(CORE)
    (pkg / "sub").mkdir()
    (pkg / "sub" / "__init__.py").write_text('"""Subpackage."""\n')
    (pkg / "sub" / "deep.py").write_text(DEEP)
    (pkg / "tests").mkdir()
    (pkg / "tests" / "__init__.py").write_text("")
    (pkg / "tests" / "test_x.py").write_text(TEST_MODULE)
    _git_init(root, remote="https://github.com/org/demo.git", tag="v0.1.0")
    (pkg / "core.py").write_text(CORE + "\n# uncommitted change: the tree is dirty\n")
    return root


def _git_init(root: Path, *, remote: str, tag: str) -> None:
    git = ["git", "-c", "user.email=jane@example.com", "-c", "user.name=Jane"]
    for args in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        ["commit", "-qm", "init"],
        ["remote", "add", "origin", remote],
        ["tag", tag],
    ):
        subprocess.run([*git, *args], cwd=root, check=True, capture_output=True)


@pytest.fixture(scope="module")
def site(project) -> Path:
    html = quickstart(project, ignore=["tests/"])
    assert html == project / "docsrc" / "_build" / "html"
    return html


def test_docsrc_is_a_thin_shim(project, site):
    conf = (project / "docsrc" / "conf.py").read_text()
    assert CONF_SHIM_MARKER in conf
    assert "extensions" not in conf  # nothing generated inline: the module is the SSOT
    index = (project / "docsrc" / "index.md").read_text()
    assert "{include} ../README.md" in index
    assert "demo.md" in index


def test_landing_page_is_the_readme(site):
    index = (site / "index.html").read_text()
    assert "<h1>demo" in index
    assert 'src="https://img.shields.io/pypi/v/demo.svg"' in index
    assert "_images/logo.png" in index and (site / "_images" / "logo.png").is_file()
    assert 'class="admonition note"' in index
    assert 'class="mermaid"' in index
    assert '<link rel="alternate" type="text/markdown" href="index.html.md">' in index
    assert 'href="demo.md"' in index


def test_api_tree_is_nested_and_ignores_tests(site):
    pages = {p.name for p in (site / "_autosummary").glob("*.html")}
    assert {
        "demo.html",
        "demo.core.html",
        "demo.sub.html",
        "demo.sub.deep.html",
    } <= pages
    assert not any("tests" in p for p in pages)
    assert "tests" not in (site / "_autosummary" / "demo.html").read_text()
    core = (site / "_autosummary" / "demo.core.html").read_text()
    assert (
        '<link rel="alternate" type="text/markdown" href="demo.core.html.md">' in core
    )
    assert '<link rel="describedby" href="../llms.txt"' in core
    index = (site / "index.html").read_text()
    assert "toctree-l3" in index  # api -> demo -> demo.core / demo.sub -> ...


def test_both_docstring_styles_render_as_field_lists(site):
    core = (site / "_autosummary" / "demo.core.html").read_text()
    assert core.count('class="field-list') >= 2
    assert "Parameters" in core and "Returns" in core
    assert "the sum of both" in core  # the one-liner Returns became a section


def test_normalizer_effects(site):
    core = (site / "_autosummary" / "demo.core.html").read_text()
    assert 'class="doctest' in core  # doctest after prose is a doctest block
    assert "problematic" not in core  # no *args emphasis error
    assert 'class="highlight-python' in core  # the fence became a code block
    assert "```" not in core


def test_agent_outputs_and_aggregate(site):
    assert (site / "llms.txt").is_file()
    assert (site / "index.html.md").is_file()
    assert (site / "_autosummary" / "demo.core.html.md").is_file()
    assert (site / "objects.inv").is_file()
    aggregate = (site / "demo.md").read_text()
    assert "Add two numbers" in aggregate and "deep" in aggregate
    assert not (site / "llms-full.txt").exists()
    assert "demo.md" in (site / "llms.txt").read_text()


def test_provenance_footer_page_and_json(project, site):
    """WP7: the landing line, the orphan about page and build_info.json agree."""
    info = json.loads((site / "build_info.json").read_text())
    git = info["git"]
    assert info["schema_version"] == 1 and info["package"]["version"] == "0.1.0"
    assert (
        git["branch"] == "main" and git["tags"] == ["v0.1.0"] and git["dirty"] is True
    )
    assert git["commit_url"] == f"https://github.com/org/demo/commit/{git['commit']}"
    assert info["site"]["modules_documented"] >= 4
    assert info["site"]["objects_documented"] >= 2
    assert info["pypi"]["checked"] is False  # conftest turns the lookup off
    assert (
        info["alignment"]["aligned"] is False
        and "uncommitted" in info["alignment"]["notes"][0]
    )

    index = (site / "index.html").read_text()
    assert index.count('class="epythet-provenance"') == 1
    assert f">{git['short_commit']}+dirty</a> (main) · demo 0.1.0 · " in index
    assert '<a href="about-this-build.html">about this build</a>' in index
    assert (
        'class="epythet-provenance"'
        not in (site / "_autosummary" / "demo.core.html").read_text()
    )

    about = (site / "about-this-build.html").read_text()
    assert "may be misaligned" in about and git["commit"] in about
    assert "Modules documented" in about and about.index(
        "Modules documented"
    ) < about.index('id="reproduce"')
    assert (
        "about-this-build" not in index.split('class="epythet-provenance"')[0]
    )  # not in the nav
    assert (site / "about-this-build.html.md").is_file()
    assert "build_info.json" in (site / "llms.txt").read_text()
    assert (site / "demo.md").read_text().startswith("> built ")
    assert "about-this-build.md" in (project / "docsrc" / ".gitignore").read_text()


def test_provenance_off_and_minimal(project):
    other = project.parent / "noprov"
    shutil.copytree(project, other, ignore=shutil.ignore_patterns("docsrc"))
    (other / "pyproject.toml").write_text(
        PYPROJECT + "[tool.epythet]\nprovenance = false\n"
    )
    html = quickstart(other)
    assert not (html / "build_info.json").exists()
    assert not (html / "about-this-build.html").exists()
    assert "epythet-provenance" not in (html / "index.html").read_text()

    (other / "pyproject.toml").write_text(
        PYPROJECT + '[tool.epythet]\nprovenance = "minimal"\n'
    )
    html = quickstart(other)
    assert (html / "build_info.json").is_file()
    assert not (other / "docsrc" / "about-this-build.md").exists()
    assert not (html / "about-this-build.html").exists()
    index = (html / "index.html").read_text()
    assert (
        "epythet-provenance" in index
        and '<a href="build_info.json">build info</a>' in index
    )


def test_theme_is_deterministic_and_rebuild_is_stable(project, site):
    first = (site / "index.html").read_text()
    make(project, "html")
    assert (site / "index.html").read_text() == first


def test_shibuya_gets_link_relations_from_the_post_build_pass(project):
    other = project.parent / "shibuya"
    shutil.copytree(project, other, ignore=shutil.ignore_patterns("docsrc"))
    (other / "pyproject.toml").write_text(
        PYPROJECT + '[tool.epythet]\ntheme = "shibuya"\n'
    )
    html = quickstart(other)
    for page in ("index.html", "_autosummary/demo.core.html"):
        assert 'type="text/markdown"' in (html / page).read_text()


def test_extra_pages_seam(project):
    other = project.parent / "pages"
    shutil.copytree(project, other, ignore=shutil.ignore_patterns("docsrc"))
    cfg = load_config(other)
    page = PageSpec(
        "agents.md", "<!-- generated by epythet -->\n\n# For AI agents\n\nHello.\n"
    )
    scaffold(cfg, verbose=False, pages=[page])
    assert (other / "docsrc" / "agents.md").is_file()
    index = (other / "docsrc" / "index.md").read_text()
    assert "\napi\nagents\n" in index
    html = build(cfg, "html")
    assert "For AI agents" in (html / "agents.html").read_text()


def test_missing_package_dir_is_a_config_error_before_sphinx(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "nothing-here"\n')
    with pytest.raises(ConfigError, match="package_dir"):
        quickstart(tmp_path)


def test_tool_epythet_theme_and_accent(project):
    """A second project with explicit theme settings builds with them applied."""
    other = project.parent / "themed"
    shutil.copytree(project, other, ignore=shutil.ignore_patterns("docsrc"))
    (other / "pyproject.toml").write_text(
        PYPROJECT + '[tool.epythet]\ntheme = "pydata"\naccent = "#3661ac"\n'
        'copyright = "2026, Jane"\n[tool.epythet.theme_options]\nnavigation_depth = 2\n'
    )
    html = quickstart(other)
    index = (html / "index.html").read_text()
    assert "pydata-sphinx-theme" in index
    assert "2026, Jane" in index
    css = (html / "_static" / "epythet.css").read_text()
    assert "--pst-color-primary: #3661ac" in css


def test_make_docsrc_keeps_a_hand_written_conf(project):
    other = project.parent / "handwritten"
    shutil.copytree(project, other, ignore=shutil.ignore_patterns("docsrc"))
    (other / "docsrc").mkdir()
    (other / "docsrc" / "conf.py").write_text("project = 'mine'\n")
    make_docsrc(other, verbose=False)
    assert (other / "docsrc" / "conf.py").read_text() == "project = 'mine'\n"


def test_build_failure_raises(project):
    other = project.parent / "broken"
    shutil.copytree(project, other, ignore=shutil.ignore_patterns("docsrc"))
    (other / "docsrc").mkdir()
    (other / "docsrc" / "conf.py").write_text("raise RuntimeError('boom')\n")
    with pytest.raises(BuildError):
        make(other, "html")


def test_load_config_sees_the_demo_project(project):
    cfg = load_config(project)
    assert cfg.package_dir == project / "demo"
    assert cfg.repo_url == "https://github.com/org/demo"


# ---------------------------------------------------------------------------
# Fleet robustness (WP5): __all__ of objects, __main__ with argparse, comma ignore
# ---------------------------------------------------------------------------

ALL_INIT = '''"""A package whose __all__ lists objects, not submodules (a third of the fleet)."""

from allpkg.core import thing

__all__ = ["thing", "_listed"]
'''

ARGPARSE_MAIN = '''"""Command line: importing this module parses sys.argv (and exits)."""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("required")
ARGS = parser.parse_args()
'''


@pytest.fixture(scope="module")
def all_project(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("allpkg")
    (root / "pyproject.toml").write_text(PYPROJECT.replace("demo", "allpkg"))
    (root / "README.md").write_text("# allpkg\n")
    pkg = root / "allpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(ALL_INIT)
    (pkg / "core.py").write_text('"""Core."""\n\n\ndef thing():\n    """A thing."""\n')
    (pkg / "extra.py").write_text('"""Not in __all__, still a public module."""\n')
    (pkg / "_private.py").write_text('"""Private: never a page."""\n')
    (pkg / "_listed.py").write_text(
        '"""Private but named in __all__: keeps its page."""\n'
    )
    (pkg / "__main__.py").write_text(ARGPARSE_MAIN)
    (pkg / "tests").mkdir()
    (pkg / "tests" / "__init__.py").write_text("")
    (pkg / "tests" / "test_x.py").write_text(TEST_MODULE)
    (pkg / "scrap").mkdir()
    (pkg / "scrap" / "__init__.py").write_text('"""Scrap."""\n')
    return root


@pytest.fixture(scope="module")
def all_site(all_project) -> Path:
    # The action passes its `ignore` input as ONE comma-joined argument.
    return quickstart(all_project, ignore=["tests/,scrap/"])


def test_comma_joined_ignore_is_split(all_project):
    assert load_config(all_project, ignore=["tests/,scrap/"]).ignore == (
        "tests/",
        "scrap/",
    )


def test_all_of_objects_still_yields_every_public_submodule(all_site):
    pages = {p.name for p in (all_site / "_autosummary").glob("*.html")}
    assert {"allpkg.html", "allpkg.core.html", "allpkg.extra.html"} <= pages
    assert "allpkg._private.html" not in pages
    assert "allpkg._listed.html" in pages  # __all__ publishes it (0.2.3 behaviour kept)


def test_main_and_ignored_modules_get_no_page(all_site):
    pages = {p.name for p in (all_site / "_autosummary").glob("*.html")}
    assert "allpkg.__main__.html" not in pages
    assert not any(".tests." in p or ".scrap." in p for p in pages)
