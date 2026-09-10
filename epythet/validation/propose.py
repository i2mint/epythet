"""``epythet ledger propose``: turn a review reply's ``proposed_rules`` into overlay rules.

A proposal is a rule file plus its fixture, exactly like a bundled rule, with
one difference: ``status: {proposed: {...}}``. The ledger loader skips
proposed rules unless asked for them (``Ledger.of_kind(..., include_proposed=True)``),
so a proposal never gates anyone; a maintainer promotes it by moving the two
files into ``epythet/ledger/rules/<group>/`` and replacing the status.

Ids are allocated after the highest id in the bundled ledger *and* the
overlay, so a proposal never collides with a rule that ships later. The
fixture is generated from the reply's ``example_bad`` and ``example_good``
docstrings, tagged ``# ruleid:`` and ``# ok:`` the way every bundled fixture
is; the overlay is then re-loaded through the normal loader, and a proposal
that does not pass its own fixture is deleted again and reported.

>>> from epythet.validation.propose import next_rule_id
>>> next_rule_id(["DR001", "DR035", "DQ003"], prefix="DR")
'DR036'
>>> next_rule_id([], prefix="DR")
'DR001'
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from epythet.validation.ledger import (
    PARSE_KINDS,
    Ledger,
    LedgerError,
    load_ledger,
    load_rule,
    proposed_rules_dir,
)
from epythet.validation.review import ReplyError, load_reply

#: Rule id prefix per namespace (``DR`` is the historical prefix for everything rendering-related).
PREFIX_FOR_NAMESPACE = {
    "rendering": "DR",
    "source": "DR",
    "semantics": "DS",
    "coverage": "DQ",
}
_ID_RE = re.compile(r"^([A-Z]{2,4})(\d{3,4})$")


def next_rule_id(existing: Iterable[str], *, prefix: str) -> str:
    """The first free id with ``prefix`` after every existing one with that prefix."""
    highest = 0
    for rule_id in existing:
        match = _ID_RE.match(rule_id)
        if match and match.group(1) == prefix:
            highest = max(highest, int(match.group(2)))
    return f"{prefix}{highest + 1:03d}"


def _yaml_scalar(value: str) -> str:
    """A double-quoted YAML scalar."""
    return json.dumps(value, ensure_ascii=False)


def _yaml_block(text: str, indent: int = 2) -> str:
    pad = " " * indent
    return "|\n" + "\n".join(pad + line if line.strip() else "" for line in text.rstrip("\n").splitlines()) + "\n"


def rule_yaml(rule_id: str, proposal: dict[str, Any], *, source: str) -> str:
    """The YAML text of a proposed rule (hand-written, so the layout matches the bundled files)."""
    detector = proposal["detector"]
    lines = [
        f"id: {rule_id}",
        f"title: {_yaml_scalar(proposal['title'])}",
        f"namespace: {proposal['namespace']}",
        f'status: {{proposed: {{date: "{datetime.now(timezone.utc).date().isoformat()}", source: {_yaml_scalar(source)}}}}}',
        f"severity: {proposal['severity']}",
        f"precision: {proposal['precision']}",
        "detector:",
        f"  kind: {detector['kind']}",
    ]
    for key in ("node", "function", "scan", "skip_doctest_lines", "whole_text", "ignore_case"):
        if key in detector:
            value = detector[key]
            lines.append(
                f"  {key}: {str(value).lower() if isinstance(value, bool) else _yaml_scalar(str(value))}"
            )
    if "pattern" in detector:
        lines.append("  pattern: " + _yaml_block(detector["pattern"], indent=4).rstrip("\n"))
    lines.append(f"message: {_yaml_scalar(proposal['message'])}")
    fix = proposal.get("fix") or {}
    lines.append("fix:")
    lines.append(f"  hint: {_yaml_scalar(str(fix.get('hint', '')))}")
    lines.append(f"  autofixable: {str(bool(fix.get('autofixable', False))).lower()}")
    if fix.get("strategy"):
        lines.append(f"  strategy: {_yaml_scalar(str(fix['strategy']))}")
    explanation = proposal.get("explanation") or proposal["title"]
    lines.append("explanation: " + _yaml_block(explanation).rstrip("\n"))
    lines.append("references:")
    lines.append("  - https://github.com/i2mint/epythet/discussions/15")
    return "\n".join(lines) + "\n"


def _indent_docstring(text: str) -> str:
    body = text.strip("\n")
    return "\n".join(("    " + line) if line.strip() else "" for line in body.splitlines())


def fixture_py(rule_id: str, proposal: dict[str, Any]) -> str:
    """The sibling fixture: one ``# ruleid:`` specimen and one ``# ok:`` specimen.

    The quote style is whichever the examples do not contain; an example that
    contains both triple quotes (or a backslash) is refused, because the
    fixture would not round-trip through ``ast``.
    """
    examples = (proposal["example_bad"], proposal["example_good"])
    for quote in ('"""', "'''"):
        if not any(quote in example or "\\" in example for example in examples):
            break
    else:
        raise LedgerError("example_bad/example_good must not contain both triple quotes or a backslash")
    title = proposal["title"].replace("\n", " ")
    return (
        f'"""Fixture for {rule_id}: {title} (proposed).\n\n'
        'Written by ``epythet ledger propose``; edit the specimens if the rule is refined.\n"""\n\n\n'
        f"def bad_case():  # ruleid: {rule_id}\n"
        f"    {quote}\n{_indent_docstring(examples[0])}\n    {quote}\n\n\n"
        f"def good_case():  # ok: {rule_id}\n"
        f"    {quote}\n{_indent_docstring(examples[1])}\n    {quote}\n"
    )


