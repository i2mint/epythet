"""Run Sphinx for a project, without ``make`` or a ``Makefile``.

``sphinx-build`` is invoked as ``python -m sphinx`` with the *current*
interpreter, so the build uses exactly the environment epythet was installed
into. The project root and any command-line overrides reach the generated
``conf.py`` through environment variables (see :mod:`epythet.sphinx_conf`).

Targets mirror the old Makefile: ``html`` (the default), ``doctest``,
``markdown``, ``github`` (``html`` then a copy into ``PROJECT_DIR/docs``),
``gitlab`` (copy into ``public``) and ``clean``.

An ``html`` build also carries its provenance (:mod:`epythet.provenance`): the
record is collected here, once, before Sphinx runs; the about page's source is
written into ``docsrc``; the record reaches the Sphinx process through the
``EPYTHET_BUILD_INFO`` environment variable, where the extension renders the
footer and writes ``build_info.json``; afterwards ``llms.txt`` and the
``<package>.md`` aggregate get a pointer to that file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

from epythet.agent_outputs import inject_link_relations_into_site, write_aggregates
from epythet.config import DocsConfig, load_config
from epythet.provenance import (
    ABOUT_PAGE_DOCNAME,
    ABOUT_PAGE_FILENAME,
    BUILD_INFO_ENV,
    BUILD_INFO_FILENAME,
    about_page,
    about_template,
    collect_build_info,
    prune_site,
    reference_from_agent_outputs,
)
from epythet.scaffold import remove_generated_file, write_generated_file
from epythet.templates import INDEX_MARKER

BUILD_DIRNAME = "_build"
COPY_TARGETS = {"github": "docs", "gitlab": "public"}
#: Written by Sphinx's HTML builders at a site's root; a hand-written directory never has it.
#: It is what makes a copy target recognisably an epythet build (``clean`` and ``github``
#: touch only such a directory, or one that is absent or empty).
SITE_MARKER = ".buildinfo"
#: Markers that identify an epythet-built site: Sphinx's own, and epythet's provenance record
#: (survives a gitignore that strips dotfiles).
SITE_MARKERS = (SITE_MARKER, BUILD_INFO_FILENAME, ".epythet-manifest.json")
#: Written into a copy target by ``github``/``gitlab``: the files that copy put there. With
#: it, ``clean`` removes only those files and ``github`` refuses to overwrite a same-named
#: file it did not write, so hand-written files beside a built site survive both (#47).
MANIFEST_FILENAME = SITE_MARKERS[-1]
#: Builders that produce a browsable site and therefore carry provenance.
HTML_TARGETS = ("html", "dirhtml")


class BuildError(RuntimeError):
    """Sphinx exited with a non-zero status, or a copy target holds hand-written files."""


def is_built_site(path: Path) -> bool:
    """Whether ``path`` is safe for epythet to overwrite or delete: absent, empty or a built site."""
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        return False
    return (
        not path.exists()
        or not any(path.iterdir())
        or any((path / marker).is_file() for marker in SITE_MARKERS)
    )


def _site_files(root: Path) -> list[str]:
    """Posix paths, relative to ``root``, of every file under it."""
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )


class _InvalidManifest(ValueError):
    """The manifest file exists but cannot be trusted as a list of files to delete."""


def _read_manifest(destination: Path) -> set[str] | None:
    """The files an earlier copy wrote into ``destination``; ``None`` if it left no manifest.

    A manifest that is there but unusable raises :class:`_InvalidManifest`: it must not read
    as "no manifest", which would send ``clean`` down the delete-everything legacy path.
    """
    path = destination / MANIFEST_FILENAME
    if not path.is_file():
        return None
    try:
        files = json.loads(path.read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise _InvalidManifest(f"{path} is unreadable ({e})") from None
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise _InvalidManifest(f"{path} does not hold a list of file names")
    for name in files:
        if _inside(destination, name) is None:
            raise _InvalidManifest(
                f"{path} lists {name!r}, which is outside {destination}"
            )
    return set(files)


def _inside(destination: Path, name: str) -> Path | None:
    """``destination / name`` if it stays inside ``destination`` (no ``..``, no absolute
    path, no symlinked directory on the way), else ``None``."""
    relative = Path(name)
    if not name or relative.is_absolute() or ".." in relative.parts:
        return None
    target = destination / relative
    try:
        parent = target.parent.resolve()
        if not parent.is_relative_to(destination.resolve()):
            return None
    except OSError:
        return None
    return target


def _remove_listed(destination: Path, files) -> None:
    """Delete ``files`` (and the manifest) from ``destination``, then the directories that
    deleting emptied; hand-made directories, empty or not, are left alone."""
    parents = set()
    for name in (*files, MANIFEST_FILENAME):
        target = _inside(destination, name)
        if target is None:
            continue
        target.unlink(missing_ok=True)
        parents.update(
            p for p in target.parents if p != destination and destination in p.parents
        )
    for directory in sorted(parents, key=lambda p: len(p.parts), reverse=True):
        if (
            directory.is_dir()
            and not directory.is_symlink()
            and not any(directory.iterdir())
        ):
            directory.rmdir()
    if destination.is_dir() and not any(destination.iterdir()):
        destination.rmdir()


def make(project_dir, *make_args):
    """Build the documentation; ``make_args`` are targets, ``html`` by default.

    :param project_dir: the project root (holding ``docsrc``)
    :param make_args: targets: ``html``, ``doctest``, ``markdown``, ``github``,
        ``gitlab``, ``clean``, or any Sphinx builder name
    """
    config = load_config(project_dir)
    for target in make_args or ("html",):
        build(config, target)


def build(
    config: DocsConfig, target: str = "html", *, overrides: dict | None = None
) -> Path | None:
    """Run one build target for a loaded configuration; returns the output directory.

    :param config: the project's configuration
    :param target: a Sphinx builder name or one of ``github``, ``gitlab``, ``clean``
    :param overrides: configuration overrides forwarded to the generated ``conf.py``
    """
    docsrc = config.docsrc_dir
    build_dir = docsrc / BUILD_DIRNAME
    if target == "clean":
        if build_dir.is_dir():
            shutil.rmtree(build_dir)
        for path in (config.project_dir / d for d in COPY_TARGETS.values()):
            if not path.is_dir():
                continue
            try:
                written = _read_manifest(path)
            except _InvalidManifest as e:
                warnings.warn(
                    f"clean: kept {path}: {e}. Delete it yourself if it is only output.",
                    stacklevel=2,
                )
                continue
            if written is not None:
                # Only what a copy wrote: hand-written files beside it stay.
                _remove_listed(path, written)
            elif is_built_site(path):
                shutil.rmtree(path)
            else:
                warnings.warn(
                    f"clean: kept {path}: it has no {' or '.join(SITE_MARKERS)} (not an epythet build), "
                    "so it may hold hand-written files. Delete it yourself if it is only output.",
                    stacklevel=2,
                )
        return None
    if target in COPY_TARGETS:
        destination = config.project_dir / COPY_TARGETS[target]
        if not is_built_site(destination):
            raise BuildError(
                f"refusing to copy the site into {destination}: it holds files but no "
                f"{' or '.join(SITE_MARKERS)}, so it is not an epythet build and may be hand-written. "
                "Move those files elsewhere (or delete the directory) and retry."
            )
        html_dir = build(config, "html", overrides=overrides)
        files = _site_files(html_dir)
        try:
            previous = _read_manifest(destination) if destination.is_dir() else None
        except _InvalidManifest as e:
            raise BuildError(
                f"refusing to copy the site into {destination}: {e}. Fix or delete the "
                "manifest (and move any hand-written files out) and retry."
            ) from None
        if previous is not None:
            clobbered = [
                f for f in files if f not in previous and (destination / f).exists()
            ]
            if clobbered:
                raise BuildError(
                    f"refusing to copy the site into {destination}: these files are not "
                    f"from an earlier epythet copy and would be overwritten: "
                    f"{', '.join(clobbered[:5])}{' ...' if len(clobbered) > 5 else ''}. "
                    "Move or rename them and retry."
                )
            # Files the earlier copy wrote and this one does not.
            for stale in previous - set(files):
                (destination / stale).unlink(missing_ok=True)
        # Recorded before the copy, as the union with the earlier record, so a copy that
        # dies midway leaves every file it may have written listed (and so cleanable).
        destination.mkdir(parents=True, exist_ok=True)
        (destination / MANIFEST_FILENAME).write_text(
            json.dumps({"files": sorted({*files, *(previous or ())})}, indent=1),
            encoding="utf-8",
        )
        shutil.copytree(html_dir, destination, dirs_exist_ok=True)
        (destination / MANIFEST_FILENAME).write_text(
            json.dumps({"files": files}, indent=1), encoding="utf-8"
        )
        # copytree never deletes: drop provenance files the fresh site no longer has.
        prune_site(
            destination,
            keep_page=(html_dir / f"{ABOUT_PAGE_DOCNAME}.html").is_file(),
            keep_json=(html_dir / BUILD_INFO_FILENAME).is_file(),
        )
        return destination

    outdir = build_dir / target
    # -E: never reuse a pickled environment; a stale one silently drops API pages
    # when the generator or the module set changed, and a full build takes seconds.
    command = [
        sys.executable,
        "-m",
        "sphinx",
        "-E",
        "-b",
        target,
        str(docsrc),
        str(outdir),
    ]
    # The Sphinx process gets the generator already resolved ("auto" probes the
    # import once, here), so conf.py never re-probes or disagrees with the scaffold.
    overrides = {"api_generator": config.resolved_api_generator, **(overrides or {})}
    env = dict(os.environ)
    env["EPYTHET_PROJECT_DIR"] = str(config.project_dir)
    env["EPYTHET_OVERRIDES"] = json.dumps(overrides)
    info = prepare_provenance(config) if target in HTML_TARGETS else None
    if info is not None:
        env[BUILD_INFO_ENV] = json.dumps(info)
    result = subprocess.run(command, cwd=str(docsrc), env=env)
    if result.returncode != 0:
        raise BuildError(
            f"sphinx-build -b {target} failed with exit status {result.returncode} "
            f"(sources: {docsrc})"
        )
    if target in HTML_TARGETS:
        # A source file that survived prepare_provenance is hand-written: keep its page.
        prune_site(
            outdir,
            keep_page=(config.docsrc_dir / ABOUT_PAGE_FILENAME).is_file(),
            keep_json=info is not None,
        )
    if target == "html" and config.agent_outputs:
        inject_link_relations_into_site(outdir)
        write_aggregates(outdir, package_name=config.name, aggregates=config.aggregates)
        if info is not None:
            reference_from_agent_outputs(outdir, info, package_name=config.name)
    return outdir


def prepare_provenance(config: DocsConfig) -> dict | None:
    """Collect the build record and write the about page's source; ``None`` when off.

    Runs before Sphinx so the page is part of the build. The page is removed
    (when it is epythet's own) for ``provenance = false`` and ``"minimal"``,
    so a switched-off project never publishes a stale one. A failure to
    collect is reported once and the build goes on without provenance; a
    wrong ``provenance_template`` is a :class:`~epythet.config.ConfigError`,
    like any other configuration mistake.
    """
    target = config.docsrc_dir / ABOUT_PAGE_FILENAME
    if not config.provenance:
        remove_generated_file(target, markers=(INDEX_MARKER,))
        return None
    template = about_template(config)
    try:
        info = collect_build_info(config)
    except Exception as e:  # provenance never fails a build
        print(f"epythet: build provenance unavailable ({e})", file=sys.stderr)
        return None
    if config.provenance == "minimal":
        remove_generated_file(target, markers=(INDEX_MARKER,))
    else:
        page = about_page(info, template=template)
        write_generated_file(target, page.content, markers=(page.marker,))
    for warning in info["warnings"]:
        print(f"epythet: provenance: {warning}", file=sys.stderr)
    return info
