"""``epythet sweep``: validate many packages read-only and rank the queue.

The fleet has some two hundred packages and one question about each rule:
how often does it fire, and where? Severities in the ledger are decided by
that distribution, not by intuition (decision D9). The sweep runs
:func:`epythet.validation.validate` at level 0 (the coverage detectors, no
linters unless asked) and level 0.5 (the doctree of every docstring) over
each package, never writes into any of them, appends what it saw to the
observations file outside the repositories, and reports two things:

- the **rule distribution**: per rule, how many findings, in how many
  packages, and the rate per hundred public objects;
- the **queue**: packages ranked by how much documentation work they hold,
  weighted the way the doc-quality research orders the work (entry points
  first: an entry point without an example outranks a helper without a
  summary; a rendering error outranks both).

Packages come from directories on the command line, or from a manifest: a
``.pth``-style file with one project directory per line (the local package
manifest is exactly that). The manifest is read, never written.

>>> from epythet.sweep import queue_score
>>> queue_score({"DQ002": 3, "DR003": 1, "DQ004": 2}, severities={"DR003": "error"})
18.0
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from epythet.validation.core import resolve_package, validate
from epythet.validation.ledger import Ledger, load_ledger, user_data_dir
from epythet.validation.model import Report

DEFAULT_LEVELS = (0, 0.5)
#: How much one finding of a rule weighs in the queue (research_doc_quality §4.3:
#: examples first, then correctness, then the summary, then parameter semantics).
RULE_WEIGHTS = {
    "DQ002": 4.0,  # entry point without a runnable example
    "DQ001": 3.0,  # public object without a docstring
    "DQ003": 1.0,  # trivial summary
    "DQ005": 1.0,  # meta-language summary
    "DQ004": 0.5,  # type restatement
}
#: Weight per severity for rendering findings (level 0.5) not listed above.
SEVERITY_WEIGHTS = {"error": 5.0, "warning": 2.0, "info": 0.5}
FORMATS = ("table", "json")


def queue_score(counts: dict[str, int], *, severities: dict[str, str]) -> float:
    """The queue weight of a package from its per-rule finding counts."""
    total = 0.0
    for rule, count in counts.items():
        weight = RULE_WEIGHTS.get(rule)
        if weight is None:
            weight = SEVERITY_WEIGHTS.get(severities.get(rule, "info"), 0.5)
        total += weight * count
    return total


@dataclass
class PackageSweep:
    """What the sweep saw in one package."""

    path: str
    name: str
    version: str | None = None
    objects: int = 0
    undocumented: int = 0
    counts: Counter = field(default_factory=Counter)
    severities: dict[str, str] = field(default_factory=dict)
    duration_s: float = 0.0
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        return queue_score(self.counts, severities=self.severities)

    def top_rules(self, n: int = 3) -> list[tuple[str, int]]:
        return self.counts.most_common(n)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "version": self.version,
            "objects": self.objects,
            "undocumented": self.undocumented,
            "score": round(self.score, 1),
            "counts": dict(self.counts),
            "duration_s": round(self.duration_s, 2),
            "error": self.error,
        }


@dataclass
class SweepResult:
    """Every package swept, the rule distribution and the ranked queue."""

    packages: list[PackageSweep] = field(default_factory=list)
    levels: tuple[float, ...] = DEFAULT_LEVELS
    started: str = ""
    duration_s: float = 0.0
    ledger_severity: dict[str, str] = field(default_factory=dict)
    ledger_title: dict[str, str] = field(default_factory=dict)

    @property
    def swept(self) -> list[PackageSweep]:
        return [p for p in self.packages if p.error is None]

    def distribution(self) -> list[dict[str, Any]]:
        """Per rule: findings, packages affected, rate per 100 public objects; most frequent first."""
        totals: Counter = Counter()
        affected: Counter = Counter()
        for package in self.swept:
            for rule, count in package.counts.items():
                totals[rule] += count
                affected[rule] += 1
        objects = sum(p.objects for p in self.swept) or 1
        rows = []
        for rule, count in totals.most_common():
            rows.append(
                {
                    "rule": rule,
                    "title": self.ledger_title.get(rule, ""),
                    "severity": self.ledger_severity.get(rule, ""),
                    "findings": count,
                    "packages": affected[rule],
                    "package_share": round(affected[rule] / max(len(self.swept), 1), 2),
                    "per_100_objects": round(100 * count / objects, 2),
                }
            )
        return rows

    def queue(self) -> list[PackageSweep]:
        """Packages by descending queue score."""
        return sorted(self.swept, key=lambda p: (-p.score, p.name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "started": self.started,
            "duration_s": round(self.duration_s, 1),
            "levels": list(self.levels),
            "packages": [p.to_dict() for p in self.packages],
            "distribution": self.distribution(),
            "queue": [
                {"name": p.name, "score": round(p.score, 1), "top": p.top_rules()}
                for p in self.queue()
            ],
        }


def packages_from_manifest(path: str | os.PathLike) -> list[Path]:
    """Project directories listed in a ``.pth``-style manifest (one per line, ``#`` comments)."""
    dirs = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("import "):
            continue
        dirs.append(Path(os.path.expandvars(line)).expanduser())
    return dirs


def _counts(report: Report) -> tuple[Counter, dict[str, str]]:
    counts: Counter = Counter()
    severities: dict[str, str] = {}
    for finding in report.findings:
        counts[finding.rule] += 1
        severities.setdefault(finding.rule, finding.severity)
    return counts, severities


def sweeps_path() -> Path:
    """Where sweep summaries are appended: ``<user data dir>/ledger/sweeps.jsonl``."""
    return user_data_dir() / "ledger" / "sweeps.jsonl"


def sweep(
    dirs: Iterable[str | os.PathLike] = (),
    *,
    manifest: str | os.PathLike | None = None,
    levels: Iterable[float] = DEFAULT_LEVELS,
    ignore: Iterable[str] = (),
    ledger: Ledger | str | os.PathLike | None = None,
    napoleon: bool = True,
    linters: bool = False,
    observe: bool = True,
    observations_path: str | os.PathLike | None = None,
    record: bool = True,
    limit: int | None = None,
    on_package=None,
) -> SweepResult:
    """Validate every package under ``dirs`` and ``manifest`` read-only; return the result.

    Args:
        dirs: Project or package directories.
        manifest: A ``.pth``-style file of project directories, read only.
        levels: The validate levels to run (``0`` coverage, ``0.5`` parse by default).
        ignore: Path substrings to skip inside each package.
        ledger: The rule catalog (``None`` = bundled).
        napoleon: Parse docstrings with napoleon's pre-processing.
        linters: Also shell out to ruff and pydoclint at level 0.
        observe: Append each package's findings to the observations file.
        observations_path: Override the observations file (tests use this).
        record: Append the sweep summary to ``sweeps.jsonl`` under the user data dir.
        limit: Sweep at most this many packages.
        on_package: Called with each :class:`PackageSweep` as it completes.
    """
    catalog = load_ledger(ledger)
    result = SweepResult(
        levels=tuple(levels),
        started=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ledger_severity={r.id: r.severity for r in catalog},
        ledger_title={r.id: r.title for r in catalog},
    )
    candidates = [Path(d) for d in dirs]
    if manifest is not None:
        candidates += packages_from_manifest(manifest)
    if limit is not None:
        candidates = candidates[:limit]
    start = time.perf_counter()
    for candidate in candidates:
        package = PackageSweep(path=str(candidate), name=candidate.name)
        began = time.perf_counter()
        try:
            resolved = resolve_package(candidate)
            package.name, package.version = resolved.name, resolved.version
            report = validate(
                candidate,
                levels=levels,
                ledger=catalog,
                napoleon=napoleon,
                ignore=ignore,
                observe=observe,
                observations_path=observations_path,
                linters=linters,
            )
        except Exception as e:  # one broken checkout must not stop the fleet
            package.error = f"{type(e).__name__}: {str(e)[:200]}"
        else:
            package.objects = report.objects_checked
            package.undocumented = report.objects_undocumented
            package.counts, package.severities = _counts(report)
            package.notes = [n for n in report.notes if "skipped" in n]
        package.duration_s = time.perf_counter() - began
        result.packages.append(package)
        if on_package is not None:
            on_package(package)
    result.duration_s = time.perf_counter() - start
    if record and result.packages:
        path = sweeps_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
    return result


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_sweep(result: SweepResult, *, top: int = 20) -> str:
    """The human report: distribution table, then the queue."""
    lines = [
        f"epythet sweep: {len(result.swept)} package(s) swept"
        f"{f', {len(result.packages) - len(result.swept)} failed' if len(result.packages) != len(result.swept) else ''}"
        f" in {result.duration_s:.0f}s; levels {', '.join(f'{lv:g}' for lv in result.levels)};"
        f" {sum(p.objects for p in result.swept)} public objects,"
        f" {sum(p.undocumented for p in result.swept)} undocumented"
    ]
    lines.append("")
    lines.append(f"{'rule':<10}{'severity':<9}{'findings':>9}{'packages':>9}{'share':>7}{'/100 obj':>10}  title")
    for row in result.distribution():
        lines.append(
            f"{row['rule']:<10}{row['severity']:<9}{row['findings']:>9}{row['packages']:>9}"
            f"{row['package_share']:>7.0%}{row['per_100_objects']:>10.1f}  {row['title']}"
        )
    lines.append("")
    lines.append(f"queue (top {top}; score = weighted findings, entry points first):")
    for package in result.queue()[:top]:
        top_rules = ", ".join(f"{rule}×{count}" for rule, count in package.top_rules())
        lines.append(
            f"  {package.score:>7.1f}  {package.name:<24} {package.objects:>5} obj  {top_rules}"
        )
    failed = [p for p in result.packages if p.error]
    if failed:
        lines.append("")
        lines.append("not swept:")
        lines += [f"  {p.path}: {p.error}" for p in failed]
    return "\n".join(lines)


def sweep_command(
    *dirs: str,
    manifest: str | None = None,
    parse_only: bool = False,
    linters: bool = False,
    ignore: list[str] | None = None,
    ledger: str | None = None,
    no_napoleon: bool = False,
    no_observe: bool = False,
    limit: int | None = None,
    format: str = "table",
    top: int = 20,
    output: str | None = None,
    quiet: bool = False,
) -> None:
    """Validate many packages read-only; print the rule distribution and the work queue.

    Runs level 0 (coverage detectors) and level 0.5 (every docstring's
    doctree) over each package; never writes into a package or the manifest.

    :param dirs: Project or package directories to sweep.
    :param manifest: A .pth-style file listing project directories, one per line (read only).
    :param parse_only: Run level 0.5 only (skip the coverage detectors).
    :param linters: Also run ruff and pydoclint at level 0 (slower).
    :param ignore: Skip files whose path contains this string (repeat -i for several).
    :param ledger: Directory of extra rule YAML files overlaid on the bundled ledger.
    :param no_napoleon: Parse docstrings without napoleon's Google/NumPy pre-processing.
    :param no_observe: Do not append findings (or the sweep summary) to the user data dir.
    :param limit: Sweep at most this many packages.
    :param format: table (human) or json (the full result).
    :param top: How many packages the queue shows.
    :param output: Write the report to this file instead of stdout.
    :param quiet: Do not print progress on stderr.
    """
    import sys

    import cw

    if format not in FORMATS:
        raise cw.CommandError(f"--format must be one of {list(FORMATS)}", code=2)
    if not dirs and manifest is None:
        raise cw.CommandError("give at least one directory or --manifest", code=2)

    def progress(package: PackageSweep) -> None:
        if quiet:
            return
        state = package.error or f"{package.objects} objects, {sum(package.counts.values())} findings"
        sys.stderr.write(f"  {package.name}: {state} ({package.duration_s:.1f}s)\n")

    try:
        result = sweep(
            dirs or (),
            manifest=manifest,
            levels=(0.5,) if parse_only else DEFAULT_LEVELS,
            ignore=ignore or (),
            ledger=ledger,
            napoleon=not no_napoleon,
            linters=linters,
            observe=not no_observe,
            record=not no_observe,
            limit=limit,
            on_package=progress,
        )
    except FileNotFoundError as e:
        raise cw.CommandError(str(e), code=2) from e
    text = render_sweep(result, top=top) if format == "table" else json.dumps(result.to_dict(), indent=2)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
