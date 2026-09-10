"""Single source of truth for a project's documentation configuration.

Everything epythet needs to build a site comes from two places, read in this
order of precedence:

1. ``pyproject.toml``: the ``[project]`` table for name, version and authors,
   and the ``[tool.epythet]`` table for documentation choices.
2. ``setup.cfg``: the ``[metadata]`` section (legacy projects).

When both files exist, ``pyproject.toml`` wins as soon as it has a ``[project]``
table. (epythet 0.1.x silently preferred ``setup.cfg``, which was wrong for the
projects that had migrated to ``pyproject.toml`` but kept a stale ``setup.cfg``.)

The result is a :class:`DocsConfig`, an immutable dataclass. The legacy 5-tuple
accessor :func:`epythet.config_parser.parse_config` is derived from it and keeps
its signature, so old ``docsrc/conf.py`` copies keep working.

The ``[tool.epythet]`` keys, all optional::

    [tool.epythet]
    display_name = "Dol"          # site title; default: the project name
    copyright = "2024, Jane Doe"  # footer line; default: none rendered
    theme = "auto"                # "auto" | "furo" | "shibuya" | ... | any installed theme
    accent = "#3661ac"            # default: derived from the package name (OKLCH)
    mode = "auto"                 # "auto" | "light" | "dark"
    ignore = ["tests/", "scrap/", "examples/"]  # path substrings to skip
    api_generator = "auto"        # "auto" | "autosummary" (imports the package) | "autoapi" (static)
    agent_outputs = true          # llms.txt + .md twins of every page
    aggregates = ["md"]           # flat single-document twins at the site root
    ai_artifacts = true           # "For AI agents" page when skills/agents/CLAUDE.md exist
    ai_artifacts_template = ""    # project-relative file overriding that page's template
    package_dir = "src/dol"       # default: found by convention
    docs_dir = "docsrc"           # where the Sphinx sources live

    [tool.epythet.theme_options]  # verbatim passthrough into html_theme_options
    announcement = "v2 is in beta"

>>> import tempfile, pathlib
>>> d = pathlib.Path(tempfile.mkdtemp())
>>> _ = (d / "pyproject.toml").write_text('''
... [project]
... name = "my-pkg"
... version = "1.2.3"
... authors = [{name = "Jane Doe"}]
... [tool.epythet]
... theme = "furo"
... ''')
>>> _ = (d / "my_pkg").mkdir()
>>> _ = (d / "my_pkg" / "__init__.py").write_text("")
>>> cfg = load_config(d)
>>> cfg.name, cfg.version, cfg.author, cfg.theme, cfg.package_dir.name
('my-pkg', '1.2.3', 'Jane Doe', 'furo', 'my_pkg')
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from configparser import ConfigParser
from dataclasses import dataclass, field, replace
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Iterable

#: Path substrings skipped by default when discovering modules to document.
DEFAULT_IGNORE: tuple[str, ...] = ("tests/", "scrap/", "examples/")

#: Modules never documented, whatever ``ignore`` says. Importing a package's
#: ``__main__`` runs its command line (argparse prints usage and exits) in the
#: middle of the build, and the module has no API to show.
ALWAYS_IGNORE: tuple[str, ...] = ("__main__",)

#: Directory under the project root holding the Sphinx sources.
DEFAULT_DOCS_DIR = "docsrc"

#: Directory candidates (relative to the project root) that may hold the package.
PACKAGE_DIR_CANDIDATES: tuple[str, ...] = ("{name}", "src/{name}")

#: Top-level directories never taken for the package when guessing by convention.
NON_PACKAGE_DIRS = frozenset(
    {"tests", "test", "docs", "docsrc", "scrap", "examples", "misc"}
)

VALID_MODES = ("auto", "light", "dark")
VALID_API_GENERATORS = ("auto", "autosummary", "autoapi")
#: Seconds allowed for the import probe behind ``api_generator = "auto"``.
IMPORT_PROBE_TIMEOUT = 120
VALID_AGGREGATES = ("md", "pdf")


class ConfigError(ValueError):
    """A project's documentation configuration is missing or invalid."""


