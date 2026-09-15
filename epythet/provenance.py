"""Build provenance: which code, which version, which tools produced a site.

A documentation site is a snapshot. The reader wants to know whether it matches
the repository they are looking at and the package they installed; the
maintainer wants to know whether the latest push has been published yet
(issue #7). This module collects that diagnosis once per build and the rest of
epythet renders it in three places:

- a one-line footer on the landing page (``built <UTC time> from <commit>
  (<branch>) · <package> <version> · about this build``), appended to the
  rendered page by :mod:`epythet.sphinx_ext`;
- ``about-this-build.html``, an orphan page (reachable from the footer, absent
  from the navigation) with the full diagnosis, rendered from
  :data:`ABOUT_PAGE_TEMPLATE`;
- ``build_info.json`` at the site root, the same data for machines, with
  stable keys and a ``schema_version``; also listed in ``llms.txt`` and
  referenced at the top of the ``<package>.md`` aggregate.

The ``[tool.epythet] provenance`` key is the seam: ``true`` (default) renders
all three, ``"minimal"`` renders the footer line and the JSON but no page,
``false`` renders nothing.

Collection never fails a build. No git, no ``git`` binary, no network, a
detached HEAD: every source degrades to ``null`` fields plus an entry in the
``warnings`` list, and the build prints one warning.

>>> from epythet.config import DocsConfig
>>> cfg = DocsConfig(project_dir="/nonexistent", name="pkg", version="1.0")
>>> info = collect_build_info(cfg, check_pypi=False)
>>> info["schema_version"], info["package"]["name"], info["git"]["available"]
(1, 'pkg', False)
>>> "not checked" in render_footer_line(info) or "about this build" in render_footer_line(info)
True
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

#: Bumped when a key is renamed or removed; additions keep the version.
SCHEMA_VERSION = 1
#: File written at the site root.
BUILD_INFO_FILENAME = "build_info.json"
#: Source file (in docsrc) and document name of the full-diagnosis page.
ABOUT_PAGE_FILENAME = "about-this-build.md"
ABOUT_PAGE_DOCNAME = "about-this-build"
#: Environment variable carrying the collected JSON into the Sphinx process.
BUILD_INFO_ENV = "EPYTHET_BUILD_INFO"
#: Set to ``0`` to skip the PyPI lookup (offline CI, tests).
PYPI_CHECK_ENV = "EPYTHET_PYPI_CHECK"
#: Seconds allowed for the PyPI lookup; the site never waits longer.
DEFAULT_PYPI_TIMEOUT = 3.0
#: Seconds allowed for each git command.
GIT_TIMEOUT = 10
#: Values ``[tool.epythet] provenance`` accepts.
VALID_PROVENANCE = (True, False, "minimal")

_OFF_VALUES = ("0", "false", "no", "off")


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------


def collect_build_info(
    config,
    *,
    check_pypi: bool | None = None,
    pypi_timeout: float = DEFAULT_PYPI_TIMEOUT,
    environ: dict | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The provenance record for one build of ``config``'s project.

    :param config: a :class:`~epythet.config.DocsConfig`
    :param check_pypi: query PyPI for the latest release; ``None`` means "unless
        the ``EPYTHET_PYPI_CHECK`` environment variable turns it off"
    :param pypi_timeout: seconds allowed for that query
    :param environ: the environment to read CI variables from (default: ``os.environ``)
    :param now: the build time (default: now, UTC)
    :return: a JSON-serialisable dict; see the module docstring for the keys.
        ``site`` counts are ``None`` here and filled in by the Sphinx
        extension, which knows what was documented.
    """
    environ = os.environ if environ is None else environ
    if check_pypi is None:
        check_pypi = environ.get(PYPI_CHECK_ENV, "1").strip().lower() not in _OFF_VALUES
    now = now or datetime.now(timezone.utc)
    warnings: list[str] = []
    git = git_info(config.project_dir, exclude=(config.docs_dir,))
    if not git["available"]:
        warnings.append(f"git: {git['error']}")
    ci = ci_info(environ)
    if git["available"] is False and ci["sha"]:
        git = {**git, "commit": ci["sha"], "short_commit": ci["sha"][:7]}
    if git["branch"] in (None, "HEAD") and ci["ref_name"]:
        git = {**git, "branch": ci["ref_name"]}
    if not git["commit_url"] and git["commit"] and ci["repository"]:
        server = ci["server_url"] or "https://github.com"
        git = {
            **git,
            "commit_url": f"{server}/{ci['repository']}/commit/{git['commit']}",
        }
    pypi = (
        pypi_info(config.name, config.version, timeout=pypi_timeout)
        if check_pypi
        else {"checked": False, "latest": None, "relation": "unknown", "error": None}
    )
    if pypi["error"]:
        warnings.append(f"pypi: {pypi['error']}")
    info: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "built_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {
            "name": config.name,
            "version": config.version or None,
            "display_name": config.display_name,
            "source": config_source(config.project_dir),
        },
        "git": git,
        "ci": ci,
        "tools": tool_versions(),
        "config": resolved_config(config),
        "site": {"modules_documented": None, "objects_documented": None},
        "pypi": pypi,
        "reproduce": reproduce_command(config, git),
        "warnings": warnings,
    }
    info["alignment"] = alignment(info)
    return info


