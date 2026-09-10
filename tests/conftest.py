"""Shared fixtures: a throwaway project builder and an isolated user data dir."""

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def make_project(tmp_path):
    """``make_project(name, {"mod.py": source, ...})`` -> project root with a pyproject."""

    def build(name: str, files: dict[str, str], *, init: str = '"""The package."""\n') -> Path:
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