@dataclass(frozen=True)
class DocsConfig:
    """Everything needed to generate a project's documentation.

    Attributes mirror the ``[tool.epythet]`` keys; see the module docstring.
    ``project_dir`` and ``package_dir`` are absolute paths.
    """

    project_dir: Path
    name: str
    version: str = ""
    author: str = ""
    description: str = ""
    display_name: str = ""
    copyright: str = ""
    repo_url: str = ""
    theme: str = "auto"
    accent: str = ""
    mode: str = "auto"
    theme_options: dict[str, Any] = field(default_factory=dict)
    ignore: tuple[str, ...] = DEFAULT_IGNORE
    api_generator: str = "auto"
    agent_outputs: bool = True
    aggregates: tuple[str, ...] = ("md",)
    ai_artifacts: bool = True
    ai_artifacts_template: str = ""
    package_dir: Path | None = None
    docs_dir: str = DEFAULT_DOCS_DIR

    def __post_init__(self):
        if not self.display_name:
            object.__setattr__(self, "display_name", self.name)
        if self.mode not in VALID_MODES:
            raise ConfigError(f"mode must be one of {VALID_MODES}, not {self.mode!r}")
        if self.api_generator not in VALID_API_GENERATORS:
            raise ConfigError(
                f"api_generator must be one of {VALID_API_GENERATORS}, "
                f"not {self.api_generator!r}"
            )
        unknown = set(self.aggregates) - set(VALID_AGGREGATES)
        if unknown:
            raise ConfigError(
                f"aggregates may only contain {VALID_AGGREGATES}; got {sorted(unknown)}"
            )
        object.__setattr__(self, "ignore", split_ignore(self.ignore))
        object.__setattr__(self, "aggregates", tuple(self.aggregates))
        object.__setattr__(self, "project_dir", Path(self.project_dir).absolute())
        if self.package_dir is not None:
            object.__setattr__(
                self, "package_dir", (self.project_dir / self.package_dir).absolute()
            )

    @cached_property
    def resolved_api_generator(self) -> str:
        """``api_generator`` with ``"auto"`` resolved: see :func:`resolve_api_generator`."""
        return resolve_api_generator(self)

    @property
    def api_ignore(self) -> tuple[str, ...]:
        """``ignore`` plus :data:`ALWAYS_IGNORE`: what the API generators skip.

        >>> DocsConfig(project_dir="/tmp/x", name="x", ignore=["tests/"]).api_ignore
        ('tests/', '__main__')
        """
        return tuple(dict.fromkeys((*self.ignore, *ALWAYS_IGNORE)))

    @property
    def docsrc_dir(self) -> Path:
        """Absolute path of the Sphinx source directory."""
        return self.project_dir / self.docs_dir

    @property
    def package_name(self) -> str:
        """The importable package name (``my-pkg`` becomes ``my_pkg``)."""
        if self.package_dir is not None:
            return self.package_dir.name
        return self.name.replace("-", "_")

    @property
    def legacy_tuple(self) -> tuple[str, str, str, str, str]:
        """The 5-tuple that :func:`epythet.config_parser.parse_config` returns."""
        return (self.name, self.copyright, self.author, self.version, self.display_name)

    def with_overrides(self, **changes) -> "DocsConfig":
        """A copy with some fields replaced (``None`` values are ignored)."""
        return replace(self, **{k: v for k, v in changes.items() if v is not None})


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_config(project_dir: str | Path, **overrides) -> DocsConfig:
    """Read a project's documentation configuration.

    :param project_dir: the project root (holding ``pyproject.toml`` or ``setup.cfg``),
        or a path to one of those files.
    :param overrides: field values that win over the files (``None`` is ignored),
        e.g. ``ignore=["tests/"]`` from a command line flag.
    :raises ConfigError: when neither configuration file is found.
    """
    project_dir = _project_root(project_dir)
    raw = _read_raw_config(project_dir)
    raw.update({k: v for k, v in overrides.items() if v is not None})
    package_dir = raw.pop("package_dir", None)
    if package_dir is None:
        package_dir = find_package_dir(project_dir, raw["name"])
    return DocsConfig(project_dir=project_dir, package_dir=package_dir, **raw)


def resolve_api_generator(config: DocsConfig) -> str:
    """The generator to run: ``autosummary`` when the package imports, else ``autoapi``.

    ``autosummary`` imports the package and documents what it finds (aliases,
    partials, re-exports); when the import fails, in CI typically because an
    optional dependency is missing, it produces an *empty* API section and a
    successful build. ``auto`` probes the import once, in a subprocess with the
    project root on ``sys.path`` (as the build has it), and falls back to the
    static ``autoapi`` generator, printing why. An explicit value is returned as is.
    """
    if config.api_generator != "auto":
        return config.api_generator
    ok, error = _import_probe(
        config.package_name, str(config.project_dir), sys.executable
    )
    if ok:
        return "autosummary"
    print(
        f"epythet: {config.package_name!r} does not import ({error}); documenting "
        "it statically with autoapi (aliases and re-exports are not followed). "
        "Install the package's dependencies in the docs environment to get the "
        "full API pages.",
        file=sys.stderr,
    )
    return "autoapi"


