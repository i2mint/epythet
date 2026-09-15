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
  :data:`ABOUT_PAGE_TEMPLATE` or the project's ``provenance_template``;
- ``build_info.json`` at the site root, the same data for machines, with
  stable keys and a ``schema_version``; also listed in ``llms.txt`` and
  referenced at the top of the ``<package>.md`` aggregate.

The ``[tool.epythet] provenance`` key is the seam: ``true`` (default) renders
all three, ``"minimal"`` renders the footer line and the JSON but no page,
``false`` renders nothing.

Collection never fails a build. No git, no ``git`` binary, no network, a
detached HEAD: every source degrades to ``null`` fields plus an entry in the
``warnings`` list, and the build prints one warning. The record is published,
so nothing local goes into it: remote URLs lose any credentials, path-shaped
remotes are dropped, git's error text is scrubbed of paths, and the reproduce
lines name the clone by its remote, not by the local folder.

``SOURCE_DATE_EPOCH`` (the reproducible-builds convention Sphinx honours too)
fixes the build time when set.

>>> from epythet.config import DocsConfig
>>> cfg = DocsConfig(project_dir="/nonexistent", name="pkg", version="1.0")
>>> info = collect_build_info(cfg, check_pypi=False)
>>> info["schema_version"], info["package"]["name"], info["git"]["available"]
(1, 'pkg', False)
>>> "about this build" in render_footer_line(info)
True
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
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
#: Reproducible-builds convention: seconds since the epoch, fixes ``built_at``.
SOURCE_DATE_EPOCH_ENV = "SOURCE_DATE_EPOCH"
#: Seconds allowed for the PyPI lookup, in total; the build never waits longer.
DEFAULT_PYPI_TIMEOUT = 3.0
#: Seconds allowed for each git command.
GIT_TIMEOUT = 10
#: Characters of a commit hash shown in the footer and the summary.
SHORT_COMMIT_LENGTH = 7
#: First line of the stamp prepended to the ``<package>.md`` aggregate.
AGGREGATE_STAMP_PREFIX = "> built "

_OFF_VALUES = ("0", "false", "no", "off")
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------


