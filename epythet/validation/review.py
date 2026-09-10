"""Level 3: a review *packet* for an in-session agent, and the ingestion of its reply.

Level 3 never calls a model itself and never gates (decision D8; research
§7.3). It packs what a reviewer needs into one directory under the user data
dir and stops:

- ``pages/<docname>.txt``: the ``-b text`` render of the pages to review
  (changed against the snapshot when there is one, else a sample), which is
  about nine times fewer tokens than the HTML (research §7.3);
- ``screenshots/<docname>.png``: optional, when Playwright is installed and
  ``screenshots=True``;
- ``rubric.md``: the six-dimension rubric, the ledger's rule ids for
  grounding, and the review controls;
- ``schema.json``: the strict JSON schema the reply must satisfy;
- ``packet.json``: the manifest (package, version, pages, prompt hash).

An agent (through a skill; the maintainer's decision 7) reads the packet and
writes ``review.json``. Passing that file back as ``review_reply=`` turns its
``findings`` into level-3 findings and leaves its ``proposed_rules`` for
``epythet ledger propose``, which writes them as ``status: proposed`` rules
into an overlay for a human to promote.

>>> from epythet.validation.review import REPLY_SCHEMA
>>> sorted(REPLY_SCHEMA["properties"])
['findings', 'model', 'prompt_hash', 'proposed_rules', 'schema_version']
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from epythet.validation.ledger import Ledger, user_data_dir
from epythet.validation.model import SEVERITIES, Finding

REVIEW_LEVEL = 3
#: The rule id of the one finding a packet run always produces.
PACKET_RULE = "REVIEW"
#: The rule id of a reply finding that names no ledger rule.
UNRULED = "REVIEW-PROPOSED"
PAGE_MODES = ("changed", "sample", "all")
DEFAULT_SAMPLE = 8
REPLY_SCHEMA_VERSION = "1"

#: The six dimensions of research_doc_quality §3, scored 0-3 each.
RUBRIC = """\
# Review rubric

Score each documented object on the page 0-3 on the six dimensions below.
Only report an object whose score is 0 or 1 on a dimension, or whose page
shows a rendering artifact. Never report a style preference.

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| A. Summary | absent | restates the name, or meta-language ("This function...") | one verb-first sentence saying what it does | also implies when to reach for it and disambiguates siblings |
| B. Parameter and return semantics | absent | descriptions restate the type | meaning, units, default behaviour | plus interactions, ranges, what the return is keyed or ordered by |
| C. Example presence and runnability | none | present but not runnable (pseudo-code, `...`, no output) | one runnable doctest for the common case | plus a variation or edge case; deterministic |
| D. Failure modes | nothing | exceptions named without cause | each exception paired with its trigger | plus non-exception failure modes |
| E. Cross-references and orientation | none | related name in prose | See Also with 1-3 adjacent callables and why | plus when *not* to use |
| F. Module orientation (per module) | none | one line restating the name | purpose and named entry points | plus a minimal example and the relation to the package |

# What to look for first (research_doc_quality §4.3)

1. Runnable examples. 2. Correctness of every claim (ranks above completeness).
3. A precise, disambiguating one-line summary. 4. Parameter *semantics*, not types.
5. Failure modes. 6. When to use and when not. 7. Consistent terminology.
8. Cross-references, one to three, with reasons.

# Rendering artifacts

A `-b text` page keeps text leaks verbatim: a `:param x:` in running prose,
a `>>>` inside a paragraph, a literal ```` ``` ```` fence, `*args` opening
an emphasis, a `##` heading, a `[text](url)` link. Each of those is a ledger
rule (below). Name the rule id when one fits; otherwise mark the finding
`proposed` and draft a rule under `proposed_rules`.

# Controls

- You are proposing, not gating: nothing here fails a build.
- Report only what is stable: re-read the page in a different order and keep
  the findings you would make both times.
- Name a `rule` from the list below, or write `proposed` and fill in
  `proposed_rules` with a detector a machine can run (a regex over the
  docstring text, or a doctree/html detector name), an `example_bad` and an
  `example_good` docstring, a `message` and a `fix` hint.