def git_info(project_dir: str | Path, *, exclude: tuple[str, ...] = ()) -> dict:
    """What git knows about ``project_dir``: commit, branch, tags, dirty flag, remote.

    ``exclude`` names paths (relative to the project) left out of the dirty
    check; the build rewrites a committed ``docsrc/``, which must not count.
    Everything is ``None`` with ``available`` false when the directory is not a
    repository or ``git`` is not installed.
    """
    out = {
        "available": False,
        "commit": None,
        "short_commit": None,
        "branch": None,
        "tags": [],
        "dirty": None,
        "remote_url": None,
        "commit_url": None,
        "error": None,
    }
    commit, error = _git(project_dir, "rev-parse", "HEAD")
    if error:
        out["error"] = error
        return out
    out["available"] = True
    out["commit"] = commit
    out["short_commit"] = commit[:7]
    branch, _ = _git(project_dir, "rev-parse", "--abbrev-ref", "HEAD")
    out["branch"] = branch or None
    tags, _ = _git(project_dir, "tag", "--points-at", "HEAD")
    out["tags"] = tags.split() if tags else []
    status, error = _git(
        project_dir,
        "status",
        "--porcelain",
        "--untracked-files=no",
        "--",
        ".",
        *(f":(exclude){path.strip('/')}" for path in exclude if path.strip("/")),
    )
    out["dirty"] = None if error else bool(status.strip())
    remote, _ = _git(project_dir, "remote", "get-url", "origin")
    remote = strip_credentials(remote) if remote else ""
    out["remote_url"] = remote or None
    repo_url = github_web_url(remote) if remote else None
    if repo_url:
        out["commit_url"] = f"{repo_url}/commit/{commit}"
    return out


