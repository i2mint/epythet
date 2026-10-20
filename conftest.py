"""Repo-level pytest configuration.

``epythet/ledger/rules/**.py`` are ledger fixtures: deliberately bad (and good)
docstrings that ``epythet validate`` checks against. They are data, not tests,
so ``--doctest-modules`` must not collect them. Modules whose doctests need an
optional extra are skipped when it is not installed.
"""

from importlib.util import find_spec

collect_ignore = ["epythet/ledger/rules"]

#: Module -> the optional dependency its doctests need (the ``migrate`` extra).
_NEEDS_EXTRA = {"epythet/migrate.py": "docstring_parser"}
collect_ignore += [path for path, dep in _NEEDS_EXTRA.items() if not find_spec(dep)]
