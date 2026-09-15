"""Regression tests for i2mint/epythet#31: three validate/repair rule pairs that
used to be mutually exclusive (``D412`` vs what ``repair`` wrote, ``DOC108``
firing on every annotated signature, ``D107`` vs ``DOC301`` over where
``__init__`` is documented). One fixture module per conflict; each must repair
to zero level-0 findings.
"""

import shutil
import textwrap
from pathlib import Path

import pytest

from epythet.repair import repair_source
from epythet.validation.lint import run_lint_level

pytestmark = pytest.mark.skipif(
    shutil.which("ruff") is None or shutil.which("pydoclint") is None,
    reason="ruff and pydoclint must both be installed to exercise level 0",
)

D412_MODULE = '''"""A module."""


def f(x: int) -> int:
    """Add one to x.

    Args:
        x: the value to increment.

    Returns:
        x plus one.

    Examples:
        >>> f(1)
        2
    """
    return x + 1
'''

DOC108_MODULE = '''"""A module."""


def mk_app(funcs: list, app: int | None = None) -> int:
    """Build an app from funcs.

    Args:
        funcs: the functions to expose.
        app: an existing app to extend.

    Returns:
        the built app.
    """
    return app or 0
'''

INIT_DOC_MODULE = '''"""A module."""


class Thing:
    """A thing.

    Args:
        x: the value.
    """

    def __init__(self, x: int):
        self.x = x
'''


def _repaired_package(tmp_path: Path, name: str, module_source: str) -> Path:
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
    (project / name / "__init__.py").write_text('"""The package."""\n')
    repaired = repair_source(module_source).repaired
    (project / name / "mod.py").write_text(repaired)
    return project


@pytest.mark.parametrize(
    "name,source",
    [
        ("d412pkg", D412_MODULE),
        ("doc108pkg", DOC108_MODULE),
        ("initdocpkg", INIT_DOC_MODULE),
    ],
)
def test_repaired_fixture_has_no_level_0_findings(tmp_path, name, source):
    project = _repaired_package(tmp_path, name, source)
    findings, notes = run_lint_level(project / name, project_dir=project)
    assert notes == []
    assert findings == []