def _git(project_dir, *args) -> tuple[str, str | None]:
    """``(stdout, error)`` of one git command; the error names why it failed."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
    except FileNotFoundError:
        return "", "git is not installed"
    except (OSError, subprocess.TimeoutExpired) as e:
        return "", f"{type(e).__name__}: {e}"
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        return "", (message[-1] if message else f"git {args[0]} failed")
    return result.stdout.strip(), None


def strip_credentials(url: str) -> str:
    """A remote URL without any ``user:token@`` part: the record is published.

    >>> strip_credentials("https://me:ghp_secret@github.com/o/r.git")
    'https://github.com/o/r.git'
    >>> strip_credentials("git@github.com:o/r.git")
    'git@github.com:o/r.git'
    """
    return re.sub(r"^([a-z+]+://)[^/@]+@", r"\1", url.strip())


def github_web_url(remote: str) -> str | None:
    """The ``https://github.com/owner/repo`` form of a remote URL, or ``None``.

    >>> github_web_url("git@github.com:i2mint/epythet.git")
    'https://github.com/i2mint/epythet'
    >>> github_web_url("https://github.com/i2mint/epythet/")
    'https://github.com/i2mint/epythet'
    >>> github_web_url("https://gitlab.com/x/y.git") is None
    True
    """
    match = re.match(
        r"^(?:https?://|git@|ssh://git@)github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
        remote.strip(),
    )
    if not match:
        return None
    owner, repo = match.groups()
    return f"https://github.com/{owner}/{repo}"


def ci_info(environ: dict | None = None) -> dict:
    """The GitHub Actions context, when the build runs there (else ``None`` fields).

    >>> ci_info({"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "o/r",
    ...          "GITHUB_RUN_ID": "42", "GITHUB_SHA": "abc", "GITHUB_REF": "refs/heads/main",
    ...          "GITHUB_REF_NAME": "main"})["run_url"]
    'https://github.com/o/r/actions/runs/42'
    >>> ci_info({})["provider"] is None
    True
    """
    env = os.environ if environ is None else environ
    if env.get("GITHUB_ACTIONS", "").lower() != "true":
        return {
            "provider": None,
            "repository": None,
            "sha": None,
            "ref": None,
            "ref_name": None,
            "run_id": None,
            "run_url": None,
            "server_url": None,
        }
    server = env.get("GITHUB_SERVER_URL") or "https://github.com"
    repository = env.get("GITHUB_REPOSITORY") or None
    run_id = env.get("GITHUB_RUN_ID") or None
    return {
        "provider": "github",
        "repository": repository,
        "sha": env.get("GITHUB_SHA") or None,
        "ref": env.get("GITHUB_REF") or None,
        "ref_name": env.get("GITHUB_REF_NAME") or None,
        "run_id": run_id,
        "run_url": (
            f"{server}/{repository}/actions/runs/{run_id}"
            if repository and run_id
            else None
        ),
        "server_url": server,
    }


def tool_versions() -> dict:
    """Versions of epythet, Sphinx, docutils and Python in the build environment."""
    from importlib.metadata import PackageNotFoundError, version

    def dist_version(name):
        try:
            return version(name)
        except PackageNotFoundError:
            return None

    return {
        "epythet": dist_version("epythet"),
        "sphinx": dist_version("sphinx"),
        "docutils": dist_version("docutils"),
        "python": ".".join(str(v) for v in sys.version_info[:3]),
    }


def resolved_config(config) -> dict:
    """The documentation choices as the build resolved them (theme, accent, generator...)."""
    try:
        from epythet.themes import resolve_theme

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
        html_theme, accent = theme.html_theme, theme.accent_light
    except Exception:  # an unknown theme name: the build reports that itself
        html_theme, accent = config.theme, config.accent or None
    try:
        api_generator = config.resolved_api_generator
    except Exception:
        api_generator = config.api_generator
    return {
        "theme": config.theme,
        "html_theme": html_theme,
        "accent": accent,
        "mode": config.mode,
        "api_generator": api_generator,
        "ignore": list(config.ignore),
        "agent_outputs": config.agent_outputs,
        "aggregates": list(config.aggregates),
        "ai_artifacts": config.ai_artifacts,
        "provenance": config.provenance,
        "docs_dir": config.docs_dir,
    }


def config_source(project_dir: str | Path) -> str | None:
    """Which file the package metadata came from: the rule of :mod:`epythet.config`."""
    project_dir = Path(project_dir)
    pyproject = project_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib

            if "project" in tomllib.loads(pyproject.read_text(encoding="utf-8")):
                return "pyproject.toml"
        except Exception:
            pass
    if (project_dir / "setup.cfg").is_file():
        return "setup.cfg"
    return None


def pypi_info(
    name: str, version: str, *, timeout: float = DEFAULT_PYPI_TIMEOUT
) -> dict:
    """The latest release of ``name`` on PyPI and how ``version`` relates to it.

    ``relation`` is ``same``, ``behind``, ``ahead`` or ``unknown`` (not on
    PyPI, unreachable, or unparsable versions). Any failure is recorded in
    ``error`` and never raised.
    """
    out = {"checked": False, "latest": None, "relation": "unknown", "error": None}
    if not name:
        return out
    try:
        latest = pypi_latest_version(name, timeout=timeout)
    except Exception as e:  # network down, DNS, 404, bad JSON: all "not checked"
        out["error"] = f"{type(e).__name__}: {e}".strip()
        return out
    out["checked"] = True
    out["latest"] = latest
    if latest and version:
        out["relation"] = compare_versions(version, latest)
    return out


def pypi_latest_version(
    name: str, *, timeout: float = DEFAULT_PYPI_TIMEOUT
) -> str | None:
    """The ``info.version`` of ``https://pypi.org/pypi/<name>/json`` (``None`` on 404)."""
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    request = Request(
        f"https://pypi.org/pypi/{name}/json",
        headers={"Accept": "application/json", "User-Agent": "epythet"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    return data.get("info", {}).get("version") or None


def compare_versions(ours: str, latest: str) -> str:
    """``same`` / ``behind`` / ``ahead`` of ``latest``, or ``unknown`` when unparsable.

    >>> compare_versions("0.2.4", "0.2.5"), compare_versions("1.0", "1.0.0")
    ('behind', 'same')
    >>> compare_versions("0.3.0.dev1", "0.2.5"), compare_versions("x", "1")
    ('ahead', 'unknown')
    """
    try:
        from packaging.version import Version

        a, b = Version(ours), Version(latest)
    except Exception:
        return "unknown"
    if a == b:
        return "same"
    return "behind" if a < b else "ahead"


def reproduce_command(config, git: dict) -> str:
    """The shell lines that rebuild this site from the same commit."""
    lines = []
    if git.get("remote_url") and git.get("commit"):
        lines.append(f"git clone {git['remote_url']} && cd {config.project_dir.name}")
        lines.append(f"git checkout {git['commit']}")
    epythet_version = tool_versions()["epythet"]
    spec = f"epythet=={epythet_version}" if epythet_version else "epythet"
    lines.append(f'pip install "{spec}"')
    ignore = " ".join(config.ignore)
    lines.append(f"epythet quickstart . --ignore {ignore}".rstrip())
    return "\n".join(lines)


def alignment(info: dict) -> dict:
    """Whether the docs can be trusted to match the repository and the package.

    ``aligned`` is ``True`` when nothing suggests otherwise, ``False`` when a
    note says why they may differ, ``None`` when there is no git information to
    judge by. ``notes`` are the plain-language reasons, in the order shown.
    """
    notes: list[str] = []
    git, pypi, ci, pkg = info["git"], info["pypi"], info["ci"], info["package"]
    if git["dirty"]:
        notes.append(
            f"The working tree had uncommitted changes when the docs were built, "
            f"so they may describe code that is not in commit {git['short_commit']}."
        )
    if ci["sha"] and git["commit"] and ci["sha"] != git["commit"]:
        notes.append(
            f"The CI checkout ({ci['sha'][:7]}) differs from the commit the docs "
            f"were built from ({git['short_commit']})."
        )
    if pypi["checked"] and pypi["latest"]:
        if pypi["relation"] == "behind":
            notes.append(
                f"The documented version ({pkg['version']}) is behind the latest "
                f"release on PyPI ({pypi['latest']}): `pip install {pkg['name']}` "
                "gives newer code than these docs describe."
            )
        elif pypi["relation"] == "ahead":
            notes.append(
                f"The documented version ({pkg['version']}) is ahead of the latest "
                f"release on PyPI ({pypi['latest']}): these docs describe unreleased code."
            )
    if not git["available"] and not git["commit"]:
        notes.append(
            "No git information was available, so the commit these docs describe is unknown."
        )
        return {"aligned": None, "notes": notes}
    return {"aligned": not notes, "notes": notes}


# --------------------------------------------------------------------------
# Rendering: the footer line
# --------------------------------------------------------------------------


def footer_text(info: dict) -> str:
    """The provenance line as plain text (no link).

    >>> info = {"built_at": "2026-09-15T14:02:00Z", "package": {"name": "dol", "version": "0.3.1"},
    ...         "git": {"short_commit": "a1b2c3d", "branch": "master", "dirty": True}}
    >>> footer_text(info)
    'built 2026-09-15 14:02 UTC from a1b2c3d+dirty (master) · dol 0.3.1'
    """
    parts = [f"built {human_time(info['built_at'])}"]
    git = info["git"]
    if git.get("short_commit"):
        commit = git["short_commit"] + ("+dirty" if git.get("dirty") else "")
        branch = f" ({git['branch']})" if git.get("branch") else ""
        parts[0] += f" from {commit}{branch}"
    pkg = info["package"]
    if pkg.get("version"):
        parts.append(f"{pkg['name']} {pkg['version']}")
    else:
        parts.append(pkg["name"])
    return " · ".join(parts)


def render_footer_line(
    info: dict, *, about_href: str | None = ABOUT_PAGE_DOCNAME + ".html"
) -> str:
    """The landing-page footer as one small HTML paragraph.

    The commit links to GitHub when the remote is known; ``about_href`` is the
    "about this build" link target (``None`` to omit the link, as ``minimal`` does
    without a page: the JSON is linked instead).
    """
    git = info["git"]
    built = f"built {escape(human_time(info['built_at']))}"
    if git.get("short_commit"):
        commit = escape(git["short_commit"]) + ("+dirty" if git.get("dirty") else "")
        if git.get("commit_url"):
            commit = f'<a href="{escape(git["commit_url"])}">{commit}</a>'
        branch = f" ({escape(git['branch'])})" if git.get("branch") else ""
        built += f" from {commit}{branch}"
    pkg = info["package"]
    package = escape(pkg["name"]) + (
        f" {escape(pkg['version'])}" if pkg.get("version") else ""
    )
    link = (
        f'<a href="{escape(about_href)}">about this build</a>'
        if about_href
        else f'<a href="{BUILD_INFO_FILENAME}">build info</a>'
    )
    return (
        '<p class="epythet-provenance" style="font-size:.8em;opacity:.65;'
        'margin-top:2.5em;text-align:right">'
        f"{built} · {package} · {link}</p>"
    )


def human_time(iso: str) -> str:
    """``2026-09-15T14:02:00Z`` -> ``2026-09-15 14:02 UTC``.

    >>> human_time("2026-09-15T14:02:00Z")
    '2026-09-15 14:02 UTC'
    """
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    except ValueError:
        return iso


# --------------------------------------------------------------------------
# Rendering: the about page
# --------------------------------------------------------------------------

#: The Markdown source of the about page. ``{marker}`` must stay: it is how
#: epythet recognises its own file. Literal braces are doubled.
ABOUT_PAGE_TEMPLATE = """\
---
orphan: true
---
{marker}

# About this build

{summary}

{alignment_block}

## Source

| | |
|---|---|
| Commit | {commit_cell} |
| Branch | {branch} |
| Tags at this commit | {tags} |
| Working tree | {tree_state} |
| Remote | {remote} |

## Continuous integration

{ci_block}

## Tools

| | |
|---|---|
| epythet | {epythet_version} |
| Sphinx | {sphinx_version} |
| docutils | {docutils_version} |
| Python | {python_version} |

## Configuration as resolved

| | |
|---|---|
| theme | `{theme}` (Sphinx theme `{html_theme}`) |
| accent | `{accent}` |
| api_generator | `{api_generator}` |
| ignore | {ignore} |
| agent_outputs | `{agent_outputs}` |
| aggregates | {aggregates} |
| ai_artifacts | `{ai_artifacts}` |

## Package on PyPI

{pypi_block}

## Reproduce

```bash
{reproduce}
```

The same data, for machines: <a href="{build_info_filename}"><code>{build_info_filename}</code></a> (schema version {schema_version}).
"""

#: The fields :func:`render_about_page` fills; a custom template may use any subset.
TEMPLATE_FIELDS = frozenset(
    {
        "marker",
        "summary",
        "alignment_block",
        "commit_cell",
        "branch",
        "tags",
        "tree_state",
        "remote",
        "ci_block",
        "epythet_version",
        "sphinx_version",
        "docutils_version",
        "python_version",
        "theme",
        "html_theme",
        "accent",
        "api_generator",
        "ignore",
        "agent_outputs",
        "aggregates",
        "ai_artifacts",
        "pypi_block",
        "reproduce",
        "build_info_filename",
        "schema_version",
    }
)


def render_about_page(info: dict, *, template: str = ABOUT_PAGE_TEMPLATE) -> str:
    """The Markdown source of ``about-this-build.md`` for a collected ``info``."""
    from epythet.templates import INDEX_MARKER

    git, pkg, ci, pypi, cfg, tools = (
        info["git"],
        info["package"],
        info["ci"],
        info["pypi"],
        info["config"],
        info["tools"],
    )
    unknown = "unknown"
    fields = {
        "marker": INDEX_MARKER,
        "summary": _summary(info),
        "alignment_block": _alignment_block(info),
        "commit_cell": (
            f"[`{git['commit']}`]({git['commit_url']})"
            if git.get("commit_url")
            else (f"`{git['commit']}`" if git.get("commit") else unknown)
        ),
        "branch": f"`{git['branch']}`" if git.get("branch") else unknown,
        "tags": ", ".join(f"`{t}`" for t in git.get("tags") or []) or "none",
        "tree_state": (
            "dirty (uncommitted changes)"
            if git.get("dirty")
            else ("clean" if git.get("dirty") is False else unknown)
        ),
        "remote": f"`{git['remote_url']}`" if git.get("remote_url") else unknown,
        "ci_block": _ci_block(ci),
        "epythet_version": tools.get("epythet") or unknown,
        "sphinx_version": tools.get("sphinx") or unknown,
        "docutils_version": tools.get("docutils") or unknown,
        "python_version": tools.get("python") or unknown,
        "theme": cfg["theme"],
        "html_theme": cfg["html_theme"],
        "accent": cfg["accent"] or unknown,
        "api_generator": cfg["api_generator"],
        "ignore": ", ".join(f"`{p}`" for p in cfg["ignore"]) or "none",
        "agent_outputs": str(cfg["agent_outputs"]).lower(),
        "aggregates": ", ".join(f"`{a}`" for a in cfg["aggregates"]) or "none",
        "ai_artifacts": str(cfg["ai_artifacts"]).lower(),
        "pypi_block": _pypi_block(pkg, pypi),
        "reproduce": info["reproduce"],
        "build_info_filename": BUILD_INFO_FILENAME,
        "schema_version": info["schema_version"],
    }
    return template.format(**fields)


def _summary(info: dict) -> str:
    git, pkg = info["git"], info["package"]
    when = human_time(info["built_at"])
    version = f" {pkg['version']}" if pkg.get("version") else ""
    source = f" (from `{pkg['source']}`)" if pkg.get("source") else ""
    if git.get("short_commit"):
        commit = (
            f"[`{git['short_commit']}`]({git['commit_url']})"
            if git.get("commit_url")
            else f"`{git['short_commit']}`"
        )
        branch = f" on branch `{git['branch']}`" if git.get("branch") else ""
        where = f" from commit {commit}{branch}"
    else:
        where = ""
    return (
        f"This documentation was built on **{when}**{where}, for "
        f"**{pkg['name']}{version}**{source}."
    )


def _alignment_block(info: dict) -> str:
    align = info["alignment"]
    if align["aligned"]:
        return (
            ":::{note}\nNothing suggests a mismatch: the tree was clean at the commit "
            "above, and the documented version is the one on PyPI"
            + ("." if info["pypi"]["checked"] else " (PyPI was not checked).")
            + "\n:::"
        )
    notes = "\n".join(f"- {note}" for note in align["notes"])
    return (
        ":::{warning}\nThe documentation and the package may be misaligned:\n\n"
        f"{notes}\n:::"
    )


def _ci_block(ci: dict) -> str:
    if not ci.get("provider"):
        return "Not built in CI (no GitHub Actions environment was detected)."
    run = f"[{ci['run_id']}]({ci['run_url']})" if ci.get("run_url") else "unknown"
    return (
        "| | |\n|---|---|\n"
        f"| Repository | `{ci.get('repository') or 'unknown'}` |\n"
        f"| Run | {run} |\n"
        f"| Ref | `{ci.get('ref') or 'unknown'}` |\n"
        f"| Commit | `{ci.get('sha') or 'unknown'}` |"
    )


def _pypi_block(pkg: dict, pypi: dict) -> str:
    if not pypi["checked"]:
        return "Not checked" + (f" ({pypi['error']})." if pypi.get("error") else ".")
    if not pypi["latest"]:
        return f"`{pkg['name']}` is not on PyPI."
    relation = {
        "same": "the same as the documented version.",
        "behind": f"newer than the documented version ({pkg['version']}).",
        "ahead": f"older than the documented version ({pkg['version']}).",
        "unknown": "not comparable with the documented version.",
    }[pypi["relation"]]
    return (
        f"Latest release: [{pypi['latest']}](https://pypi.org/project/{pkg['name']}/"
        f"{pypi['latest']}/), {relation}"
    )


# --------------------------------------------------------------------------
# Site-level helpers used by build.py and sphinx_ext.py
# --------------------------------------------------------------------------


def about_page(info: dict, *, template: str = ABOUT_PAGE_TEMPLATE):
    """The about page as a :class:`~epythet.scaffold.PageSpec`."""
    from epythet.scaffold import PageSpec

    return PageSpec(ABOUT_PAGE_FILENAME, render_about_page(info, template=template))


def site_counts(env) -> dict:
    """Documented-module and documented-object counts from a Sphinx environment."""
    from epythet.confgen import API_ROOT

    docnames = getattr(env, "found_docs", ()) or ()
    modules = sum(
        1
        for d in docnames
        if (d.startswith("_autosummary/") or d.startswith(f"{API_ROOT}/"))
        and d != f"{API_ROOT}/index"
    )
    try:
        objects = sum(
            1
            for entry in env.get_domain("py").objects.values()
            if entry.objtype != "module"
        )
    except Exception:
        objects = None
    return {"modules_documented": modules, "objects_documented": objects}


def write_build_info(html_dir: str | Path, info: dict) -> Path:
    """Write ``build_info.json`` at the site root; returns its path."""
    target = Path(html_dir) / BUILD_INFO_FILENAME
    target.write_text(
        json.dumps(info, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return target


def reference_from_agent_outputs(
    html_dir: str | Path, info: dict, *, package_name: str
) -> None:
    """List ``build_info.json`` in ``llms.txt`` and stamp the top of ``<package>.md``."""
    html_dir = Path(html_dir)
    llms = html_dir / "llms.txt"
    line = (
        f"- [{BUILD_INFO_FILENAME}]({BUILD_INFO_FILENAME}): build provenance "
        "(commit, version, tool versions, whether the docs match the package)"
    )
    if llms.is_file():
        text = llms.read_text(encoding="utf-8")
        if BUILD_INFO_FILENAME not in text:
            llms.write_text(
                text.rstrip("\n") + "\n\n## Build\n\n" + line + "\n", encoding="utf-8"
            )
    aggregate = html_dir / f"{package_name}.md"
    if aggregate.is_file():
        text = aggregate.read_text(encoding="utf-8")
        if BUILD_INFO_FILENAME not in text[:500]:
            stamp = f"> {footer_text(info)}. Details: {BUILD_INFO_FILENAME}\n\n"
            aggregate.write_text(stamp + text, encoding="utf-8")


def load_build_info(raw: str | None) -> dict | None:
    """Parse the JSON the build process hands over in ``EPYTHET_BUILD_INFO``."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None
