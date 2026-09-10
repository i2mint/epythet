"""The artifact ledger: rule definitions (bundled YAML) and observations (user data dir).

Storage is split by mutability, as decided in the v2 decision record (D8):

- **Rules** are one YAML file per rule under ``epythet/ledger/rules/<group>/``
  (the ``build`` namespace lives in ``build_warnings/``: a directory named
  ``build/`` is dropped from wheels by the project's ``.gitignore``)
  with a sibling ``.py`` fixture that doubles as the regression test. They are
  human-edited, rarely, and ship inside epythet.
- **Observations** (occurrences with file paths and snippets from real repos)
  are append-only JSONL under the user data dir, never inside the repo, because
  they are derived from repositories that are not all public. Occurrence counts
  are a *derived view* over that file, computed on read.

The ``ledger=`` seam of :func:`epythet.validation.validate` accepts ``None``
(bundled rules), a directory (bundled rules plus a package-local overlay,
same id overrides) or a ready :class:`Ledger`.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from epythet.validation.model import SEVERITIES, Finding

BUNDLED_RULES_DIR = Path(__file__).resolve().parent.parent / "ledger" / "rules"

DETECTOR_KINDS = ("regex", "source", "doctree", "build-warning", "html", "llm")
#: Detector kinds evaluated per docstring at level 0.5.
PARSE_KINDS = ("regex", "source", "doctree")
PRECISIONS = ("very-high", "high", "medium", "low")
NAMESPACES = ("rendering", "source", "semantics", "build", "links", "coverage")
RULE_ID_RE = re.compile(r"^[A-Z]{2,4}\d{3,4}$")
FIXTURE_TAG_RE = re.compile(
    r"#\s*(ruleid|ok):\s*([A-Z]{2,4}\d{3,4}(?:\s*,\s*[A-Z]{2,4}\d{3,4})*)"
)


class LedgerError(Exception):
    """A rule file is schema-invalid, a rule id is duplicated, or a fixture is missing.

    ``epythet validate`` maps this to exit code 20 so CI can tell "the catalog is
    broken" apart from "the package has problems".
    """


@dataclass
class Rule:
    """One ledger rule, loaded from its YAML file and validated.

    ``detector`` is the raw mapping from the YAML; the compiled regex (for
    ``regex`` and ``source`` kinds) is available as :attr:`pattern`.
    """

    id: str
    title: str
    namespace: str
    severity: str
    precision: str
    detector: dict[str, Any]
    message: str
    fix: dict[str, Any] = field(default_factory=dict)
    status: dict[str, Any] = field(default_factory=dict)
    applies_to: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    references: list[str] = field(default_factory=list)
    path: Path | None = None

    @property
    def kind(self) -> str:
        """The detector kind: one of :data:`DETECTOR_KINDS`."""
        return self.detector["kind"]

    @property
    def pattern(self) -> re.Pattern | None:
        """Compiled ``detector.pattern`` (multiline; case-insensitive on request)."""
        raw = self.detector.get("pattern")
        if raw is None:
            return None
        flags = re.MULTILINE
        if self.detector.get("ignore_case"):
            flags |= re.IGNORECASE
        return re.compile(raw.strip("\n"), flags)

    @property
    def autofixable(self) -> bool:
        """Whether ``epythet repair`` (WP3) can rewrite this one mechanically."""
        return bool(self.fix.get("autofixable", False))

    @property
    def fix_hint(self) -> str:
        """The one-line fix hint shown next to each finding."""
        return str(self.fix.get("hint", ""))

    @property
    def fixture_path(self) -> Path | None:
        """The sibling ``.py`` fixture, when the rule has one."""
        if self.path is None:
            return None
        candidate = self.path.with_suffix(".py")
        return candidate if candidate.exists() else None

    @property
    def is_proposed(self) -> bool:
        """Whether the rule is still a proposal (level 3 or a human wrote it, nobody promoted it)."""
        return "proposed" in self.status

    def applies(self, *, napoleon: bool) -> bool:
        """Whether the rule is live under the given napoleon setting.

        A rule that declares ``applies_to: {napoleon: false}`` only makes sense
        when Google/NumPy sections are *not* pre-processed (DR012 is the case).
        """
        wanted = self.applies_to.get("napoleon")
        return wanted is None or wanted == napoleon

    def format_message(self, match: str) -> str:
        """Fill the rule's message template with the matched evidence."""
        try:
            return self.message.format(match=match)
        except (KeyError, IndexError):
            return self.message

    def finding(
        self,
        *,
        level: float,
        evidence: str = "",
        file: str | None = None,
        line: int | None = None,
        object: str | None = None,
        message: str | None = None,
    ) -> Finding:
        """A :class:`Finding` for this rule at one location."""
        return Finding(
            rule=self.id,
            severity=self.severity,
            level=level,
            message=message if message is not None else self.format_message(evidence),
            file=file,
            line=line,
            object=object,
            detector=self.kind,
            evidence=evidence,
            fix=self.fix_hint,
            autofixable=self.autofixable,
            strategy=str(self.fix.get("strategy", "")),
        )


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as e:  # pragma: no cover - environment dependent
        raise LedgerError(
            "reading ledger rules needs PyYAML: pip install 'epythet[validate]'"
        ) from e
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise LedgerError(f"{path}: not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise LedgerError(f"{path}: expected a mapping at the top level")
    return data


_REQUIRED = ("id", "title", "namespace", "severity", "precision", "detector", "message")
_OPTIONAL = ("fix", "status", "applies_to", "explanation", "references")


def _require_bool(value, *, path: Path, field_name: str) -> None:
    if value is not None and not isinstance(value, bool):
        raise LedgerError(
            f"{path}: {field_name} must be a YAML boolean (true/false), got {value!r}"
        )


def _validate_rule_data(data: dict[str, Any], path: Path) -> None:
    """Raise :class:`LedgerError` unless ``data`` is a well-formed rule."""
    missing = [key for key in _REQUIRED if key not in data]
    if missing:
        raise LedgerError(f"{path}: missing required field(s) {missing}")
    unknown = sorted(set(data) - set(_REQUIRED) - set(_OPTIONAL))
    if unknown:
        raise LedgerError(f"{path}: unknown field(s) {unknown}")
    rule_id = data["id"]
    if not isinstance(rule_id, str) or not RULE_ID_RE.match(rule_id):
        raise LedgerError(f"{path}: id {rule_id!r} must look like DR001")
    if path.stem != rule_id:
        raise LedgerError(f"{path}: file name must match rule id {rule_id!r}")
    if data["severity"] not in SEVERITIES:
        raise LedgerError(f"{path}: severity must be one of {SEVERITIES}")
    if data["precision"] not in PRECISIONS:
        raise LedgerError(f"{path}: precision must be one of {PRECISIONS}")
    if data["namespace"] not in NAMESPACES:
        raise LedgerError(f"{path}: namespace must be one of {NAMESPACES}")
    for section in ("fix", "status", "applies_to"):
        if section in data and not isinstance(data[section], dict):
            raise LedgerError(f"{path}: {section} must be a mapping")
    _require_bool(
        data.get("fix", {}).get("autofixable"), path=path, field_name="fix.autofixable"
    )
    _require_bool(
        data.get("applies_to", {}).get("napoleon"),
        path=path,
        field_name="applies_to.napoleon",
    )
    detector = data["detector"]
    if not isinstance(detector, dict) or detector.get("kind") not in DETECTOR_KINDS:
        raise LedgerError(f"{path}: detector.kind must be one of {DETECTOR_KINDS}")
    kind = detector["kind"]
    for key in ("pattern", "message_pattern"):
        if detector.get(key):
            try:
                re.compile(detector[key])
            except re.error as e:
                raise LedgerError(
                    f"{path}: detector.{key} does not compile: {e}"
                ) from e
    if kind in ("regex", "source"):
        if not detector.get("pattern"):
            raise LedgerError(f"{path}: a {kind} detector needs a pattern")
    elif kind == "doctree":
        if not detector.get("function"):
            raise LedgerError(f"{path}: a doctree detector needs a function name")
    elif kind == "build-warning":
        if not (detector.get("warning_type") or detector.get("message_pattern")):
            raise LedgerError(
                f"{path}: a build-warning detector needs warning_type or message_pattern"
            )
        if not detector.get("example_warning"):
            raise LedgerError(f"{path}: a build-warning rule needs an example_warning")
    if kind in PARSE_KINDS and not path.with_suffix(".py").exists():
        raise LedgerError(f"{path}: a {kind} rule needs a sibling .py fixture")


def _validate_fixture(rule: "Rule") -> None:
    """A parse-level fixture must carry at least one ``ruleid`` and one ``ok`` tag for its rule."""
    cases = [c for c in iter_fixture_cases(rule.fixture_path) if rule.id in c.rule_ids]
    if not any(c.expect_hit for c in cases):
        raise LedgerError(f"{rule.fixture_path}: no '# ruleid: {rule.id}' specimen")
    if not any(not c.expect_hit for c in cases):
        raise LedgerError(f"{rule.fixture_path}: no '# ok: {rule.id}' specimen")


def load_rule(path: Path) -> Rule:
    """Load and validate one rule file."""
    path = Path(path)
    data = _load_yaml(path)
    _validate_rule_data(data, path)
    known = {f for f in Rule.__dataclass_fields__ if f != "path"}
    kwargs = {k: v for k, v in data.items() if k in known}
    rule = Rule(path=path, **kwargs)
    if rule.kind == "doctree":
        from epythet.validation.detectors import DETECTORS

        if rule.detector["function"] not in DETECTORS:
            raise LedgerError(
                f"{path}: unknown doctree detector {rule.detector['function']!r}; "
                f"known: {sorted(DETECTORS)}"
            )
    if rule.kind in PARSE_KINDS:
        _validate_fixture(rule)
    return rule


def iter_rule_files(rules_dir: Path) -> Iterator[Path]:
    """Every ``*.yaml`` under ``rules_dir``, in a stable order."""
    return iter(sorted(Path(rules_dir).rglob("*.yaml")))


@dataclass
class Ledger:
    """The loaded rule catalog: bundled rules plus any overlay, keyed by id."""

    rules: dict[str, Rule] = field(default_factory=dict)
    sources: list[Path] = field(default_factory=list)

    def __iter__(self) -> Iterator[Rule]:
        return iter(self.rules.values())

    def __len__(self) -> int:
        return len(self.rules)

    def __getitem__(self, rule_id: str) -> Rule:
        return self.rules[rule_id]

    def of_kind(self, *kinds: str, include_proposed: bool = False) -> list[Rule]:
        """Rules whose detector kind is one of ``kinds``, in id order.

        Proposed rules (``status: {proposed: ...}``) are left out unless asked
        for: a proposal from level 3 must not gate anyone until a maintainer
        promotes it.
        """
        return [
            r
            for r in self
            if r.kind in kinds and (include_proposed or not r.is_proposed)
        ]

    def add_dir(self, rules_dir: Path, *, allow_override: bool = False) -> None:
        """Load every rule under ``rules_dir``; duplicates are an error unless overriding."""
        rules_dir = Path(rules_dir)
        if not rules_dir.is_dir():
            raise LedgerError(f"ledger directory not found: {rules_dir}")
        for path in iter_rule_files(rules_dir):
            rule = load_rule(path)
            if rule.id in self.rules and not allow_override:
                raise LedgerError(
                    f"duplicate rule id {rule.id}: {self.rules[rule.id].path} and {path}"
                )
            self.rules[rule.id] = rule
        self.sources.append(rules_dir)
        self.check_build_examples()

    def check_build_examples(self) -> None:
        """Every build-warning rule's ``example_warning`` must classify to that rule."""
        from epythet.validation.build import classify_warning, parse_warning_line

        for rule in self.of_kind("build-warning", include_proposed=True):
            warning = parse_warning_line(rule.detector["example_warning"])
            if warning is None:
                raise LedgerError(f"{rule.path}: example_warning is not a warning line")
            winner = classify_warning(warning, self)
            if winner is None or winner.id != rule.id:
                raise LedgerError(
                    f"{rule.path}: example_warning classifies to "
                    f"{winner.id if winner else 'nothing'}, not {rule.id}"
                )


def load_ledger(ledger: Ledger | str | os.PathLike | None = None) -> Ledger:
    """Resolve the ``ledger=`` seam to a :class:`Ledger`.

    ``None`` loads the bundled rules; a path loads the bundled rules and then
    overlays the directory (same id overrides); a :class:`Ledger` is returned
    as is.
    """
    if isinstance(ledger, Ledger):
        return ledger
    loaded = Ledger()
    loaded.add_dir(BUNDLED_RULES_DIR)
    if ledger is not None:
        loaded.add_dir(Path(ledger), allow_override=True)
    return loaded


# --------------------------------------------------------------------------
# Fixtures: the sibling .py file is the regression test for a rule
# --------------------------------------------------------------------------


@dataclass
class FixtureCase:
    """One specimen function in a fixture: its docstring and what the tag promises."""

    name: str
    line: int
    expect_hit: bool
    rule_ids: tuple[str, ...]
    docstring: Any  # epythet.validation.docstrings.Docstring


def iter_fixture_cases(fixture_path: Path) -> Iterator[FixtureCase]:
    """Yield the tagged specimens of a fixture file.

    A specimen is a ``def`` (or ``class``) whose header line carries a
    ``# ruleid: DR001`` (must fire) or ``# ok: DR001`` (must not fire) comment,
    Semgrep style. Several ids may be listed, comma-separated.
    """
    from epythet.validation.docstrings import iter_file_docstrings

    lines = Path(fixture_path).read_text(encoding="utf-8").splitlines()
    for doc in iter_file_docstrings(Path(fixture_path)):
        if doc.kind == "module":
            continue
        header = lines[doc.def_line - 1] if doc.def_line - 1 < len(lines) else ""
        tag = FIXTURE_TAG_RE.search(header)
        if tag is None:
            continue
        ids = tuple(s.strip() for s in tag.group(2).split(","))
        yield FixtureCase(
            name=doc.qualname,
            line=doc.def_line,
            expect_hit=tag.group(1) == "ruleid",
            rule_ids=ids,
            docstring=doc,
        )


# --------------------------------------------------------------------------
# Observations: append-only JSONL outside the repo
# --------------------------------------------------------------------------


def user_data_dir() -> Path:
    """``$EPYTHET_DATA_DIR``, else ``$XDG_DATA_HOME/epythet``, else ``~/.local/share/epythet``.

    Deliberately XDG-style on every platform (not ``platformdirs``'s macOS
    ``Application Support``): it matches where the rest of epythet's local
    data already lives, and it is what the decision record names.
    """
    override = os.environ.get("EPYTHET_DATA_DIR")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "epythet"


def observations_path() -> Path:
    """Where observations are appended: ``<user data dir>/ledger/observations.jsonl``."""
    return user_data_dir() / "ledger" / "observations.jsonl"


def observation_record(
    finding: Finding, *, package: str, package_version: str | None, run_id: str
) -> dict[str, Any]:
    """The JSONL line written for one finding."""
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "package": package,
        "package_version": package_version,
        "rule": finding.rule,
        "tool": finding.tool,
        "severity": finding.severity,
        "level": finding.level,
        "file": finding.file,
        "line": finding.line,
        "object": finding.object,
        "evidence": finding.evidence[:200],
    }


def append_observations(
    findings: Iterable[Finding],
    *,
    package: str,
    package_version: str | None = None,
    path: Path | None = None,
) -> int:
    """Append one JSONL line per finding; returns how many were written."""
    path = Path(path) if path is not None else observations_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    count = 0
    with path.open("a", encoding="utf-8") as fp:
        for finding in findings:
            record = observation_record(
                finding, package=package, package_version=package_version, run_id=run_id
            )
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def occurrence_counts(path: Path | None = None) -> Counter:
    """Occurrences per rule id over the whole observations file (empty if absent).

    This is the derived view that replaces an ``occurrences`` field in the rule
    files; a malformed line is skipped rather than failing the run.
    """
    path = Path(path) if path is not None else observations_path()
    counts: Counter = Counter()
    if not path.exists():
        return counts
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                counts[json.loads(line)["rule"]] += 1
            except (ValueError, KeyError, TypeError):
                continue
    return counts
