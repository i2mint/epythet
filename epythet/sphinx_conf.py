"""The star-import target for a project's ``docsrc/conf.py``.

A generated ``conf.py`` is two lines::

    from epythet.sphinx_conf import *  # noqa: F401,F403
    # optional overrides below, e.g. html_theme = "alabaster"

Importing this module locates the project (the ``EPYTHET_PROJECT_DIR``
environment variable, else the nearest ancestor of the current directory with a
``pyproject.toml`` or ``setup.cfg``; Sphinx runs ``conf.py`` from the source
directory), loads its :class:`~epythet.config.DocsConfig`, applies any overrides
passed in the ``EPYTHET_OVERRIDES`` environment variable (JSON, set by
:mod:`epythet.build` for command-line flags such as ``--ignore``), and exports
the settings from :func:`epythet.confgen.sphinx_settings` as module globals.
"""

import json as _json
import os as _os
import sys as _sys
from pathlib import Path as _Path

from epythet.confgen import sphinx_settings as _sphinx_settings
from epythet.config import ConfigError as _ConfigError
from epythet.config import load_config as _load_config

#: Environment variable naming the project root (set by ``epythet make``).
PROJECT_DIR_ENV = "EPYTHET_PROJECT_DIR"
#: Environment variable carrying JSON config overrides (set by ``epythet make``).
OVERRIDES_ENV = "EPYTHET_OVERRIDES"


def _find_project_dir() -> _Path:
    env = _os.environ.get(PROJECT_DIR_ENV)
    if env:
        return _Path(env)
    here = _Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() or (
            candidate / "setup.cfg"
        ).is_file():
            return candidate
    raise _ConfigError(
        f"No pyproject.toml or setup.cfg found above {here}; set {PROJECT_DIR_ENV}."
    )


def _overrides() -> dict:
    raw = _os.environ.get(OVERRIDES_ENV)
    return _json.loads(raw) if raw else {}


epythet_config = _load_config(_find_project_dir(), **_overrides())
"""The :class:`~epythet.config.DocsConfig` this configuration was generated from."""

for _path in (epythet_config.project_dir, epythet_config.project_dir / "src"):
    if _path.is_dir() and str(_path) not in _sys.path:
        _sys.path.insert(0, str(_path))

globals().update(_sphinx_settings(epythet_config))
