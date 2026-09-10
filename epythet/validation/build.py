"""Level 1: run the documentation build and turn its warning stream into findings.

This is the ``backend=`` seam of ``epythet validate``. Levels 0 and 0.5 read
Python source and docutils doctrees and are backend-independent by
construction; only this level (and level 2, owned by WP3) touches Sphinx. A
future MkDocs backend implements the same two methods, :meth:`SphinxBackend.versions`
and :meth:`SphinxBackend.build_warnings`, and inherits the whole ledger.

Two Sphinx facts shape the invocation. Since Sphinx 8.1 ``-W`` runs the whole
build and exits 1 if any warning occurred, so ``--keep-going`` is redundant
and not passed. Since Sphinx 8.0 ``show_warning_types`` defaults on, which
suffixes every warning with ``[docutils]``-style types; that suffix is what
the ledger's ``build-warning`` rules match on, because Sphinx still has no
structured warning output.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from epythet.validation.ledger import Ledger, Rule
from epythet.validation.model import Finding

BUILD_LEVEL = 1

#: ``path:docstring of obj:3: WARNING: message [type]`` and the simpler
#: ``path:12: WARNING: message [type]`` and ``WARNING: message`` shapes.
WARNING_LINE_RE = re.compile(
    r"^(?:(?P<loc>.*?):\s*)?(?P<sev>WARNING|ERROR|SEVERE|CRITICAL): (?P<msg>.*?)"
    r"(?: \[(?P<type>[\w.\-]+)\])?\s*$"
)
DOCSTRING_LOC_RE = re.compile(
    r"^(?P<file>.*?):docstring of (?P<obj>[\w.]+)(?::(?P<line>\d+))?$"
)
FILE_LINE_RE = re.compile(r"^(?P<file>.*?)(?::(?P<line>\d+))?$")


@dataclass
class BuildWarning:
    """One parsed line of the Sphinx warning stream."""

    severity: str
    message: str
    type: str | None = None
    file: str | None = None
    line: int | None = None
    object: str | None = None
    raw: str = ""


def parse_warning_line(
    line: str, *, project_dir: Path | None = None
) -> BuildWarning | None:
    """Parse one warning line; ``None`` when the line is not a warning.

    >>> w = parse_warning_line("/p/dol/base.py:docstring of dol.base.Store:7: WARNING: Inline emphasis start-string without end-string. [docutils]")
    >>> (w.file, w.object, w.line, w.type, w.severity)
    ('/p/dol/base.py', 'dol.base.Store', 7, 'docutils', 'warning')
    >>> parse_warning_line("reading sources... [ 10%] index") is None
    True
    """
    match = WARNING_LINE_RE.match(line.strip())
    if match is None:
        return None
    warning = BuildWarning(
        severity="error" if match["sev"] != "WARNING" else "warning",
        message=match["msg"].strip(),
        type=match["type"],
        raw=line.strip(),
    )
    loc = match["loc"]
    if loc:
        doc = DOCSTRING_LOC_RE.match(loc)
        if doc:
            warning.file, warning.object = doc["file"], doc["obj"]
            warning.line = int(doc["line"]) if doc["line"] else None
        else:
            fl = FILE_LINE_RE.match(loc)
            if fl:
                warning.file = fl["file"] or None
                warning.line = int(fl["line"]) if fl["line"] else None
    if warning.file and project_dir is not None:
        try:
            warning.file = (
                Path(warning.file)
                .resolve()
                .relative_to(Path(project_dir).resolve())
                .as_posix()
            )
        except ValueError:
            pass
    return warning


def parse_warning_stream(
    text: str, *, project_dir: Path | None = None
) -> Iterator[BuildWarning]:
    """Every warning in a ``-w`` warnings file or a build log."""
    for line in text.splitlines():
        warning = parse_warning_line(line, project_dir=project_dir)
        if warning is not None:
            yield warning


def _rule_matches(rule: Rule, warning: BuildWarning) -> bool:
    detector = rule.detector
    wanted_type = detector.get("warning_type")
    if wanted_type is not None:
        actual = warning.type or ""
        if not fnmatch.fnmatchcase(actual, wanted_type):
            return False
    message_pattern = detector.get("message_pattern")
    if message_pattern is not None and not re.search(message_pattern, warning.message):
        return False
    return True


def _build_rules_in_priority(ledger: Ledger) -> list[Rule]:
    """Most specific first: message-pattern rules, then typed, then wildcard."""

    def specificity(rule: Rule) -> tuple[int, str]:
        detector = rule.detector
        if detector.get("message_pattern"):
            return (0, rule.id)
        if detector.get("warning_type") not in (None, "*"):
            return (1, rule.id)
        return (2, rule.id)

    return sorted(ledger.of_kind("build-warning"), key=specificity)


def classify_warning(warning: BuildWarning, ledger: Ledger) -> Rule | None:
    """The first build-warning rule that matches, most specific first."""
    for rule in _build_rules_in_priority(ledger):
        if _rule_matches(rule, warning):
            return rule
    return None


def warnings_to_findings(
    warnings: Iterable[BuildWarning], ledger: Ledger
) -> list[Finding]:
    """Map each warning to a ledger finding (unclassified warnings keep their type as the rule)."""
    findings = []
    for warning in warnings:
        rule = classify_warning(warning, ledger)
        evidence = warning.message
        if rule is None:
            findings.append(
                Finding(
                    rule=f"sphinx:{warning.type or 'unknown'}",
                    severity=warning.severity,
                    level=BUILD_LEVEL,
                    message=warning.message,
                    file=warning.file,
                    line=warning.line,
                    object=warning.object,
                    detector="build-warning",
                    evidence=warning.raw,
                    tool="sphinx",
                )
            )
            continue
        findings.append(
            rule.finding(
                level=BUILD_LEVEL,
                evidence=evidence,
                file=warning.file,
                line=warning.line,
                object=warning.object,
            )
        )
    return findings


@dataclass
class BuildResult:
    """What one build produced: exit status, parsed warnings, and the raw log."""

    returncode: int
    warnings: list[BuildWarning] = field(default_factory=list)
    log: str = ""
    outdir: Path | None = None
    command: list[str] = field(default_factory=list)


def default_sphinx_build() -> list[str] | None:
    """``python -m sphinx`` when Sphinx is importable here, else ``sphinx-build`` on PATH."""
    if importlib.util.find_spec("sphinx") is not None:
        return [sys.executable, "-m", "sphinx"]
    exe = shutil.which("sphinx-build")
    return [exe] if exe else None


@dataclass
class SphinxBackend:
    """The default (and only shipped) backend: ``sphinx-build -b html -W``.

    ``docsrc`` defaults to ``<project>/docsrc``, the directory epythet
    generates. ``outdir`` defaults to a temporary directory so validation
    never litters the repository.
    """

    sphinx_build: Sequence[str] | None = None
    docsrc: str | Path | None = None
    outdir: str | Path | None = None
    builder: str = "html"
    nitpicky: bool = False
    name: str = "sphinx"

    def versions(self) -> dict[str, str | None]:
        """``{"sphinx": ..., "docutils": ...}`` as importable here (``None`` if not)."""
        versions: dict[str, str | None] = {}
        for module in ("sphinx", "docutils"):
            try:
                versions[module] = __import__(module).__version__
            except ImportError:
                versions[module] = None
        return versions

    def resolve_docsrc(self, project_dir: Path) -> Path | None:
        """The Sphinx source directory, or ``None`` when there is none to build."""
        docsrc = Path(self.docsrc) if self.docsrc else Path(project_dir) / "docsrc"
        return docsrc if (docsrc / "conf.py").exists() else None

    def build_warnings(self, project_dir: Path) -> BuildResult:
        """Run the build and parse its warnings; never raises on a failed build."""
        project_dir = Path(project_dir)
        command = (
            list(self.sphinx_build) if self.sphinx_build else default_sphinx_build()
        )
        if command is None:
            return BuildResult(returncode=127, log="sphinx-build not found", command=[])
        docsrc = self.resolve_docsrc(project_dir)
        if docsrc is None:
            return BuildResult(
                returncode=2, log="no docsrc/conf.py to build", command=command
            )
        outdir = (
            Path(self.outdir)
            if self.outdir
            else Path(tempfile.mkdtemp(prefix="epythet-validate-"))
        )
        warnings_file = outdir / "warnings.txt"
        args = [*command, "-b", self.builder, "-W", "-q", "-w", str(warnings_file)]
        if self.nitpicky:
            args.append("-n")
        args += [
            "-d",
            str(outdir / ".doctrees"),
            str(docsrc),
            str(outdir / self.builder),
        ]
        proc = subprocess.run(args, cwd=project_dir, capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        stream = (
            warnings_file.read_text(encoding="utf-8", errors="replace")
            if warnings_file.exists()
            else log
        )
        return BuildResult(
            returncode=proc.returncode,
            warnings=list(parse_warning_stream(stream, project_dir=project_dir)),
            log=log,
            outdir=outdir,
            command=args,
        )


def run_build_level(
    project_dir: Path, ledger: Ledger, *, backend: SphinxBackend
) -> tuple[list[Finding], list[str]]:
    """Level 1: build, classify warnings, and report a failed build as a finding."""
    result = backend.build_warnings(project_dir)
    notes: list[str] = []
    findings = warnings_to_findings(result.warnings, ledger)
    if result.returncode != 0 and not findings:
        tail = result.log.strip().splitlines()[-5:]
        findings.append(
            Finding(
                rule="BUILD",
                severity="error",
                level=BUILD_LEVEL,
                message=f"documentation build failed (exit {result.returncode})",
                detector="build-warning",
                evidence=" | ".join(tail)[:400],
                tool=backend.name,
            )
        )
    if result.outdir is not None:
        notes.append(f"build output: {result.outdir}")
    return findings, notes