def collect_build_info(
    config,
    *,
    check_pypi: bool | None = None,
    pypi_timeout: float = DEFAULT_PYPI_TIMEOUT,
    dirty_exclude: tuple[str, ...] | None = None,
    environ: dict | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The provenance record for one build of ``config``'s project.

    :param config: a :class:`~epythet.config.DocsConfig`
    :param check_pypi: query PyPI for the latest release; ``None`` means "unless
        the ``EPYTHET_PYPI_CHECK`` environment variable turns it off"
    :param pypi_timeout: seconds allowed for that query
    :param dirty_exclude: project-relative paths left out of the dirty check, on
        top of the docs dir; ``None`` means the directories the ``github`` /
        ``gitlab`` targets copy the site into (:data:`epythet.build.COPY_TARGETS`)
    :param environ: the environment to read CI variables from (default: ``os.environ``)
    :param now: the build time (default: ``SOURCE_DATE_EPOCH`` if set, else now, UTC)
    :return: a JSON-serialisable dict; see the module docstring for the keys.
        ``site`` counts are ``None`` here and filled in by the Sphinx
        extension, which knows what was documented.
    """
    environ = os.environ if environ is None else environ
    if check_pypi is None:
        check_pypi = environ.get(PYPI_CHECK_ENV, "1").strip().lower() not in _OFF_VALUES
    if dirty_exclude is None:
        from epythet.build import COPY_TARGETS  # lazy: build imports this module

        dirty_exclude = tuple(COPY_TARGETS.values())
    now = now or build_time(environ)
    warnings: list[str] = []
    git = git_info(config.project_dir, exclude=(config.docs_dir, *dirty_exclude))
    if not git["available"]:
        warnings.append(f"git: {git['error']}")
    ci = ci_info(environ)
    if ci["sha"] and git["available"]:
        ci["sha_in_history"] = _is_ancestor(config.project_dir, ci["sha"])
    if git["available"] is False and ci["sha"]:
        git = {**git, "commit": ci["sha"], "short_commit": short_commit(ci["sha"])}
    if git["branch"] is None and ci["ref_name"]:
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
        "built_at": now.strftime(_TIME_FORMAT),
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


def build_time(environ: dict | None = None) -> datetime:
    """Now in UTC, or the instant ``SOURCE_DATE_EPOCH`` names when it is set.

    >>> build_time({"SOURCE_DATE_EPOCH": "0"}).strftime("%Y-%m-%d")
    '1970-01-01'
    """
    env = os.environ if environ is None else environ
    raw = env.get(SOURCE_DATE_EPOCH_ENV, "").strip()
    if raw.isdigit():
        return datetime.fromtimestamp(int(raw), timezone.utc)
    return datetime.now(timezone.utc)


def short_commit(sha: str) -> str:
    """The first :data:`SHORT_COMMIT_LENGTH` characters of a commit hash."""
    return sha[:SHORT_COMMIT_LENGTH]


def git_info(project_dir: str | Path, *, exclude: tuple[str, ...] = ()) -> dict:
    """What git knows about ``project_dir``: commit, branch, tags, dirty flag, remote.

    ``exclude`` names paths (relative to the project) left out of the dirty
    check; the build rewrites a committed ``docsrc/``, which must not count.
    Everything is ``None`` with ``available`` false when the directory is not a
    repository or ``git`` is not installed. A detached HEAD has ``branch``
    ``None``. ``remote_url`` is the publishable form of ``origin`` (no
    credentials, no local paths), see :func:`publishable_remote`.
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
    out["short_commit"] = short_commit(commit)
    branch, _ = _git(project_dir, "rev-parse", "--abbrev-ref", "HEAD")
    out["branch"] = branch if branch and branch != "HEAD" else None
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
    out["remote_url"] = publishable_remote(remote) if remote else None
    repo_url = github_web_url(out["remote_url"]) if out["remote_url"] else None
    if repo_url:
        out["commit_url"] = f"{repo_url}/commit/{commit}"
    return out


def _git(project_dir, *args) -> tuple[str, str | None]:
    """``(stdout, error)`` of one git command; the error names why it failed."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
        )
    except FileNotFoundError:
        return "", "git is not installed"
    except (OSError, subprocess.TimeoutExpired) as e:
        return "", scrub_paths(f"{type(e).__name__}: {e}")
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        return "", scrub_paths(message[-1] if message else f"git {args[0]} failed")
    return result.stdout.strip(), None


def _is_ancestor(project_dir, sha: str) -> bool | None:
    """Whether ``sha`` is HEAD or one of its ancestors (``None`` when git cannot say)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), "merge-base", "--is-ancestor", sha, "HEAD"],
            capture_output=True,
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # 1: not an ancestor; 128: no such object in this clone. Neither is "in history".
    return result.returncode == 0


def scrub_paths(message: str) -> str:
    """Replace absolute paths in a diagnostic with ``<path>``: the record is published.

    >>> scrub_paths("fatal: detected dubious ownership in repository at '/home/me/x'")
    "fatal: detected dubious ownership in repository at '<path>'"
    >>> scrub_paths("fatal: not a git repository (or any of the parent directories): .git")
    'fatal: not a git repository (or any of the parent directories): .git'
    """
    return re.sub(r"(?:(?<=[\s'\"])|^)(?:/|[A-Za-z]:[\\/])[^\s'\"]*", "<path>", message)


