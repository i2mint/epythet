"""Run Sphinx for a project, without ``make`` or a ``Makefile``.

``sphinx-build`` is invoked as ``python -m sphinx`` with the *current*
interpreter, so the build uses exactly the environment epythet was installed
into. The project root and any command-line overrides reach the generated
``conf.py`` through environment variables (see :mod:`epythet.sphinx_conf`).

Targets mirror the old Makefile: ``html`` (the default), ``doctest``,
``markdown``, ``github`` (``html`` then a copy into ``PROJECT_DIR/docs``),
``gitlab`` (copy into ``public``) and ``clean``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from epythet.agent_outputs import write_aggregates
from epythet.config import DocsConfig, load_config

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
    env = dict(os.environ)
    env["EPYTHET_PROJECT_DIR"] = str(config.project_dir)
    env["EPYTHET_OVERRIDES"] = json.dumps(overrides or {})
    result = subprocess.run(command, cwd=str(docsrc), env=env)
    if result.returncode != 0:
        raise BuildError(
            f"sphinx-build -b {target} failed with exit status {result.returncode} "
            f"(sources: {docsrc})"
        )
    if target == "html" and config.agent_outputs:
        write_aggregates(outdir, package_name=config.name, aggregates=config.aggregates)
    return outdir
