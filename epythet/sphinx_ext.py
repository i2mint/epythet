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
  takes its colours from CSS variables (``epythet_theme_css``);
- the build provenance (``epythet_build_info``): the one-line footer appended
  to the landing page, the documented-module counts on the about page, and
  ``build_info.json`` at the site root, see :mod:`epythet.provenance`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from epythet.agent_outputs import inject_link_relations
from epythet.normalizer import sphinx_process_docstring
from epythet.provenance import (
    ABOUT_PAGE_DOCNAME,
    render_footer_line,
    site_counts,
    write_build_info,
)

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


def _is_html_build(app) -> bool:
    return getattr(app.builder, "format", "") == "html"


def _provenance_page_context(app, pagename, templatename, context, doctree):
    """Append the footer line to the landing page and the counts to the about page."""
    info = getattr(app.config, "epythet_build_info", None)
    if not info or not _is_html_build(app) or "body" not in context:
        return
    if pagename == app.config.root_doc:
        has_page = ABOUT_PAGE_DOCNAME in app.env.found_docs
        about_href = f"{ABOUT_PAGE_DOCNAME}.html" if has_page else None
        context["body"] += "\n" + render_footer_line(info, about_href=about_href)
    elif pagename == ABOUT_PAGE_DOCNAME:
        block = _site_counts_html(site_counts(app.env))
        anchor = '<section id="reproduce">'
        if anchor in context["body"]:
            context["body"] = context["body"].replace(anchor, block + "\n" + anchor, 1)
        else:
            context["body"] += "\n" + block


def _site_counts_html(counts: dict) -> str:
    rows = "".join(
        f"<tr><td><p>{label}</p></td><td><p>{value if value is not None else 'unknown'}</p></td></tr>"
        for label, value in (
            ("Modules documented", counts.get("modules_documented")),
            ("Objects documented", counts.get("objects_documented")),
        )
    )
    return (
        '<section id="site"><h2>Site</h2>'
        f'<table class="docutils align-default"><tbody>{rows}</tbody></table></section>'
    )


def _write_build_info(app, exception) -> None:
    """``build-finished`` hook: ``build_info.json`` with the counts filled in."""
    info = getattr(app.config, "epythet_build_info", None)
    if exception is not None or not info or not _is_html_build(app):
        return
    try:
        info = dict(info, site=site_counts(app.env))
        write_build_info(app.outdir, info)
    except Exception as e:  # provenance never fails a build
        logging.getLogger(__name__).warning(
            "epythet: build_info.json not written (%s)", e
        )


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("epythet")
    except PackageNotFoundError:  # pragma: no cover
        return "0"


def setup(app):
    """Register epythet's hooks and configuration values (idempotent)."""
    if getattr(app, "_epythet_setup_done", False):
        return {
            "version": _version(),
            "parallel_read_safe": True,
            "parallel_write_safe": True,
        }
    app._epythet_setup_done = True
    app.add_config_value("epythet_theme_css", "", "html")
    app.add_config_value("epythet_agent_outputs", True, "html")
    # rebuild "": rule lists hold functions or dotted paths; never pickled into the env
    app.add_config_value("epythet_normalizer_rules", None, "")
    app.add_config_value("epythet_provenance", True, "html")
    app.add_config_value("epythet_build_info", None, "html")
    app.connect("autodoc-process-docstring", sphinx_process_docstring, priority=400)
    app.connect("builder-inited", write_theme_css)
    app.connect("html-page-context", _link_relations_if_enabled)
    app.connect("html-page-context", _provenance_page_context)
    app.connect("build-finished", _write_build_info)
    logging.getLogger("sphinx.sphinx.ext.autosummary").addFilter(
        _DropIgnoredModuleWarnings()
    )
    return {
        "version": _version(),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
