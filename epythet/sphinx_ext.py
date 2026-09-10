"""epythet's Sphinx extension: the normalizer, agent link relations and theme CSS.

Listed automatically in the generated configuration
(``extensions = [..., "epythet.sphinx_ext"]``); usable on its own in any
``conf.py`` too. It registers:

- the docstring normalizer on ``autodoc-process-docstring`` (priority 400, so
  it runs before napoleon), see :mod:`epythet.normalizer`;
- the ``<link rel="alternate" type="text/markdown">`` / ``rel="describedby"``
  relations on every HTML page when ``epythet_agent_outputs`` is on, see
  :mod:`epythet.agent_outputs`;
- the theme accent stylesheet ``_static/epythet.css`` when the chosen theme
  takes its colours from CSS variables (``epythet_theme_css``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from epythet.agent_outputs import inject_link_relations
from epythet.normalizer import sphinx_process_docstring

CSS_FILENAME = "epythet.css"


class _DropIgnoredModuleWarnings(logging.Filter):
    """Silence autosummary's notice about stubs we excluded on purpose (``ignore``)."""

    def filter(self, record):
        return "references excluded document" not in record.getMessage()


def write_theme_css(app) -> None:
    """``builder-inited`` hook: materialise the theme CSS into ``_static``."""
    css = getattr(app.config, "epythet_theme_css", "")
    if not css:
        return
    static_dir = Path(app.confdir) / "_static"
    static_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / CSS_FILENAME).write_text(css, encoding="utf-8")


def _link_relations_if_enabled(app, pagename, templatename, context, doctree):
    if getattr(app.config, "epythet_agent_outputs", False):
        inject_link_relations(app, pagename, templatename, context, doctree)


def setup(app):
    """Register epythet's hooks and configuration values."""
    app.add_config_value("epythet_theme_css", "", "html")
    app.add_config_value("epythet_agent_outputs", True, "html")
    app.add_config_value("epythet_normalizer_rules", None, "env")
    app.connect("autodoc-process-docstring", sphinx_process_docstring, priority=400)
    app.connect("builder-inited", write_theme_css)
    app.connect("html-page-context", _link_relations_if_enabled)
    logging.getLogger("sphinx.sphinx.ext.autosummary").addFilter(
        _DropIgnoredModuleWarnings()
    )
    return {"version": "0.2.0", "parallel_read_safe": True, "parallel_write_safe": True}