@dataclass
class ProposalResult:
    """What ``propose`` wrote, and what it refused."""

    overlay: Path
    written: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


def propose(
    reply_path: str | Path,
    *,
    overlay: str | Path | None = None,
    ledger: Ledger | str | Path | None = None,
) -> ProposalResult:
    """Write every ``proposed_rules`` entry of a reply into ``overlay`` as a proposed rule."""
    reply = load_reply(Path(reply_path))
    overlay_dir = Path(overlay) if overlay else proposed_rules_dir()
    overlay_dir.mkdir(parents=True, exist_ok=True)
    catalog = load_ledger(ledger)
    known = set(catalog.rules)
    for path in overlay_dir.rglob("*.yaml"):
        known.add(path.stem)
    result = ProposalResult(overlay=overlay_dir)
    for proposal in reply.get("proposed_rules", []):
        prefix = PREFIX_FOR_NAMESPACE.get(proposal["namespace"], "DR")
        rule_id = next_rule_id(known, prefix=prefix)
        known.add(rule_id)
        yaml_path = overlay_dir / f"{rule_id}.yaml"
        py_path = yaml_path.with_suffix(".py")
        try:
            yaml_path.write_text(rule_yaml(rule_id, proposal, source=str(reply_path)), encoding="utf-8")
            py_path.write_text(fixture_py(rule_id, proposal), encoding="utf-8")
            rule = load_rule(yaml_path)
            if rule.kind in PARSE_KINDS:
                _check_fixture_fires(rule)
        except LedgerError as e:
            yaml_path.unlink(missing_ok=True)
            py_path.unlink(missing_ok=True)
            result.rejected.append(f"{proposal['title']}: {e}")
            continue
        result.written.append(rule_id)
    return result


def _check_fixture_fires(rule) -> None:
    """The proposal's own examples must behave: the bad one fires, the good one does not."""
    from epythet.validation.ledger import iter_fixture_cases
    from epythet.validation.parse import evaluate_rule, parse_docstring

    for case in iter_fixture_cases(rule.fixture_path):
        if rule.id not in case.rule_ids:
            continue
        hits = evaluate_rule(rule, parse_docstring(case.docstring))
        if case.expect_hit and not hits:
            raise LedgerError(f"{rule.id}: the detector does not fire on example_bad")
        if not case.expect_hit and hits:
            raise LedgerError(f"{rule.id}: the detector fires on example_good")


def propose_command(reply: str, *, overlay: str | None = None, ledger: str | None = None) -> None:
    """Write a review reply's proposed rules into a ledger overlay as ``status: proposed`` rules.

    :param reply: A review.json written by a reviewer (see the packet's INSTRUCTIONS.md).
    :param overlay: Directory to write into (default: <user data dir>/ledger/proposed).
    :param ledger: An extra overlay whose ids must not be reused.
    """
    import cw

    try:
        result = propose(reply, overlay=overlay, ledger=ledger)
    except (ReplyError, LedgerError, FileNotFoundError) as e:
        raise cw.CommandError(str(e), code=2) from e
    for rule_id in result.written:
        print(f"proposed {rule_id}: {result.overlay / rule_id}.yaml (+ .py fixture)")
    for reason in result.rejected:
        print(f"rejected: {reason}")
    if not result.written and not result.rejected:
        print("nothing to propose: the reply has no proposed_rules")
    print(f"use them with: epythet validate <package> --ledger {result.overlay}")
    if result.rejected:
        raise cw.CommandError(f"{len(result.rejected)} proposal(s) rejected", code=2)
