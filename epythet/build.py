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
from pathlib import Path

from epythet.agent_outputs import inject_link_relations_into_site, write_aggregates
from epythet.config import DocsConfig, load_config
from epythet.provenance import (
    BUILD_INFO_ENV,
    about_page,
    collect_build_info,
    reference_from_agent_outputs,
)

BUILD_DIRNAME = "_build"
COPY_TARGETS = {"github": "docs", "gitlab": "public"}


class BuildError(RuntimeError):
    """Sphinx exited with a non-zero status."""


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
        for path in (
            build_dir,
            *(config.project_dir / d for d in COPY_TARGETS.values()),
        ):
            if path.is_dir():
                shutil.rmtree(path)
        return None
    if target in COPY_TARGETS:
        html_dir = build(config, "html", overrides=overrides)
        destination = config.project_dir / COPY_TARGETS[target]
        shutil.copytree(html_dir, destination, dirs_exist_ok=True)
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
    info = prepare_provenance(config) if target == "html" else None
    if info is not None:
        env[BUILD_INFO_ENV] = json.dumps(info)
    result = subprocess.run(command, cwd=str(docsrc), env=env)
    if result.returncode != 0:
        raise BuildError(
            f"sphinx-build -b {target} failed with exit status {result.returncode} "
            f"(sources: {docsrc})"
        )
    if target == "html" and config.agent_outputs:
        inject_link_relations_into_site(outdir)
        write_aggregates(outdir, package_name=config.name, aggregates=config.aggregates)
        if info is not None:
            reference_from_agent_outputs(outdir, info, package_name=config.name)
    return outdir


def prepare_provenance(config: DocsConfig) -> dict | None:
    """Collect the build record and write the about page's source; ``None`` when off.

    Runs before Sphinx so the page is part of the build. The about page is
    skipped for ``provenance = "minimal"``. Any failure is reported once and
    the build goes on without provenance.
    """
    if not config.provenance:
        return None
    try:
        info = collect_build_info(config)
        page = about_page(info)
        target = config.docsrc_dir / page.filename
        if config.provenance == "minimal":
            _remove_generated(target, marker=page.marker)
        else:
            _write_generated(target, page.content, marker=page.marker)
        for warning in info["warnings"]:
            print(f"epythet: provenance: {warning}", file=sys.stderr)
        return info
    except Exception as e:  # provenance never fails a build
        print(f"epythet: build provenance unavailable ({e})", file=sys.stderr)
        return None


def _write_generated(path: Path, content: str, *, marker: str) -> None:
    """Write a generated file unless a hand-written one (no marker) is in the way."""
    if path.exists() and marker not in path.read_text(
        encoding="utf-8", errors="replace"
    ):
        return
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def _remove_generated(path: Path, *, marker: str) -> None:
    if path.is_file() and marker in path.read_text(encoding="utf-8", errors="replace"):
        path.unlink()