- Never invent behaviour: a claim about what code does must come from the
  code or its tests, and an example must have been executed.
- Put the model name in `model` and the packet's `prompt_hash` in the reply.

# Ledger rules you may name
"""

REPLY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "epythet level-3 review reply",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "model", "prompt_hash", "findings", "proposed_rules"],
    "properties": {
        "schema_version": {"const": REPLY_SCHEMA_VERSION},
        "model": {"type": "string", "minLength": 1},
        "prompt_hash": {"type": "string", "minLength": 8},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["page", "rule", "severity", "message"],
                "properties": {
                    "page": {"type": "string"},
                    "object": {"type": ["string", "null"]},
                    "rule": {
                        "type": "string",
                        "pattern": r"^([A-Z]{2,4}\d{3,4}|proposed)$",
                    },
                    "dimension": {"type": "string", "enum": list("ABCDEF")},
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "message": {"type": "string", "minLength": 1},
                    "evidence": {"type": "string"},
                },
            },
        },
        "proposed_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "namespace",
                    "severity",
                    "precision",
                    "detector",
                    "message",
                    "example_bad",
                    "example_good",
                ],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "namespace": {
                        "type": "string",
                        "enum": ["rendering", "source", "semantics", "coverage"],
                    },
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "precision": {
                        "type": "string",
                        "enum": ["very-high", "high", "medium", "low"],
                    },
                    "detector": {
                        "type": "object",
                        "required": ["kind"],
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": ["regex", "source", "doctree", "html"],
                            },
                            "pattern": {"type": "string"},
                            "node": {"type": "string"},
                            "function": {"type": "string"},
                        },
                    },
                    "message": {"type": "string", "minLength": 1},
                    "fix": {
                        "type": "object",
                        "properties": {
                            "hint": {"type": "string"},
                            "autofixable": {"type": "boolean"},
                            "strategy": {"type": "string"},
                        },
                    },
                    "explanation": {"type": "string"},
                    "example_bad": {"type": "string", "minLength": 1},
                    "example_good": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

INSTRUCTIONS = """\
# How to review this packet

1. Read `rubric.md`.
2. Read each file under `pages/` (and `screenshots/` when present).
3. Write `review.json` in this directory, valid against `schema.json`.
4. Feed it back: `epythet validate <package> --level 4 --review-reply <this dir>/review.json`
   turns its findings into level-3 findings (informational unless
   `--fail-on-review`), and `epythet ledger propose <this dir>/review.json`
   writes its `proposed_rules` as `status: proposed` rules for a human to promote.
"""


@dataclass
class ReviewPacket:
    """Where a packet was written and what went into it."""

    path: Path
    pages: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    prompt_hash: str = ""
    notes: list[str] = field(default_factory=list)


def reviews_dir() -> Path:
    """``<user data dir>/review``: one subdirectory per package, one per run below it."""
    return user_data_dir() / "review"


def rubric_text(ledger: Ledger) -> str:
    """The rubric with the ledger's rule ids appended, so replies can name them."""
    rules = "\n".join(
        f"- {rule.id}: {rule.title}"
        for rule in sorted(ledger, key=lambda r: r.id)
        if not rule.is_proposed
    )
    return RUBRIC + rules + "\n"


