"""Level 2: read the *rendered* output (XML, HTML, text) and report what the build hid.

A strict build is silent about most of what a reader sees wrong (research
§2.2): an object listed with no description, a cross-reference that rendered
as plain code, a link to an anchor Sphinx pruned, an image that is not in the
built tree. This level renders three builders through the ``backend=`` seam
(:meth:`~epythet.validation.build.SphinxBackend.render`) and reads each for
what it shows best (research §5.4):

- ``xml`` for structure: empty object descriptions and unresolved
  cross-references (a ``literal`` with class ``xref`` that no ``reference``
  wraps, detectable without ``-n``);
- ``html`` for links and assets: dangling ``#idN`` anchors and ``<img src>``
  that resolve to nothing in the built tree;
- ``text`` for snapshots: a 4 KB page that keeps every text-leak artifact
  verbatim and none of the theme, diffed against ``docsrc/_snapshots/text``
  when ``snapshot=True``.

Only the standard library parses the output (``xml.etree`` and ``html.parser``):
the pages are Sphinx's own, not untrusted input. Snapshots are opt-in and
off by default; ``update_snapshots=True`` re-baselines.

>>> from epythet.validation.rendered import dangling_anchors
>>> dangling_anchors('<a id="x"></a><a href="#x">ok</a><a href="#id7">gone</a>')
['#id7']
"""

from __future__ import annotations

import difflib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Iterator
from urllib.parse import urlsplit

from epythet.validation.ledger import Ledger, Rule
from epythet.validation.model import Finding

RENDER_LEVEL = 2
#: Where ``-b text`` snapshots live, relative to the Sphinx source directory.
SNAPSHOT_DIRNAME = "_snapshots/text"
#: Rule ids this level reports under (all bundled; see ``epythet/ledger/rules``).
EMPTY_DESCRIPTION = "DR026"
DANGLING_ANCHOR = "DR027"
SNAPSHOT_DRIFT = "DR035"
UNRESOLVED_XREF = "DR023"
MISSING_IMAGE = "DR024"
#: Paragraphs autodoc writes itself; a class with no docstring still has one.
_GENERATED_PARAGRAPH_PREFIXES = ("Bases:",)
_DIFF_LINES_IN_EVIDENCE = 12


@dataclass
class RenderHit:
    """One thing a render detector found on one page."""

    page: str
    evidence: str
    object: str | None = None


RenderDetector = Callable[[Path, Path], list[RenderHit]]
#: Detector name (as in a rule's ``detector.function``) -> function.
RENDER_DETECTORS: dict[str, RenderDetector] = {}


def render_detector(name: str):
    """Register a level-2 detector; the ledger loader validates ``html`` rules against it."""

    def register(fn: RenderDetector) -> RenderDetector:
        RENDER_DETECTORS[name] = fn
        return fn

    return register


# --------------------------------------------------------------------------
# XML: structure
# --------------------------------------------------------------------------


def _pages(outdir: Path, suffix: str) -> Iterator[tuple[str, Path]]:
    """``(docname, path)`` for every page of one builder, in a stable order."""
    outdir = Path(outdir)
    for path in sorted(outdir.rglob(f"*{suffix}")):
        if any(part.startswith(("_static", "_sources", "_modules")) for part in path.relative_to(outdir).parts):
            continue
        yield path.relative_to(outdir).with_suffix("").as_posix(), path


