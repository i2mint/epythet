"""User-level defaults and parametrizable text snippets.

epythet ships opinions (what a README section for agents should say, which
humour lines introduce the "for humans" pointer, whether a missing section is a
warning or something to add). A user who wants different opinions sets them
once, outside any repository, and every project on that machine picks them up.
Two things live under the user's config directory:

- ``config.toml``: policy. The ``[readme]`` table decides what the
  ``epythet-agentic-readme`` skill does (``agentic_aspects = "warn" | "add"``,
  ``humor``, ``agentic_first``); the ``[snippets]`` table can point ``dir`` at
  a different snippet folder.
- ``snippets/<name>.md``: text overrides. A snippet is looked up in the user's
  folder first, then in the packaged defaults (``epythet/data/snippets``).
  ``epythet snippets init`` copies the packaged defaults out **once**, with a
  header recording the epythet version they came from, and never overwrites a
  file that exists; ``epythet snippets diff`` shows how a user's copy differs
  from the current packaged default, so upstream changes are visible without
  ever being applied silently.

The config directory is ``$EPYTHET_CONFIG_DIR``, else ``$XDG_CONFIG_HOME/epythet``,
else ``~/.config/epythet``: the config-side twin of
:func:`epythet.validation.ledger.user_data_dir`, which holds mutable data
(ledger observations) under ``~/.local/share/epythet``. Skills stay prose: they
call ``epythet snippets show <name>`` and ``epythet ai-readme-check --format json``
and let this module do the resolving.

>>> import os, tempfile
>>> os.environ["EPYTHET_CONFIG_DIR"] = tempfile.mkdtemp()
>>> load_user_config().readme
ReadmePolicy(agentic_aspects='warn', humor=False, agentic_first=False)
>>> snippet("agentic-readme-humor").source
'packaged'
>>> written = init_snippets()
>>> snippet("agentic-readme-humor").source
'user'
>>> init_snippets()          # a second init writes nothing
[]
>>> del os.environ["EPYTHET_CONFIG_DIR"]
"""

from __future__ import annotations

import difflib
import os
import re
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Iterator

from epythet.config import ConfigError

#: Environment variable overriding the whole config directory.
CONFIG_DIR_ENV = "EPYTHET_CONFIG_DIR"
#: The policy file inside the config directory.
CONFIG_FILENAME = "config.toml"
#: The snippet folder inside the config directory (unless ``[snippets] dir`` says otherwise).
SNIPPETS_DIRNAME = "snippets"
#: Where the packaged default snippets live.
PACKAGED_SNIPPETS_DIR = Path(__file__).resolve().parent / "data" / "snippets"
SNIPPET_SUFFIX = ".md"
#: What ``agentic_aspects`` may be.
AGENTIC_ASPECTS_POLICIES = ("warn", "add")

_HEADER_RE = re.compile(
    r"\A<!--\s*epythet snippet\s+\"(?P<name>[^\"]+)\"\s+copied from epythet\s+"
    r"(?P<version>[^\s.]+(?:\.[^\s.]+)*?)\.?(?:\s.*?)?-->\s*\n?",
    re.DOTALL,
)


class UserConfigError(ConfigError):
    """``config.toml`` has a key epythet does not know or a value it cannot use."""


# --------------------------------------------------------------------------
# Directories
# --------------------------------------------------------------------------


def config_dir() -> Path:
    """``$EPYTHET_CONFIG_DIR``, else ``$XDG_CONFIG_HOME/epythet``, else ``~/.config/epythet``.

    XDG-style on every platform, like :func:`epythet.validation.ledger.user_data_dir`.

    >>> os.environ[CONFIG_DIR_ENV] = "/tmp/x"; config_dir().as_posix()
    '/tmp/x'
    >>> del os.environ[CONFIG_DIR_ENV]
    """
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "epythet"


def config_path() -> Path:
    """The policy file: ``<config dir>/config.toml``."""
    return config_dir() / CONFIG_FILENAME


