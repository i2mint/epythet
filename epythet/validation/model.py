"""The finding and report model shared by every level of ``epythet validate``.

One in-memory model, several renderers: the human table, the JSON document and
the JSONL stream are all views over the same :class:`Report`, so they can never
disagree. The vocabulary here (severities, levels, exit codes) is the one fixed
in the epythet v2 decision record (discussion #15, decision D8).

Levels are named by *what artifact they read*, not by when they run:

=====  =======  ==================================================
level  name     reads
=====  =======  ==================================================
0      lint     the source text of each docstring (ruff, pydoclint)
0.5    parse    the docutils doctree of each docstring, in isolation
1      build    the Sphinx warning stream
2      render   the built output (owned by WP3, not implemented here)
3      review   an LLM review of rendered pages (WP3, never gates)
=====  =======  ==================================================

The CLI exposes them as a *tier index* (``--level 0`` runs level 0,
``--level 1`` runs levels 0 and 0.5, ``--level 2`` adds the build), which is
what :data:`TIERS` and :func:`levels_for_tier` translate.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

SCHEMA_VERSION = "1"

SEVERITIES = ("error", "warning", "info")
#: Lower rank is worse. Used for ``--fail-on`` comparisons.
SEVERITY_RANK = {name: rank for rank, name in enumerate(SEVERITIES)}

#: Level number -> level name, in run order.
LEVELS: dict[float, str] = {
    0: "lint",
    0.5: "parse",
    1: "build",
    2: "render",
    3: "review",
}
#: Run order of the levels; index into this list is the CLI ``--level`` tier.
TIERS: list[float] = list(LEVELS)
#: Tiers this work package implements. Tiers 3 and 4 (levels 2 and 3) are WP3.
IMPLEMENTED_TIERS = (0, 1, 2)

EXIT_OK = 0
EXIT_INTERNAL = 1
#: Level -> exit code when that level has findings at or above the threshold.
EXIT_FOR_LEVEL: dict[float, int] = {0: 10, 0.5: 11, 1: 12, 2: 13, 3: 14}
EXIT_LEDGER = 20


def levels_for_tier(tier: int) -> list[float]:
    """The levels a CLI tier runs: every level up to and including the tier's.

    >>> levels_for_tier(0)
    [0]
    >>> levels_for_tier(1)
    [0, 0.5]
    >>> levels_for_tier(2)
    [0, 0.5, 1]
    """
    if tier not in range(len(TIERS)):
        raise ValueError(
            f"level must be one of {list(range(len(TIERS)))}, got {tier!r}"
        )
    return TIERS[: tier + 1]


def severity_at_or_above(severity: str, threshold: str) -> bool:
    """True when ``severity`` is at least as serious as ``threshold``.

    >>> severity_at_or_above("error", "warning")
    True
    >>> severity_at_or_above("info", "warning")
    False
    """
    return SEVERITY_RANK[severity] <= SEVERITY_RANK[threshold]


@dataclass
class Finding:
    """One problem found in one place.

    ``rule`` is a ledger rule id (``DR001``) for levels 0.5 and 1, or the
    upstream tool's code (``D102``, ``DOC101``) for level 0, in which case
    ``tool`` names the tool. ``line`` is 1-based and, for docstring findings,
    the line the docstring literal starts on.
    """

    rule: str
    severity: str
    level: float
    message: str
    file: str | None = None
    line: int | None = None
    object: str | None = None
    detector: str = ""
    evidence: str = ""
    fix: str = ""
    autofixable: bool = False
    tool: str = "epythet"
    ledger_occurrences: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready dict; the JSON and JSONL renderers emit exactly this."""
        return asdict(self)

    @property
    def location(self) -> str:
        """``file:line`` for the table renderer, or ``-`` when unknown."""
        if self.file is None:
            return "-"
        return f"{self.file}:{self.line}" if self.line is not None else self.file


@dataclass
class Report:
    """Everything one ``validate`` run produced, plus enough context to reproduce it."""

    package: str
    package_dir: str
    levels_run: list[float]
    findings: list[Finding] = field(default_factory=list)
    durations: dict[str, float] = field(default_factory=dict)
    objects_checked: int = 0
    objects_undocumented: int = 0
    notes: list[str] = field(default_factory=list)
    epythet_version: str | None = None
    sphinx_version: str | None = None
    docutils_version: str | None = None
    schema_version: str = SCHEMA_VERSION

    def counts_by_severity(self) -> dict[str, int]:
        """``{"error": n, "warning": n, "info": n}`` over all findings."""
        counts = {name: 0 for name in SEVERITIES}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    def summary(self) -> dict[str, Any]:
        """The ``summary`` block of the JSON document."""
        return {
            **self.counts_by_severity(),
            "objects_checked": self.objects_checked,
            "objects_undocumented": self.objects_undocumented,
            "findings": len(self.findings),
            "duration_s": {str(k): round(v, 3) for k, v in self.durations.items()},
        }

    def to_dict(self) -> dict[str, Any]:
        """The JSON document described in decision D8."""
        return {
            "schema_version": self.schema_version,
            "package": self.package,
            "package_dir": self.package_dir,
            "epythet_version": self.epythet_version,
            "sphinx_version": self.sphinx_version,
            "docutils_version": self.docutils_version,
            "levels_run": self.levels_run,
            "summary": self.summary(),
            "notes": list(self.notes),
            "findings": [f.to_dict() for f in self.findings],
        }

    def failing_levels(self, fail_on: str = "error") -> list[float]:
        """Levels with at least one finding at or above ``fail_on``, in run order."""
        if fail_on not in SEVERITY_RANK:
            raise ValueError(f"fail_on must be one of {SEVERITIES}, got {fail_on!r}")
        levels = {
            f.level for f in self.findings if severity_at_or_above(f.severity, fail_on)
        }
        return sorted(levels)

    def exit_code(self, fail_on: str = "error") -> int:
        """The process exit code: ``0`` when clean, else the code of the first failing level.

        The *first* (lowest) failing level is reported because it is the first
        gate a CI pipeline would have stopped at.

        >>> r = Report("p", "/p", [0, 0.5])
        >>> r.exit_code()
        0
        >>> r.findings.append(Finding("DR001", "error", 0.5, "leak"))
        >>> r.exit_code(), r.exit_code("info")
        (11, 11)
        >>> r.findings.append(Finding("D102", "warning", 0, "missing"))
        >>> r.exit_code(), r.exit_code("warning")
        (11, 10)
        """
        failing = self.failing_levels(fail_on)
        return EXIT_FOR_LEVEL[failing[0]] if failing else EXIT_OK


class Timer:
    """Records how long each level took, as ``report.durations[level_name]``.

    >>> durations = {}
    >>> with Timer(durations, "parse"):
    ...     pass
    >>> list(durations) == ["parse"] and durations["parse"] >= 0
    True
    """

    def __init__(self, durations: dict[str, float], key: str):
        self.durations, self.key = durations, key

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.durations[self.key] = time.perf_counter() - self._start


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Stable order for every renderer: severity, then rule id, then location."""
    return sorted(
        findings,
        key=lambda f: (SEVERITY_RANK[f.severity], f.rule, f.file or "", f.line or 0),
    )