def publishable_remote(url: str) -> str | None:
    """The form of a remote URL that may appear on a public site, or ``None``.

    Credentials are dropped from scheme URLs, the user part from scp-style
    remotes, and path-shaped remotes (a local or ``file://`` clone) are not
    published at all.

    >>> publishable_remote("https://me:ghp_secret@github.com/o/r.git")
    'https://github.com/o/r.git'
    >>> publishable_remote("thor@myserver.local:repos/demo.git")
    'myserver.local:repos/demo.git'
    >>> publishable_remote("git@github.com:o/r.git")
    'git@github.com:o/r.git'
    >>> publishable_remote("/Users/me/bare/demo.git") is None
    True
    >>> publishable_remote("file:///srv/git/demo.git") is None
    True
    """
    url = url.strip()
    scheme = re.match(r"^([a-z][a-z0-9+.-]*)://", url, re.IGNORECASE)
    if scheme:
        if scheme.group(1).lower() == "file":
            return None
        return strip_credentials(url)
    scp = re.match(r"^(?:([^@/:]+)@)?([^/:]+):(.+)$", url)
    if scp:
        user, host, path = scp.groups()
        # ``git@`` is the conventional, anonymous SSH user of the forges: keep it.
        return f"{user}@{host}:{path}" if user == "git" else f"{host}:{path}"
    return None


def strip_credentials(url: str) -> str:
    """A scheme URL without any ``user:token@`` part (scp-style remotes pass through).

    >>> strip_credentials("https://me:ghp_secret@github.com/o/r.git")
    'https://github.com/o/r.git'
    """
    return re.sub(
        r"^([a-z][a-z0-9+.-]*://)[^/@]+@", r"\1", url.strip(), flags=re.IGNORECASE
    )


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


def clone_dirname(remote: str) -> str:
    """The directory ``git clone <remote>`` creates.

    >>> clone_dirname("https://github.com/org/demo.git"), clone_dirname("git@github.com:o/r")
    ('demo', 'r')
    """
    tail = remote.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return re.sub(r"\.git$", "", tail)


def ci_info(environ: dict | None = None) -> dict:
    """The GitHub Actions context, when the build runs there (else ``None`` fields).

    ``sha_in_history`` says whether the event's commit is in the built HEAD's
    history; the publish action fast-forwards to the branch tip before
    building, so HEAD is normally a descendant of ``GITHUB_SHA``, not equal to it.

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
            "sha_in_history": None,
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
        "sha_in_history": None,
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
    PyPI, unreachable, or unparsable versions). Any failure, including the
    ``timeout`` elapsing, is recorded in ``error`` and never raised.
    """
    out = {"checked": False, "latest": None, "relation": "unknown", "error": None}
    if not name:
        return out
    try:
        latest = _bounded(pypi_latest_version, name, timeout=timeout)
    except Exception as e:  # network down, DNS, 404, bad JSON: all "not checked"
        out["error"] = f"{type(e).__name__}: {e}".strip()
        return out
    out["checked"] = True
    out["latest"] = latest
    if latest and version:
        out["relation"] = compare_versions(version, latest)
    return out


def _bounded(function, *args, timeout: float):
    """Run ``function`` in a daemon thread; give up after ``timeout`` seconds.

    ``urlopen``'s timeout bounds each socket operation, not name resolution
    or the whole transfer; this bounds the wall clock the build spends.
    """
    result: dict[str, Any] = {}

    def run():
        try:
            result["value"] = function(*args, timeout=timeout)
        except BaseException as e:  # reported by the caller, never raised here
            result["error"] = e

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TimeoutError(f"no answer within {timeout:g}s")
    if "error" in result:
        raise result["error"]
    return result.get("value")


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
        remote = git["remote_url"]
        lines.append(f"git clone {remote} && cd {clone_dirname(remote)}")
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
    if ci["sha"] and git["commit"] and ci.get("sha_in_history") is False:
        notes.append(
            f"The CI checkout ({short_commit(ci['sha'])}) is not in the history of "
            f"the commit the docs were built from ({git['short_commit']})."
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
    without a page: the JSON is linked instead). The style is inline on purpose:
    it must hold in every theme without a stylesheet of its own.
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
        return datetime.strptime(iso, _TIME_FORMAT).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso


# --------------------------------------------------------------------------
# Rendering: the about page
# --------------------------------------------------------------------------

