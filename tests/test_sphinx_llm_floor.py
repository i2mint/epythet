"""The sphinx-llm floor must support the suffix mode agent_outputs pins.

sphinx-llm 1.0.0 refuses ``llms_txt_suffix_mode="append"`` (it only knows file-suffix,
url-suffix, auto and replace) and stops the build, and pip keeps an environment that
already satisfies a lower floor. So the declared floor must be 1.1 or later.
"""

import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
APPEND_SINCE = (1, 1)


def _floor(requirement: str) -> tuple[int, ...]:
    m = re.search(r">=\s*([0-9.]+)", requirement)
    assert m, f"no lower bound in {requirement!r}"
    return tuple(int(p) for p in m.group(1).split("."))


def test_the_sphinx_llm_floor_supports_the_pinned_suffix_mode():
    from epythet import agent_outputs

    deps = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    (req,) = [d for d in deps if d.replace("_", "-").startswith("sphinx-llm")]
    source = Path(agent_outputs.__file__).read_text()
    if '"llms_txt_suffix_mode": "append"' in source:
        assert _floor(req) >= APPEND_SINCE