def _prompt_hash(rubric: str, schema: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(rubric.encode("utf-8"))
    digest.update(json.dumps(schema, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:16]


def _text_pages(text_dir: Path) -> dict[str, Path]:
    from epythet.validation.rendered import _pages

    return dict(_pages(text_dir, ".txt"))


def select_pages(
    available: Iterable[str],
    *,
    mode: str = "changed",
    changed: Iterable[str] | None = None,
    sample: int = DEFAULT_SAMPLE,
) -> list[str]:
    """Which pages go into the packet.

    ``changed`` mode uses the snapshot diff when there is one and falls back
    to ``sample`` (the first ``sample`` API pages, index first) otherwise;
    ``all`` takes every page.

    >>> select_pages(["index", "api", "_autosummary/p", "_autosummary/p.m"], mode="sample", sample=2)
    ['index', '_autosummary/p']
    >>> select_pages(["index", "a"], mode="changed", changed=["a"])
    ['a']
    """
    available = list(available)
    if mode not in PAGE_MODES:
        raise ValueError(f"mode must be one of {PAGE_MODES}, got {mode!r}")
    if mode == "all":
        return available
    if mode == "changed" and changed is not None:
        wanted = set(changed)
        return [p for p in available if p in wanted]
    ordered = sorted(available, key=lambda p: (p != "index", "_autosummary" not in p, p))
    return ordered[:sample]


def _screenshot(html_dir: Path, docname: str, target: Path) -> bool:
    """Render one HTML page to PNG with Playwright; ``False`` when it cannot."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    page_path = html_dir / f"{docname}.html"
    if not page_path.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(page_path.resolve().as_uri())
            page.screenshot(path=str(target), full_page=True)
            browser.close()
    except Exception:  # Playwright raises its own hierarchy; any failure is "no screenshot"
        return False
    return True


def write_packet(
    *,
    package: str,
    package_version: str | None,
    outdirs: dict[str, Path],
    ledger: Ledger,
    changed: Iterable[str] | None = None,
    mode: str = "changed",
    sample: int = DEFAULT_SAMPLE,
    screenshots: bool = False,
    packet_dir: Path | None = None,
) -> ReviewPacket:
    """Write a review packet and return where it is."""
    text_dir = outdirs.get("text")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(packet_dir) if packet_dir else reviews_dir() / package / run_id
    root.mkdir(parents=True, exist_ok=True)
    packet = ReviewPacket(path=root)
    if text_dir is None:
        packet.notes.append("no text render available; packet has no pages")
        available: dict[str, Path] = {}
    else:
        available = _text_pages(text_dir)
    packet.pages = select_pages(available, mode=mode, changed=changed, sample=sample)
    pages_dir = root / "pages"
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    for docname in packet.pages:
        target = pages_dir / f"{docname}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(available[docname], target)
    if screenshots and "html" in outdirs:
        for docname in packet.pages:
            target = root / "screenshots" / f"{docname}.png"
            if _screenshot(outdirs["html"], docname, target):
                packet.screenshots.append(docname)
        if packet.pages and not packet.screenshots:
            packet.notes.append(
                "screenshots requested but none taken (pip install playwright && playwright install chromium)"
            )
    rubric = rubric_text(ledger)
    packet.prompt_hash = _prompt_hash(rubric, REPLY_SCHEMA)
    (root / "rubric.md").write_text(rubric, encoding="utf-8")
    (root / "schema.json").write_text(json.dumps(REPLY_SCHEMA, indent=2), encoding="utf-8")
    (root / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    manifest = {
        "schema_version": REPLY_SCHEMA_VERSION,
        "package": package,
        "package_version": package_version,
        "run_id": run_id,
        "mode": mode,
        "pages": packet.pages,
        "screenshots": packet.screenshots,
        "prompt_hash": packet.prompt_hash,
        "reply_path": str(root / "review.json"),
    }
    (root / "packet.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    latest = root.parent / "latest.json"
    try:
        latest.write_text(json.dumps({"packet": str(root)}), encoding="utf-8")
    except OSError:
        pass
    return packet


# --------------------------------------------------------------------------
# Replies
# --------------------------------------------------------------------------


class ReplyError(ValueError):
    """A review reply is not valid against :data:`REPLY_SCHEMA`."""


def _check_type(value, expected: str, where: str) -> None:
    kinds = {"object": dict, "array": list, "string": str, "boolean": bool}
    if not isinstance(value, kinds[expected]):
        raise ReplyError(f"{where}: expected {expected}, got {type(value).__name__}")


def _validate_against(schema: dict[str, Any], value, where: str) -> None:
    """A small JSON-schema checker: types, required, enums, patterns, additionalProperties.

    Enough for :data:`REPLY_SCHEMA`, and deliberately not delegated to the
    ``jsonschema`` package: the error text is part of what a reviewing agent
    reads back, so it must not depend on what happens to be installed.
    """
    import re

    if "const" in schema and value != schema["const"]:
        raise ReplyError(f"{where}: must be {schema['const']!r}")
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(
            (t == "null" and value is None) or (t != "null" and isinstance(value, {"string": str}[t]))
            for t in expected
        ):
            raise ReplyError(f"{where}: expected one of {expected}")
        return
    if expected:
        _check_type(value, expected, where)
    if "enum" in schema and value not in schema["enum"]:
        raise ReplyError(f"{where}: must be one of {schema['enum']}, got {value!r}")
    if "pattern" in schema and not re.match(schema["pattern"], value):
        raise ReplyError(f"{where}: {value!r} does not match {schema['pattern']}")
    if "minLength" in schema and len(value) < schema["minLength"]:
        raise ReplyError(f"{where}: must not be empty")
    if expected == "object":
        for key in schema.get("required", ()):
            if key not in value:
                raise ReplyError(f"{where}: missing required key {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise ReplyError(f"{where}: unknown key(s) {unknown}")
        for key, sub in properties.items():
            if key in value:
                _validate_against(sub, value[key], f"{where}.{key}")
    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            _validate_against(schema["items"], item, f"{where}[{index}]")


def validate_reply(reply: dict[str, Any]) -> None:
    """Raise :class:`ReplyError` unless ``reply`` satisfies :data:`REPLY_SCHEMA`."""
    _validate_against(REPLY_SCHEMA, reply, "reply")


def load_reply(path: Path) -> dict[str, Any]:
    """Read and validate a ``review.json``."""
    try:
        reply = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ReplyError(f"{path}: {e}") from e
    validate_reply(reply)
    return reply


def reply_findings(reply: dict[str, Any], ledger: Ledger, *, source: str = "") -> list[Finding]:
    """Turn a reply's ``findings`` into level-3 findings (informational by construction)."""
    findings: list[Finding] = []
    model = reply.get("model", "")
    for item in reply.get("findings", []):
        rule_id = item["rule"]
        known = rule_id in ledger.rules
        findings.append(
            Finding(
                rule=rule_id if rule_id != "proposed" else UNRULED,
                severity=item["severity"],
                level=REVIEW_LEVEL,
                message=item["message"],
                file=item.get("page"),
                object=item.get("object"),
                detector="llm",
                evidence=item.get("evidence", ""),
                fix=ledger[rule_id].fix_hint if known else "",
                tool=f"review:{model}" if model else "review",
            )
        )
    return findings


def run_review_level(
    *,
    package: str,
    package_version: str | None,
    outdirs: dict[str, Path],
    ledger: Ledger,
    changed: Iterable[str] | None = None,
    mode: str = "changed",
    sample: int = DEFAULT_SAMPLE,
    screenshots: bool = False,
    packet_dir: Path | None = None,
    reply: Path | None = None,
) -> tuple[list[Finding], list[str]]:
    """Level 3: write the packet, then ingest ``reply`` when one is given."""
    findings: list[Finding] = []
    notes: list[str] = []
    packet = write_packet(
        package=package,
        package_version=package_version,
        outdirs=outdirs,
        ledger=ledger,
        changed=changed,
        mode=mode,
        sample=sample,
        screenshots=screenshots,
        packet_dir=packet_dir,
    )
    notes += packet.notes
    findings.append(
        Finding(
            rule=PACKET_RULE,
            severity="info",
            level=REVIEW_LEVEL,
            message=(
                f"review packet with {len(packet.pages)} page(s) written to {packet.path} "
                f"(see INSTRUCTIONS.md; reply with --review-reply)"
            ),
            detector="llm",
            evidence=", ".join(packet.pages[:5]),
            file=None,
        )
    )
    if reply is not None:
        loaded = load_reply(Path(reply))
        if loaded.get("prompt_hash") != packet.prompt_hash:
            notes.append(
                f"reply prompt_hash {loaded.get('prompt_hash')!r} differs from this packet's {packet.prompt_hash!r} (rubric or schema changed since the review)"
            )
        found = reply_findings(loaded, ledger, source=str(reply))
        findings += found
        proposals = len(loaded.get("proposed_rules", []))
        notes.append(
            f"review reply: {len(found)} finding(s), {proposals} proposed rule(s)"
            + (" (run: epythet ledger propose <reply>)" if proposals else "")
        )
    return findings, notes
