"""Shared fixtures: a throwaway project builder and an isolated user data dir."""

import os
import textwrap
from pathlib import Path

import pytest


#: 2026-09-15T12:00:00Z; every build in the suite claims this time.
FIXED_BUILD_EPOCH = "1789473600"


@pytest.fixture(autouse=True, scope="session")
def _hermetic_provenance(tmp_path_factory):
    """Provenance in the test suite: no network, a fixed build time, isolated git.

    ``EPYTHET_PYPI_CHECK=0`` keeps PyPI out (offline CI, determinism);
    ``SOURCE_DATE_EPOCH`` makes rebuilds byte-identical; the git variables keep
    the developer's global config (``commit.gpgsign``, hooks, templates) out of
    the fixture repositories. Session-scoped so it is in place before the
    module-scoped smoke builds.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("EPYTHET_PYPI_CHECK", "0")
        mp.setenv("SOURCE_DATE_EPOCH", FIXED_BUILD_EPOCH)
        mp.setenv("GIT_CONFIG_GLOBAL", os.devnull)
        mp.setenv("GIT_CONFIG_NOSYSTEM", "1")
        # A fixture project that is not a repo must not find one above the temp dir.
        mp.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path_factory.getbasetemp()))
        yield


@pytest.fixture
def make_project(tmp_path):
    """``make_project(name, {"mod.py": source, ...})`` -> project root with a pyproject."""

    def build(
        name: str, files: dict[str, str], *, init: str = '"""The package."""\n'
    ) -> Path:
        project = tmp_path / name
        (project / name).mkdir(parents=True)
        (project / "pyproject.toml").write_text(
            textwrap.dedent(
                f"""
                [project]
                name = "{name}"
                version = "0.0.1"
                """
            )
        )
        (project / name / "__init__.py").write_text(init)
        for relative, source in files.items():
            target = project / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source)
        return project

    return build


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point every user-data write (observations, packets, proposals) at a temp dir."""
    target = tmp_path / "epythet-data"
    monkeypatch.setenv("EPYTHET_DATA_DIR", str(target))
    return target


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Point the user config dir (config.toml, snippets/) at a temp dir."""
    target = tmp_path / "epythet-config"
    monkeypatch.setenv("EPYTHET_CONFIG_DIR", str(target))
    return target