def _parents(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def _ancestors(node: ET.Element, parents: dict) -> Iterator[ET.Element]:
    while node in parents:
        node = parents[node]
        yield node


def _signature_name(signature: ET.Element | None) -> str | None:
    """``module.fullname`` of a ``desc_signature`` node."""
    if signature is None:
        return None
    module = signature.get("module") or ""
    fullname = signature.get("fullname") or ""
    return ".".join(part for part in (module, fullname) if part) or None


def _object_of(node: ET.Element, parents: dict) -> str | None:
    """The dotted name of the innermost ``desc`` an XML node sits in."""
    for ancestor in _ancestors(node, parents):
        if ancestor.tag == "desc":
            return _signature_name(ancestor.find("desc_signature"))
    return None


def _text(node: ET.Element) -> str:
    return " ".join("".join(node.itertext()).split())


def _is_generated(paragraph: ET.Element) -> bool:
    return _text(paragraph).startswith(_GENERATED_PARAGRAPH_PREFIXES)


def empty_descriptions_in(root: ET.Element) -> list[RenderHit]:
    """Objects the page lists or describes with no text at all.

    Two shapes: a ``desc`` whose ``desc_content`` holds nothing but generated
    paragraphs, index entries and nested objects; and an autosummary row
    whose summary cell is an empty paragraph (autodoc leaves undocumented
    members out of the page entirely, so the table row is all a reader sees).
    """
    parents = _parents(root)
    hits: list[RenderHit] = []
    for desc in root.iter("desc"):
        content = desc.find("desc_content")
        if content is None:
            continue
        own = [
            child
            for child in content
            if child.tag not in ("index", "desc")
            and not (child.tag == "paragraph" and _is_generated(child))
        ]
        if own:
            continue
        name = _signature_name(desc.find("desc_signature"))
        hits.append(RenderHit(page="", evidence=name or _text(desc)[:80], object=name))
    for table in root.iter("autosummary_table"):
        for row in table.iter("row"):
            entries = list(row.iter("entry"))
            if len(entries) < 2:
                continue
            summary = _text(entries[1])
            if summary:
                continue
            literal = entries[0].find(".//literal")
            name = _text(literal) if literal is not None else _text(entries[0])
            hits.append(RenderHit(page="", evidence=name, object=name))
    return hits


def unresolved_xrefs_in(root: ET.Element) -> list[RenderHit]:
    """Cross-references that rendered as plain code: an ``xref`` literal no ``reference`` wraps.

    Autosummary rows are left out: an unwrapped name there means an
    undocumented object (reported by :func:`empty_descriptions_in`), not a
    bad target.
    """
    parents = _parents(root)
    hits: list[RenderHit] = []
    for literal in root.iter("literal"):
        classes = (literal.get("classes") or "").split()
        if "xref" not in classes:
            continue
        chain = list(_ancestors(literal, parents))
        if any(a.tag in ("reference", "autosummary_table") for a in chain):
            continue
        if any(a.tag == "title" for a in chain):
            continue  # section titles are not links
        hits.append(
            RenderHit(page="", evidence=_text(literal), object=_object_of(literal, parents))
        )
    return hits


def _scan_xml(outdir: Path, extract) -> list[RenderHit]:
    hits: list[RenderHit] = []
    for docname, path in _pages(outdir, ".xml"):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for hit in extract(root):
            hit.page = docname
            hits.append(hit)
    return hits


@render_detector("empty_descriptions")
def empty_descriptions(outdirs: dict[str, Path], _docsrc: Path) -> list[RenderHit]:
    """Level-2 detector over the ``xml`` output (DR026)."""
    if "xml" not in outdirs:
        return []
    return _scan_xml(outdirs["xml"], empty_descriptions_in)


@render_detector("unresolved_xrefs")
def unresolved_xrefs(outdirs: dict[str, Path], _docsrc: Path) -> list[RenderHit]:
    """Level-2 detector over the ``xml`` output (DR023 at level 2)."""
    if "xml" not in outdirs:
        return []
    return _scan_xml(outdirs["xml"], unresolved_xrefs_in)


# --------------------------------------------------------------------------
# HTML: links and assets
# --------------------------------------------------------------------------


class _LinkCollector(HTMLParser):
    """Collects ``id`` values, fragment ``href`` targets and ``<img src>`` values."""

    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.fragment_hrefs: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag == "a" and attributes.get("name"):
            self.ids.add(attributes["name"])
        href = attributes.get("href") if tag == "a" else None
        if href and href.startswith("#") and len(href) > 1:
            self.fragment_hrefs.append(href)
        if tag == "img" and attributes.get("src"):
            self.images.append(attributes["src"])


def _collect(html: str) -> _LinkCollector:
    collector = _LinkCollector()
    collector.feed(html)
    return collector


def dangling_anchors(html: str) -> list[str]:
    """Fragment links on a page whose target id does not exist on that page.

    This is the research's exact detector (§6.3): every ``problematic`` span
    Sphinx emits links to a ``#idN`` system message it then prunes, and a
    hand-written ``:ref:`` to a missing label ends the same way.
    """
    collector = _collect(html)
    return [
        href
        for href in collector.fragment_hrefs
        if href[1:] not in collector.ids
    ]


def _is_local(src: str) -> bool:
    parts = urlsplit(src)
    return not parts.scheme and not parts.netloc and not src.startswith("data:")


def missing_images(html: str, *, page_dir: Path) -> list[str]:
    """``<img src>`` values that resolve to no file next to the page."""
    return [
        src
        for src in _collect(html).images
        if _is_local(src) and not (page_dir / urlsplit(src).path).exists()
    ]


def _scan_html(outdir: Path, extract) -> list[RenderHit]:
    hits: list[RenderHit] = []
    for docname, path in _pages(outdir, ".html"):
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits += [RenderHit(page=docname, evidence=e) for e in extract(html, path.parent)]
    return hits


@render_detector("dangling_anchors")
def dangling_anchors_detector(outdirs: dict[str, Path], _docsrc: Path) -> list[RenderHit]:
    """Level-2 detector over the ``html`` output (DR027)."""
    if "html" not in outdirs:
        return []
    return _scan_html(outdirs["html"], lambda html, _dir: dangling_anchors(html))


@render_detector("missing_images")
def missing_images_detector(outdirs: dict[str, Path], _docsrc: Path) -> list[RenderHit]:
    """Level-2 detector over the ``html`` output (DR024 at level 2)."""
    if "html" not in outdirs:
        return []
    return _scan_html(
        outdirs["html"], lambda html, page_dir: missing_images(html, page_dir=page_dir)
    )


# --------------------------------------------------------------------------
# Text: snapshots
# --------------------------------------------------------------------------


@dataclass
class SnapshotDiff:
    """How the ``-b text`` render compares with the stored snapshots."""

    changed: dict[str, str] = field(default_factory=dict)  # docname -> unified diff
    added: list[str] = field(default_factory=list)  # rendered, no snapshot yet
    removed: list[str] = field(default_factory=list)  # snapshot, no longer rendered
    compared: int = 0

    @property
    def clean(self) -> bool:
        return not (self.changed or self.added or self.removed)


def _unified_diff(old: str, new: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"snapshot/{name}.txt",
            tofile=f"rendered/{name}.txt",
        )
    )