# --------------------------------------------------------------------------
# Policy
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadmePolicy:
    """The ``[readme]`` table: what to do about agentic aspects missing from a README.

    ``agentic_aspects`` is ``"warn"`` (report only; the packaged default) or
    ``"add"`` (write or update the section). ``humor`` draws the "for humans"
    line from the humour pool; ``agentic_first`` places the section right after
    the README's intro rather than at the end.
    """

    agentic_aspects: str = "warn"
    humor: bool = False
    agentic_first: bool = False

    def __post_init__(self):
        if self.agentic_aspects not in AGENTIC_ASPECTS_POLICIES:
            raise UserConfigError(
                f"[readme] agentic_aspects must be one of {AGENTIC_ASPECTS_POLICIES}, "
                f"got {self.agentic_aspects!r}"
            )
        for name in ("humor", "agentic_first"):
            if not isinstance(getattr(self, name), bool):
                raise UserConfigError(f"[readme] {name} must be true or false")


@dataclass(frozen=True)
class SnippetsConfig:
    """The ``[snippets]`` table: ``dir`` overrides where user snippets are read."""

    dir: str = ""


@dataclass(frozen=True)
class UserConfig:
    """Everything ``config.toml`` can say, with defaults for what it does not."""

    readme: ReadmePolicy = field(default_factory=ReadmePolicy)
    snippets: SnippetsConfig = field(default_factory=SnippetsConfig)
    path: Path | None = None

    def to_dict(self) -> dict:
        """A JSON-ready view (the ``policy`` block of ``ai-readme-check --format json``)."""
        return {
            "path": str(self.path) if self.path else None,
            "readme": {f.name: getattr(self.readme, f.name) for f in fields(ReadmePolicy)},
            "snippets": {"dir": self.snippets.dir},
        }


