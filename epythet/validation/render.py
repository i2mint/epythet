"""Renderers for a :class:`~epythet.validation.model.Report`: table, JSON, JSONL.

All three read the same report object, so the human table and the machine
formats can never disagree. The table groups findings by rule and caps each
group, with a trailing "N more" line, so a fleet-wide run stays readable.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Callable

from epythet.validation.model import LEVELS, Report, sort_findings

FORMATS = ("table", "json", "jsonl")


def _level_label(level: float) -> str:
    return f"{level:g} {LEVELS.get(level, '?')}"


def render_table(report: Report, *, max_per_rule: int = 10) -> str:
    """One block per rule, worst severity first, each capped at ``max_per_rule`` lines."""
    counts = report.counts_by_severity()
    lines = [
        f"epythet validate {report.package}  "
        f"levels: {', '.join(_level_label(lv) for lv in report.levels_run)}  "
        f"objects: {report.objects_checked} ({report.objects_undocumented} undocumented)  "
        f"findings: {counts['error']} error, {counts['warning']} warning, {counts['info']} info"
    ]
    groups: "OrderedDict[str, list]" = OrderedDict()
    for finding in sort_findings(report.findings):
        groups.setdefault(finding.rule, []).append(finding)
    for rule, findings in groups.items():
        first = findings[0]
        tool = "" if first.tool == "epythet" else f" [{first.tool}]"
        lines.append("")
        lines.append(
            f"{rule}{tool}  {first.severity}  level {first.level:g}  ({len(findings)})"
        )
        for finding in findings[:max_per_rule]:
            where = finding.location
            obj = f"  {finding.object}" if finding.object else ""
            lines.append(f"  {where}{obj}")
            lines.append(f"      {finding.message}")
        if len(findings) > max_per_rule:
            lines.append(
                f"  … {len(findings) - max_per_rule} more of {rule} (see --format json)"
            )
        if first.fix:
            lines.append(f"  fix: {first.fix}")
    if report.notes:
        lines.append("")
        lines.extend(f"note: {note}" for note in report.notes)
    if not report.findings:
        lines.append("")
        lines.append("no findings")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    """The full JSON document (decision D8), pretty-printed."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def render_jsonl(report: Report) -> str:
    """One finding per line; the summary is not included (use ``json`` for it)."""
    return "\n".join(
        json.dumps(f.to_dict(), ensure_ascii=False) for f in report.findings
    )


RENDERERS: dict[str, Callable[..., str]] = {
    "table": render_table,
    "json": render_json,
    "jsonl": render_jsonl,
}


def render(report: Report, format: str = "table", **kwargs) -> str:
    """Render with the named format (``table``, ``json`` or ``jsonl``)."""
    if format not in RENDERERS:
        raise ValueError(f"format must be one of {FORMATS}, got {format!r}")
    renderer = RENDERERS[format]
    return renderer(report, **kwargs) if format == "table" else renderer(report)
