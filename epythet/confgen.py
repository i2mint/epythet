"""Generate the Sphinx configuration from a :class:`~epythet.config.DocsConfig`.

:func:`sphinx_settings` returns the plain dict a ``conf.py`` would define. The
shim ``docsrc/conf.py`` that :func:`epythet.scaffold.make_docsrc` writes gets
it through ``from epythet.sphinx_conf import *``; tests and tools call it
directly. Every value here is either verified in the v2 research (README
include, nested API tree, typed cross-references, agent twins) or a direct
consequence of the decision record.

>>> from epythet.config import DocsConfig
>>> cfg = DocsConfig(project_dir="/tmp/x", name="x", package_dir="x", theme="furo")
>>> s = sphinx_settings(cfg)
>>> s["html_theme"], s["default_role"], "sphinx.ext.autosummary" in s["extensions"]
('furo', 'code', True)
"""

from __future__ import annotations

from typing import Any

from epythet.agent_outputs import sphinx_settings as _agent_settings
from epythet.config import DocsConfig
from epythet.themes import resolve_theme

#: Extensions every epythet site uses, whatever the API generator.
BASE_EXTENSIONS: tuple[str, ...] = (
    "sphinx.ext.napoleon",  # RST field lists and Google/NumPy sections, together
    "sphinx_autodoc_typehints",  # links types from annotations, TYPE_CHECKING, stubs
    "sphinx.ext.intersphinx",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",  # writes .nojekyll
    "myst_parser",  # Markdown pages; the README becomes the landing page
    "sphinxcontrib.mermaid",
    "sphinx_copybutton",
    "epythet.sphinx_ext",  # normalizer, link relations, theme CSS
)

#: Where the API pages live under ``docsrc`` (and in the site URL).
API_ROOT = "api"

MYST_EXTENSIONS: tuple[str, ...] = (
    "alert",  # GitHub > [!NOTE] blocks (myst-parser >= 5.1)
    "colon_fence",
    "deflist",
    "fieldlist",
    "attrs_inline",
    "attrs_block",
    "html_image",
    "tasklist",
    "strikethrough",
)


def sphinx_settings(config: DocsConfig) -> dict[str, Any]:
    """The complete Sphinx ``conf.py`` namespace for ``config``."""
    theme = resolve_theme(
        config.package_name,
        theme=config.theme,
        accent=config.accent,
        mode=config.mode,
        theme_options=config.theme_options,
        repo_url=config.repo_url,
        description=config.description,
        docs_dir=config.docs_dir,
    )
    settings: dict[str, Any] = {
        # -- project ---------------------------------------------------------
        "project": config.name,
        "author": config.author,
        "copyright": config.copyright,
        "release": config.version,
        "version": config.version,
        "html_title": config.display_name,
        "html_short_title": config.display_name,
        "html_show_copyright": bool(config.copyright),
        "html_show_sphinx": False,
        # -- engine ----------------------------------------------------------
        "extensions": list(BASE_EXTENSIONS),
        "source_suffix": {".rst": "restructuredtext", ".md": "markdown"},
        "exclude_patterns": ["_build", "Thumbs.db", ".DS_Store"],
        "templates_path": [],
        # -- docstrings ------------------------------------------------------
        "default_role": "code",  # `x` renders as code, never a broken xref
        "autodoc_typehints": "description",
        "autodoc_typehints_description_target": "documented_params",
        "python_use_unqualified_type_names": True,
        "napoleon_google_docstring": True,
        "napoleon_numpy_docstring": True,
        "napoleon_preprocess_types": False,  # it cannot link list[str]
        "doctest_default_flags": 0,
        # -- Markdown pages --------------------------------------------------
        "myst_enable_extensions": list(MYST_EXTENSIONS),
        "myst_heading_anchors": 3,
        "myst_fence_as_directive": ["mermaid"],
        # myst.xref_missing: an included README links to repo files that are not site pages
        "suppress_warnings": [
            "myst.header",
            "myst.xref_missing",
            "autoapi.python_import_resolution",
        ],
        "intersphinx_mapping": {"python": ("https://docs.python.org/3", None)},
        "copybutton_prompt_text": r">>> |\.\.\. |\$ ",
        "copybutton_prompt_is_regexp": True,
        # -- theme -----------------------------------------------------------
        "html_theme": theme.html_theme,
        "html_theme_options": theme.html_theme_options,
        "html_context": theme.html_context,
        "html_static_path": ["_static"],
        "html_css_files": ["epythet.css"] if theme.css else [],
        "pygments_style": "friendly",
        # -- epythet's own values (read by epythet.sphinx_ext) ---------------
        "epythet_theme_css": theme.css,
        "epythet_agent_outputs": config.agent_outputs,
        "epythet_normalizer_rules": None,
    }
    settings = merge_settings(settings, _api_generator_settings(config))
    if config.agent_outputs:
        settings["extensions"].append("sphinx_llm.txt")
        settings.update(_agent_settings(description=config.description))
    return settings


def _api_generator_settings(config: DocsConfig) -> dict[str, Any]:
    """Settings for the ``api_generator`` seam.

    ``autosummary`` (default) imports the package, so aliases, ``functools.partial``
    objects and other assigned names keep the docstring of what they point to;
    measured on dol it documents every object the 0.1.x autodoc pages had.
    ``autoapi`` parses statically (no import, no side effects) at the cost of
    those aliases: use it when the package cannot be imported in CI.
    """
    package_dir = config.package_dir
    if package_dir is None:
        raise ValueError(
            f"Cannot find the package directory for {config.name!r} under "
            f"{config.project_dir}. Set [tool.epythet] package_dir."
        )
    if config.api_generator == "autoapi":
        return {
            "extensions": ["autoapi.extension"],
            "autoapi_dirs": [str(package_dir)],
            "autoapi_root": API_ROOT,
            "autoapi_ignore": [f"*{pattern}*" for pattern in config.ignore],
            "autoapi_options": ["members", "show-inheritance", "show-module-summary"],
            "autoapi_member_order": "bysource",
            "autoapi_python_class_content": "class",
            "autoapi_keep_files": False,
            "autoapi_add_toctree_entry": True,  # also generates api/index
        }
    # autosummary: imports the package; the api.rst scaffold holds the directive.
    return {
        "extensions": ["sphinx.ext.autodoc", "sphinx.ext.autosummary"],
        "autosummary_generate": True,
        "autosummary_ignore_module_all": False,
        "autodoc_default_options": {"members": True, "show-inheritance": True},
        "exclude_patterns": [
            f"_autosummary/*{pattern.strip('/').replace('/', '.')}*"
            for pattern in config.ignore
        ],
        "suppress_warnings": ["toc.excluded", "toc.not_included"],
    }


def api_toctree_entry(config: DocsConfig) -> str:
    """The document ``index.md``'s toctree points at for the API pages.

    >>> from epythet.config import DocsConfig
    >>> api_toctree_entry(DocsConfig(project_dir="/tmp/x", name="x"))
    'api'
    >>> api_toctree_entry(DocsConfig(project_dir="/tmp/x", name="x", api_generator="autoapi"))
    'api/index'
    """
    return f"{API_ROOT}/index" if config.api_generator == "autoapi" else API_ROOT


def merge_settings(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Merge two settings dicts, concatenating list values instead of replacing them.

    >>> merge_settings({"extensions": ["a"], "x": 1}, {"extensions": ["b"], "x": 2})
    {'extensions': ['a', 'b'], 'x': 2}
    """
    merged = dict(base)
    for key, value in extra.items():
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = merged[key] + [v for v in value if v not in merged[key]]
        else:
            merged[key] = value
    return merged