def load_user_config(path: str | Path | None = None) -> UserConfig:
    """Read ``config.toml`` (default: :func:`config_path`); a missing file means defaults.

    :raises UserConfigError: on an unknown table or key, or an invalid value
    """
    target = Path(path) if path is not None else config_path()
    if not target.is_file():
        return UserConfig(path=None)
    try:
        raw = tomllib.loads(target.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise UserConfigError(f"{target}: {e}") from e
    return _user_config_from(raw, target)


def _user_config_from(raw: dict, target: Path) -> UserConfig:
    known = {"readme": ReadmePolicy, "snippets": SnippetsConfig}
    unknown = set(raw) - set(known)
    if unknown:
        raise UserConfigError(
            f"{target}: unknown table(s) {sorted(unknown)}; known: {sorted(known)}"
        )
    sections = {}
    for table, cls in known.items():
        values = raw.get(table, {})
        if not isinstance(values, dict):
            raise UserConfigError(f"{target}: [{table}] must be a table")
        allowed = {f.name for f in fields(cls)}
        extra = set(values) - allowed
        if extra:
            raise UserConfigError(
                f"{target}: unknown key(s) {sorted(extra)} in [{table}]; "
                f"known: {sorted(allowed)}"
            )
        sections[table] = cls(**values)
    return UserConfig(path=target, **sections)


# --------------------------------------------------------------------------
# Snippets
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Snippet:
    """One resolved snippet: its text and where it came from.

    ``source`` is ``"user"`` or ``"packaged"``; ``copied_from`` is the epythet
    version recorded in a user copy's header (``""`` for a packaged snippet or
    a user file written by hand).
    """

    name: str
    path: Path
    source: str
    text: str
    copied_from: str = ""

    @property
    def body(self) -> str:
        """The text without the provenance header (what templates and pools use)."""
        return strip_header(self.text)


def snippets_dir(config: UserConfig | None = None) -> Path:
    """Where user snippets are read: ``[snippets] dir`` if set, else ``<config dir>/snippets``."""
    config = config if config is not None else load_user_config()
    if config.snippets.dir:
        return Path(config.snippets.dir).expanduser()
    return config_dir() / SNIPPETS_DIRNAME


def packaged_snippet_names() -> list[str]:
    """The names of the snippets epythet ships, sorted."""
    return sorted(p.stem for p in PACKAGED_SNIPPETS_DIR.glob(f"*{SNIPPET_SUFFIX}"))


def snippet_names(*, user_dir: Path | None = None) -> list[str]:
    """Every snippet name available: packaged plus user-only files, sorted."""
    user_dir = user_dir if user_dir is not None else snippets_dir()
    names = set(packaged_snippet_names())
    if user_dir.is_dir():
        names.update(p.stem for p in user_dir.glob(f"*{SNIPPET_SUFFIX}"))
    return sorted(names)


def snippet(name: str, *, user_dir: Path | None = None) -> Snippet:
    """Resolve ``name``: the user's ``<name>.md`` wins over the packaged default.

    :raises KeyError: when neither exists
    """
    user_dir = user_dir if user_dir is not None else snippets_dir()
    user_path = user_dir / f"{name}{SNIPPET_SUFFIX}"
    if user_path.is_file():
        text = user_path.read_text(encoding="utf-8")
        return Snippet(name, user_path, "user", text, copied_from=header_version(text))
    packaged = PACKAGED_SNIPPETS_DIR / f"{name}{SNIPPET_SUFFIX}"
    if packaged.is_file():
        return Snippet(name, packaged, "packaged", packaged.read_text(encoding="utf-8"))
    raise KeyError(
        f"no snippet named {name!r}; known: {snippet_names(user_dir=user_dir)}"
    )


def snippet_text(name: str, *, user_dir: Path | None = None) -> str:
    """The effective body of ``name`` (header stripped)."""
    return snippet(name, user_dir=user_dir).body


def iter_snippets(*, user_dir: Path | None = None) -> Iterator[Snippet]:
    """Every available snippet, resolved, in name order."""
    user_dir = user_dir if user_dir is not None else snippets_dir()
    for name in snippet_names(user_dir=user_dir):
        yield snippet(name, user_dir=user_dir)


def pool_lines(text: str) -> list[str]:
    """The non-empty, non-comment lines of a pool snippet (one candidate per line).

    >>> pool_lines("# a comment\\n\\nIf you are a control freak\\n  If you like it \\n")
    ['If you are a control freak', 'If you like it']
    """
    return [
        line.strip()
        for line in strip_header(text).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


# --------------------------------------------------------------------------
# init and diff: copy out once, never overwrite, show what changed upstream
# --------------------------------------------------------------------------


def snippet_header(name: str, version: str) -> str:
    """The provenance line ``init`` writes at the top of a user copy."""
    return (
        f'<!-- epythet snippet "{name}" copied from epythet {version}. '
        "This file is yours: edit freely. `epythet snippets diff` shows how it "
        "differs from the current packaged default. -->\n"
    )


def header_version(text: str) -> str:
    """The epythet version recorded in a user copy's header (``""`` when absent).

    >>> header_version(snippet_header("x", "0.2.5") + "body")
    '0.2.5'
    >>> header_version("no header")
    ''
    """
    match = _HEADER_RE.match(text)
    return match.group("version") if match else ""


def strip_header(text: str) -> str:
    """``text`` without the provenance header, if it has one."""
    return _HEADER_RE.sub("", text, count=1)


def epythet_version() -> str:
    """epythet's version: the checkout's ``pyproject.toml`` when running from source, else the installed metadata."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            if data.get("project", {}).get("name") == "epythet":
                return str(data["project"].get("version", "")) or "unknown"
        except (tomllib.TOMLDecodeError, OSError):
            pass
    try:
        from importlib.metadata import version

        return version("epythet")
    except Exception:  # not installed as a distribution
        return "unknown"


def init_snippets(
    *, user_dir: Path | None = None, force: bool = False, names=None
) -> list[Path]:
    """Copy the packaged defaults into the user snippet folder; returns the paths written.

    A file that already exists is left alone unless ``force`` is true (then it
    is replaced; ``epythet snippets diff`` first is the way to see what you lose).

    :param names: which snippets to copy (default: all packaged)
    """
    user_dir = user_dir if user_dir is not None else snippets_dir()
    version = epythet_version()
    written: list[Path] = []
    for name in names or packaged_snippet_names():
        packaged = PACKAGED_SNIPPETS_DIR / f"{name}{SNIPPET_SUFFIX}"
        if not packaged.is_file():
            raise KeyError(f"no packaged snippet named {name!r}")
        target = user_dir / packaged.name
        if target.exists() and not force:
            continue
        user_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(
            snippet_header(name, version) + packaged.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        written.append(target)
    return written


def diff_snippet(name: str, *, user_dir: Path | None = None) -> str:
    """A unified diff from the current packaged default to the user's copy (``""`` when equal).

    Headers are ignored, so a freshly ``init``-ed copy has no diff. A user-only
    snippet (no packaged default) diffs against nothing, so every line is an
    addition.
    """
    user_dir = user_dir if user_dir is not None else snippets_dir()
    resolved = snippet(name, user_dir=user_dir)
    if resolved.source != "user":
        return ""
    packaged = PACKAGED_SNIPPETS_DIR / f"{name}{SNIPPET_SUFFIX}"
    upstream = packaged.read_text(encoding="utf-8") if packaged.is_file() else ""
    origin = f" (copied from epythet {resolved.copied_from})" if resolved.copied_from else ""
    return "".join(
        difflib.unified_diff(
            upstream.splitlines(keepends=True),
            resolved.body.splitlines(keepends=True),
            fromfile=f"packaged/{name}{SNIPPET_SUFFIX} (epythet {epythet_version()})",
            tofile=f"user/{name}{SNIPPET_SUFFIX}{origin}",
        )
    )


def snippets_table(*, user_dir: Path | None = None) -> str:
    """The ``epythet snippets list`` output: name, source, provenance, whether modified."""
    user_dir = user_dir if user_dir is not None else snippets_dir()
    lines = [f"Snippets (user folder: {user_dir}; packaged: {PACKAGED_SNIPPETS_DIR})", ""]
    lines.append(f"{'name':<32} {'source':<9} {'copied from':<12} {'status'}")
    for item in iter_snippets(user_dir=user_dir):
        if item.source == "packaged":
            status = "default"
        elif diff_snippet(item.name, user_dir=user_dir):
            status = "modified"
        else:
            status = "same as packaged"
        lines.append(
            f"{item.name:<32} {item.source:<9} {item.copied_from or '-':<12} {status}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI: ``epythet snippets list | show NAME | init [--force] | diff [--name NAME]``
# --------------------------------------------------------------------------


def snippets_list():
    """List every snippet with its source (user or packaged), provenance and status."""
    print(snippets_table())


def snippets_show(name):
    """Print the effective text of a snippet: the user's copy if it exists, else the packaged default.

    :param name: the snippet name (``epythet snippets list`` shows them)
    """
    import cw

    try:
        print(snippet(name).body, end="")
    except KeyError as e:
        raise cw.CommandError(str(e.args[0]), code=2) from e


def snippets_init(*, force: bool = False):
    """Copy the packaged default snippets into the user snippet folder, once.

    Each copy starts with a header recording the epythet version it came from.
    Existing files are never overwritten unless ``--force`` is given.

    :param force: replace existing user copies (run ``diff`` first to see what you lose)
    """
    written = init_snippets(force=force)
    folder = snippets_dir()
    if written:
        for path in written:
            print(f"wrote {path}")
    else:
        print(f"nothing to do: every packaged snippet already has a copy in {folder}")


def snippets_diff(name: str = ""):
    """Show how the user's copy of a snippet differs from the current packaged default.

    Without ``--name``, every user copy that differs is shown. Exit code 1 when any
    difference exists, like ``diff``, so scripts can tell.

    :param name: one snippet, or omitted for all
    """
    import cw

    names = [name] if name else [s.name for s in iter_snippets() if s.source == "user"]
    diffs = []
    for item in names:
        try:
            text = diff_snippet(item)
        except KeyError as e:
            raise cw.CommandError(str(e.args[0]), code=2) from e
        if text:
            diffs.append(text)
    if not diffs:
        print("no differences from the packaged defaults")
        return
    print("\n".join(diffs), end="")
    raise cw.CommandError("", code=1)


#: The ``epythet snippets`` group, by command-line name.
SNIPPET_COMMANDS = {
    "list": snippets_list,
    "show": snippets_show,
    "init": snippets_init,
    "diff": snippets_diff,
}
