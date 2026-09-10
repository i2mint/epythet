"""Beautiful, correct documentation from a Python package, with no boilerplate.

Point epythet at a project and its conventions (README, docstrings, package
layout, ``pyproject.toml`` metadata) produce the site::

    epythet quickstart PROJECT_DIR --ignore tests/ scrap/ examples/

which writes ``PROJECT_DIR/docsrc/_build/html/``: a landing page that *is* the
README, a nested API tree, a light/dark theme with an accent derived from the
package name, and agent-facing twins (``llms.txt``, a ``.md`` per page, a flat
``<package>.md``, ``objects.inv``).

The same, from Python::

    from epythet import quickstart
    quickstart(PROJECT_DIR, ignore=["tests/"])

Or step by step: :func:`make_docsrc` writes ``docsrc/`` (a two-line ``conf.py``
shim and ``index.md``), :func:`make` runs Sphinx (``html`` by default). All
configuration lives in ``[tool.epythet]`` of ``pyproject.toml``; see
:mod:`epythet.config` for the keys and :mod:`epythet.themes` for the themes.

Rendering fixes for common docstring slips (a doctest glued to the prose above
it, a Markdown fence, ``Returns: text`` on one line, a stray ``*args``) are
applied at build time by :mod:`epythet.normalizer`, so existing docstrings
render correctly without edits.

A repository's agent artifacts (skills, subagents, ``CLAUDE.md`` and friends)
are discovered by convention and rendered as a "For AI agents" page, see
:mod:`epythet.ai_artifacts`; epythet's own skills ship in ``epythet/data/skills``.

GitHub Pages helpers (:func:`check_pages_setup`, :func:`enable_pages`) and
docstring diagnosis tools (:func:`diagnose_doctest_code_blocks`,
:func:`repair_package`) live in :mod:`epythet.tools`.
"""

from epythet.config import DocsConfig, load_config
from epythet.confgen import sphinx_settings
from epythet.scaffold import make_docsrc, make_autodocs, scaffold, PageSpec
from epythet.build import make, build
from epythet.normalizer import normalize_docstring, normalize_text
from epythet.themes import accent_for, choose_theme, resolve_theme, THEMES
from epythet.agent_outputs import write_aggregates
from epythet.ai_artifacts import discover_artifacts, ai_artifacts_page

from epythet.tools import (
    repair_package,
    print_diagnosis,
    diagnose_doctest_code_blocks,
    add_newlines_before_doctests_when_missing,
    pages_config,
    check_pages_setup,
    enable_pages,
    configure_github_pages,
    repo_stub_from_local_dir,
)

from contextlib import suppress

with suppress(ImportError, ModuleNotFoundError):
    from epythet.tools import published_doc_diagnosis_df


def quickstart(project_dir, *, ignore=None):
    """Scaffold ``docsrc`` and build the HTML site; returns the output directory.

    :param project_dir: the project root
    :param ignore: path substrings to skip (default: ``[tool.epythet] ignore``)
    """
    from epythet.cli import quickstart as _quickstart

    return _quickstart(project_dir, ignore=ignore)