def compare_snapshots(text_dir: Path, snapshot_dir: Path) -> SnapshotDiff:
    """Diff every rendered text page against its stored snapshot."""
    rendered = dict(_pages(Path(text_dir), ".txt"))
    stored = dict(_pages(Path(snapshot_dir), ".txt")) if Path(snapshot_dir).is_dir() else {}
    diff = SnapshotDiff()
    for docname, path in rendered.items():
        if docname not in stored:
            diff.added.append(docname)
            continue
        diff.compared += 1
        old = stored[docname].read_text(encoding="utf-8", errors="replace")
        new = path.read_text(encoding="utf-8", errors="replace")
        if old != new:
            diff.changed[docname] = _unified_diff(old, new, docname)
    diff.removed = sorted(set(stored) - set(rendered))
    return diff


def update_snapshots(text_dir: Path, snapshot_dir: Path) -> int:
    """Replace the stored snapshots with the current render; returns pages written."""
    snapshot_dir = Path(snapshot_dir)
    if snapshot_dir.is_dir():
        for stale in snapshot_dir.rglob("*.txt"):
            stale.unlink()
    count = 0
    for docname, path in _pages(Path(text_dir), ".txt"):
        target = snapshot_dir / f"{docname}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        count += 1
    return count


@render_detector("text_snapshots")
def text_snapshots_detector(_outdirs: dict[str, Path], _docsrc: Path) -> list[RenderHit]:
    """DR035's detector is the snapshot diff, driven by ``snapshot=``; nothing to scan here."""
    return []


def changed_pages(diff: SnapshotDiff) -> list[str]:
    """Pages level 3 should review: changed or new relative to the snapshot."""
    return sorted([*diff.changed, *diff.added])


# --------------------------------------------------------------------------
# The level
# --------------------------------------------------------------------------


@dataclass
class RenderArtifacts:
    """What level 2 leaves behind for level 3: output dirs and the snapshot diff."""

    outdirs: dict[str, Path] = field(default_factory=dict)
    docsrc: Path | None = None
    snapshot: SnapshotDiff | None = None


def _rule_or_fallback(ledger: Ledger, rule_id: str, *, severity: str, title: str) -> Rule:
    """The ledger's rule, or a minimal stand-in when an overlay removed it."""
    try:
        return ledger[rule_id]
    except KeyError:
        return Rule(
            id=rule_id,
            title=title,
            namespace="rendering",
            severity=severity,
            precision="high",
            detector={"kind": "html"},
            message=title + ": {match}",
        )


def _finding(rule: Rule, hit: RenderHit, *, message: str | None = None) -> Finding:
    finding = rule.finding(
        level=RENDER_LEVEL,
        evidence=hit.evidence,
        file=hit.page,
        object=hit.object,
        message=message,
    )
    finding.detector = "render"
    return finding