@lru_cache(maxsize=None)
def _import_probe(package_name: str, project_dir: str, python: str) -> tuple[bool, str]:
    """``(imported, last error line)`` for importing ``package_name`` in a subprocess."""
    code = (
        "import importlib, sys; "
        f"sys.path[:0] = [{project_dir!r}, {project_dir + '/src'!r}]; "
        f"importlib.import_module({package_name!r})"
    )
    try:
        result = subprocess.run(
            [python, "-c", code],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=IMPORT_PROBE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"{type(e).__name__}: {e}"
    if result.returncode == 0:
        return True, ""
    lines = [line for line in result.stderr.strip().splitlines() if line.strip()]
    return False, (lines[-1] if lines else f"exit status {result.returncode}")


def split_ignore(ignore: Iterable[str]) -> tuple[str, ...]:
    """Normalise ignore patterns: each item may itself be a comma-separated list.

    The publish action passes its ``ignore`` input verbatim as one argument,
    ``--ignore tests/,scrap/,examples/``, and ``setup.cfg`` values are strings;
    both must mean three patterns, not one that never matches.

    >>> split_ignore(["tests/,scrap/", " examples/ ", "", "tests/"])
    ('tests/', 'scrap/', 'examples/')
    """
    if isinstance(ignore, str):
        ignore = [ignore]
    parts = (part.strip() for item in ignore for part in item.split(","))
    return tuple(dict.fromkeys(part for part in parts if part))


def find_package_dir(project_dir: str | Path, name: str) -> Path | None:
    """Locate the package directory for ``name`` under ``project_dir`` by convention.

    Tries ``<name>/`` then ``src/<name>/`` (with ``-`` mapped to ``_``), returning
    the first that contains an ``__init__.py``; ``None`` when nothing matches.

    >>> find_package_dir("/nonexistent", "nothing") is None
    True
    """
    project_dir = Path(project_dir)
    module_name = name.replace("-", "_")
    for candidate in PACKAGE_DIR_CANDIDATES:
        path = project_dir / candidate.format(name=module_name)
        if (path / "__init__.py").is_file():
            return path.absolute()
    # Fallback: the one top-level package that is not a conventional non-package dir.
    found = [
        d
        for root in (project_dir, project_dir / "src")
        if root.is_dir()
        for d in root.iterdir()
        if (d / "__init__.py").is_file() and d.name not in NON_PACKAGE_DIRS
    ]
    return found[0].absolute() if len(found) == 1 else None


def _project_root(path: str | Path) -> Path:
    path = Path(path).absolute()
    return path.parent if path.is_file() or path.suffix in (".toml", ".cfg") else path


def _read_raw_config(project_dir: Path) -> dict[str, Any]:
    """The raw field dict from the first usable configuration file."""
    pyproject = project_dir / "pyproject.toml"
    setup_cfg = project_dir / "setup.cfg"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if "project" in data:
            return _fields_from_pyproject(data)
    if setup_cfg.is_file():
        return _fields_from_setup_cfg(setup_cfg)
    raise ConfigError(
        f"No pyproject.toml with a [project] table and no setup.cfg found in "
        f"{project_dir}. epythet needs one of them to know the project name."
    )


def _fields_from_pyproject(data: dict) -> dict[str, Any]:
    project = data.get("project", {})
    tool = dict(data.get("tool", {}).get("epythet", {}))
    authors = project.get("authors") or []
    author = ", ".join(a.get("name", "") for a in authors if a.get("name"))
    urls = project.get("urls") or {}
    repo_url = _first_github_url(urls.values())
    fields = {
        "name": project.get("name", "NO PROJECT NAME"),
        "version": str(project.get("version", "")),
        "author": author,
        "description": project.get("description", ""),
        "repo_url": repo_url,
    }
    fields.update(_coerce_tool_fields(tool))
    return fields


def _fields_from_setup_cfg(setup_cfg: Path) -> dict[str, Any]:
    config = ConfigParser()
    config.read(setup_cfg, encoding="utf-8")
    meta = config["metadata"] if config.has_section("metadata") else {}
    fields = {
        "name": meta.get("name", "NO PROJECT NAME"),
        "version": meta.get("version", ""),
        "author": meta.get("author", ""),
        "description": meta.get("description", ""),
        "display_name": meta.get("display_name", ""),
        "copyright": meta.get("copyright", ""),
        "repo_url": _first_github_url([meta.get("url", "")]),
    }
    if config.has_section("tool.epythet") or config.has_section("epythet"):
        section = "tool.epythet" if config.has_section("tool.epythet") else "epythet"
        fields.update(_coerce_tool_fields(dict(config[section])))
    return fields


_LIST_KEYS = ("ignore", "aggregates")
_BOOL_KEYS = ("agent_outputs", "ai_artifacts")


def _coerce_tool_fields(tool: dict[str, Any]) -> dict[str, Any]:
    """Accept the ``[tool.epythet]`` keys, tolerating setup.cfg's string values."""
    out: dict[str, Any] = {}
    for key, value in tool.items():
        if key in _LIST_KEYS and isinstance(value, str):
            value = [
                v.strip() for v in value.replace("\n", ",").split(",") if v.strip()
            ]
        elif key in _BOOL_KEYS and isinstance(value, str):
            value = value.strip().lower() in ("1", "true", "yes", "on")
        elif key == "theme_options" and not isinstance(value, dict):
            raise ConfigError("[tool.epythet.theme_options] must be a table")
        out[key] = value
    unknown = set(out) - set(DocsConfig.__dataclass_fields__) - {"project_dir"}
    if unknown:
        raise ConfigError(f"Unknown [tool.epythet] keys: {sorted(unknown)}")
    return out


def _first_github_url(urls: Iterable[str]) -> str:
    for url in urls:
        if url and "github.com/" in url:
            return url.rstrip("/")
    return ""