#: The Markdown source of the about page. ``{marker}`` must stay: it is how
#: epythet recognises its own file. Literal braces are doubled. Every value
#: is already HTML-escaped (:func:`render_about_page`), so a custom template
#: may place the fields anywhere.
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
| theme | {theme} (Sphinx theme {html_theme}) |
| accent | {accent} |
| api_generator | {api_generator} |
| ignore | {ignore} |
| agent_outputs | {agent_outputs} |
| aggregates | {aggregates} |
| ai_artifacts | {ai_artifacts} |

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
    """The Markdown source of ``about-this-build.md`` for a collected ``info``.

    Values from the repository (branch, tags, remote, versions) are rendered
    as escaped inline HTML, never as Markdown: a ref name is user input.
    """
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
            _link(git["commit_url"], _code(git["commit"]))
            if git.get("commit_url")
            else (_code(git["commit"]) if git.get("commit") else unknown)
        ),
        "branch": _code(git["branch"]) if git.get("branch") else "none (detached HEAD)",
        "tags": ", ".join(_code(t) for t in git.get("tags") or []) or "none",
        "tree_state": (
            "dirty (uncommitted changes)"
            if git.get("dirty")
            else ("clean" if git.get("dirty") is False else unknown)
        ),
        "remote": _code(git["remote_url"]) if git.get("remote_url") else unknown,
        "ci_block": _ci_block(ci),
        "epythet_version": _text(tools.get("epythet")) or unknown,
        "sphinx_version": _text(tools.get("sphinx")) or unknown,
        "docutils_version": _text(tools.get("docutils")) or unknown,
        "python_version": _text(tools.get("python")) or unknown,
        "theme": _code(cfg["theme"]),
        "html_theme": _code(cfg["html_theme"]),
        "accent": _code(cfg["accent"]) if cfg.get("accent") else unknown,
        "api_generator": _code(cfg["api_generator"]),
        "ignore": ", ".join(_code(p) for p in cfg["ignore"]) or "none",
        "agent_outputs": _code(str(cfg["agent_outputs"]).lower()),
        "aggregates": ", ".join(_code(a) for a in cfg["aggregates"]) or "none",
        "ai_artifacts": _code(str(cfg["ai_artifacts"]).lower()),
        "pypi_block": _pypi_block(pkg, pypi),
        "reproduce": info["reproduce"].replace("```", "` ` `"),
        "build_info_filename": BUILD_INFO_FILENAME,
        "schema_version": info["schema_version"],
    }
    return template.format(**fields)


def _text(value) -> str:
    return escape(str(value)) if value is not None else ""


def _code(value) -> str:
    return f"<code>{_text(value)}</code>"


def _link(href: str, label_html: str) -> str:
    return f'<a href="{escape(href)}">{label_html}</a>'