def render_findings(
    outdirs: dict[str, Path], ledger: Ledger, *, docsrc: Path
) -> list[Finding]:
    """Run every ``html``-kind rule of the ledger over the rendered output."""
    findings: list[Finding] = []
    for rule in ledger.of_kind("html"):
        function = rule.detector.get("function")
        detector = RENDER_DETECTORS.get(function or "")
        if detector is None:
            continue
        for hit in detector(outdirs, docsrc):
            findings.append(_finding(rule, hit))
    return findings


def snapshot_findings(diff: SnapshotDiff, ledger: Ledger) -> list[Finding]:
    """One DR035 finding per changed page, plus info findings for new and removed pages."""
    rule = _rule_or_fallback(
        ledger, SNAPSHOT_DRIFT, severity="error", title="Rendered text drifted from its snapshot"
    )
    findings: list[Finding] = []
    for docname, text in diff.changed.items():
        lines = text.splitlines()
        evidence = "\n".join(lines[: _DIFF_LINES_IN_EVIDENCE])
        if len(lines) > _DIFF_LINES_IN_EVIDENCE:
            evidence += f"\n… {len(lines) - _DIFF_LINES_IN_EVIDENCE} more diff lines"
        findings.append(
            _finding(rule, RenderHit(page=docname, evidence=evidence), message=f"{docname} changed ({len(lines)} diff lines)")
        )
    for docname in diff.added:
        finding = _finding(rule, RenderHit(page=docname, evidence="new page"), message=f"{docname} has no snapshot yet")
        finding.severity = "info"
        findings.append(finding)
    for docname in diff.removed:
        finding = _finding(rule, RenderHit(page=docname, evidence="page gone"), message=f"{docname} is snapshotted but no longer rendered")
        finding.severity = "warning"
        findings.append(finding)
    return findings


def run_render_level(
    project_dir: Path,
    ledger: Ledger,
    *,
    backend,
    outdir: Path,
    snapshot: bool = False,
    update: bool = False,
    snapshot_dir: Path | None = None,
) -> tuple[list[Finding], list[str], RenderArtifacts]:
    """Level 2: render html, text and xml into ``outdir`` and read them.

    Returns ``(findings, notes, artifacts)``; the artifacts hand level 3 the
    output directories and the snapshot diff so it never builds again.
    """
    from epythet.validation.build import NO_DOCSRC

    notes: list[str] = []
    artifacts = RenderArtifacts()
    docsrc = backend.resolve_docsrc(Path(project_dir)) if hasattr(backend, "resolve_docsrc") else None
    result = backend.render(Path(project_dir), outdir=Path(outdir))
    if all(code == NO_DOCSRC for code in result.returncodes.values()):
        return (
            [
                Finding(
                    rule="NO_DOCSRC",
                    severity="warning",
                    level=RENDER_LEVEL,
                    message="no docsrc/conf.py to render; level 2 checked nothing (run epythet quickstart, or pass --docsrc)",
                    detector="render",
                    tool=getattr(backend, "name", "backend"),
                )
            ],
            notes,
            artifacts,
        )
    findings: list[Finding] = []
    failed = {b: c for b, c in result.returncodes.items() if b not in result.outdirs}
    for builder, code in failed.items():
        findings.append(
            Finding(
                rule="BUILD",
                severity="error",
                level=RENDER_LEVEL,
                message=f"-b {builder} failed (exit {code})",
                detector="render",
                evidence=result.log.strip().splitlines()[-1][:300] if result.log.strip() else "",
                tool=getattr(backend, "name", "backend"),
            )
        )
    artifacts.outdirs = dict(result.outdirs)
    artifacts.docsrc = docsrc
    findings += render_findings(result.outdirs, ledger, docsrc=docsrc or Path(project_dir))
    if "text" in result.outdirs and (snapshot or update):
        snapshot_dir = Path(snapshot_dir) if snapshot_dir else (docsrc or Path(project_dir) / "docsrc") / SNAPSHOT_DIRNAME
        if update:
            written = update_snapshots(result.outdirs["text"], snapshot_dir)
            notes.append(f"{written} text snapshots written to {snapshot_dir}")
            artifacts.snapshot = SnapshotDiff(compared=written)
        else:
            diff = compare_snapshots(result.outdirs["text"], snapshot_dir)
            artifacts.snapshot = diff
            if not snapshot_dir.is_dir():
                notes.append(f"no snapshots at {snapshot_dir}; run with --update-snapshots to create them")
            else:
                findings += snapshot_findings(diff, ledger)
                notes.append(f"{diff.compared} text snapshots compared against {snapshot_dir}")
    return findings, notes, artifacts
