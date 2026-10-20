"""Repo-level pytest configuration.

``epythet/ledger/rules/**.py`` are ledger fixtures: deliberately bad (and good)
docstrings that ``epythet validate`` checks against. They are data, not tests,
so ``--doctest-modules`` must not collect them.
"""

collect_ignore = ["epythet/ledger/rules"]