def _summary(info: dict) -> str:
    git, pkg = info["git"], info["package"]
    when = human_time(info["built_at"])
    version = f" {_text(pkg['version'])}" if pkg.get("version") else ""
    source = f" (from {_code(pkg['source'])})" if pkg.get("source") else ""
    if git.get("short_commit"):
        commit = (
            _link(git["commit_url"], _code(git["short_commit"]))
            if git.get("commit_url")
            else _code(git["short_commit"])
        )
        branch = f" on branch {_code(git['branch'])}" if git.get("branch") else ""
        where = f" from commit {commit}{branch}"
    else:
        where = ""
    return (
        f"This documentation was built on **{when}**{where}, for "
        f"**{_text(pkg['name'])}{version}**{source}."
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
    notes = "\n".join(f"- {escape(note, quote=False)}" for note in align["notes"])
    return (
        ":::{warning}\nThe documentation and the package may be misaligned:\n\n"
        f"{notes}\n:::"
    )


def _ci_block(ci: dict) -> str:
    if not ci.get("provider"):
        return "Not built in CI (no GitHub Actions environment was detected)."
    run = _link(ci["run_url"], _text(ci["run_id"])) if ci.get("run_url") else "unknown"
    sha = _code(ci["sha"]) if ci.get("sha") else "unknown"
    if ci.get("sha_in_history") is True:
        sha += " (in the history of the built commit)"
    repository = _code(ci["repository"]) if ci.get("repository") else "unknown"
    ref = _code(ci["ref"]) if ci.get("ref") else "unknown"
    return (
        "| | |\n|---|---|\n"
        f"| Repository | {repository} |\n"
        f"| Run | {run} |\n"
        f"| Ref | {ref} |\n"
        f"| Event commit | {sha} |"
    )


def _pypi_block(pkg: dict, pypi: dict) -> str:
    if not pypi["checked"]:
        error = f" ({_text(pypi['error'])})" if pypi.get("error") else ""
        return f"Not checked{error}."
    if not pypi["latest"]:
        return f"{_code(pkg['name'])} is not on PyPI."
    version = _text(pkg["version"])
    relation = {
        "same": "the same as the documented version.",
        "behind": f"newer than the documented version ({version}).",
        "ahead": f"older than the documented version ({version}).",
        "unknown": "not comparable with the documented version.",
    }[pypi["relation"]]
    url = f"https://pypi.org/project/{pkg['name']}/{pypi['latest']}/"
    return f"Latest release: {_link(url, _text(pypi['latest']))}, {relation}"


# --------------------------------------------------------------------------
# Site-level helpers used by build.py and sphinx_ext.py
# --------------------------------------------------------------------------


def about_page(info: dict, *, template: str = ABOUT_PAGE_TEMPLATE):
    """The about page as a :class:`~epythet.scaffold.PageSpec`.

    :raises ConfigError: when ``template`` names a field the renderer does not
        provide (literal braces must be doubled: ``{{``).
    """
    from epythet.config import ConfigError
    from epythet.scaffold import PageSpec

    try:
        content = render_about_page(info, template=template)
    except (KeyError, IndexError, ValueError) as e:
        raise ConfigError(
            f"provenance_template: unknown field {e}; the fields are "
            f"{sorted(TEMPLATE_FIELDS)} and literal braces must be doubled ({{{{ and }}}})"
        ) from e
    return PageSpec(ABOUT_PAGE_FILENAME, content)


def about_template(config) -> str:
    """The about page's template: ``[tool.epythet] provenance_template`` or the default.

    The key names a file relative to the project root, with the same contract
    as ``ai_artifacts_template``; the epythet marker is prepended when absent.

    :raises ConfigError: when the file does not exist
    """
    from epythet.config import ConfigError
    from epythet.templates import INDEX_MARKER

    template_path = getattr(config, "provenance_template", "")
    if not template_path:
        return ABOUT_PAGE_TEMPLATE
    path = config.project_dir / template_path
    if not path.is_file():
        raise ConfigError(
            f"[tool.epythet] provenance_template points at {path}, which does not exist"
        )
    template = path.read_text(encoding="utf-8")
    if INDEX_MARKER not in template and "{marker}" not in template:
        template = "{marker}\n\n" + template
    return template


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
        if not text.startswith(AGGREGATE_STAMP_PREFIX):
            stamp = f"> {footer_text(info)}. Details: {BUILD_INFO_FILENAME}\n\n"
            aggregate.write_text(stamp + text, encoding="utf-8")


def prune_site(html_dir: str | Path, *, keep_page: bool, keep_json: bool) -> list:
    """Remove provenance outputs a previous build left in ``html_dir``.

    Sphinx never cleans its output directory, so a project that turned
    ``provenance`` off (or down to ``"minimal"``) would otherwise keep
    publishing a stale page or JSON. Returns the paths removed.
    """
    html_dir = Path(html_dir)
    stale = []
    if not keep_page:
        stale += [
            html_dir / f"{ABOUT_PAGE_DOCNAME}.html",
            html_dir / f"{ABOUT_PAGE_DOCNAME}.html.md",
        ]
    if not keep_json:
        stale.append(html_dir / BUILD_INFO_FILENAME)
    removed = []
    for path in stale:
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed


def load_build_info(raw: str | None) -> dict | None:
    """Parse the JSON the build process hands over in ``EPYTHET_BUILD_INFO``.

    Anything that is not a record of this module's schema is ignored, so a
    stale or foreign value in the environment never breaks a build.

    >>> load_build_info('{"schema_version": 1, "git": {}}')["schema_version"]
    1
    >>> load_build_info('"str"') is None and load_build_info("{") is None
    True
    """
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(info, dict) or info.get("schema_version") != SCHEMA_VERSION:
        return None
    return info
