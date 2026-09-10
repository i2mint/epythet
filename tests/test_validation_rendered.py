"""Level 2: rendered-output detectors on canned XML/HTML, snapshots, the fake-backend level, exit 13."""

import shutil
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from epythet.validation import EXIT_FOR_LEVEL, load_ledger, validate
from epythet.validation.build import NO_DOCSRC, RenderResult, SphinxBackend
from epythet.validation.rendered import (
    RenderArtifacts,
    compare_snapshots,
    dangling_anchors,
    empty_descriptions_in,
    missing_images,
    run_render_level,
    unresolved_xrefs_in,
    update_snapshots,
)

XML_PAGE = """\
<document source="/p/docsrc/_autosummary/pkg.mod.rst">
<section ids="module-pkg.mod">
<title>pkg.mod</title>
<paragraph>See <literal classes="xref py py-class">pkg.Nowhere</literal> and
<reference internal="1" refuri="pkg#pkg.f"><literal classes="xref py py-func">pkg.f()</literal></reference>.</paragraph>
<autosummary_table><table><tgroup cols="2"><tbody>
<row><entry><paragraph><reference internal="1" refid="pkg.mod.documented"><literal classes="xref py py-obj">documented</literal></reference>(x)</paragraph></entry><entry><paragraph>Return x.</paragraph></entry></row>
<row><entry><paragraph><literal classes="xref py py-obj">undocumented</literal>(x)</paragraph></entry><entry><paragraph></paragraph></entry></row>
</tbody></tgroup></table></autosummary_table>
<desc desctype="class">
<desc_signature fullname="Klass" module="pkg.mod"><desc_name>Klass</desc_name></desc_signature>
<desc_content>
<paragraph>Bases: <reference internal="0"><literal classes="xref py py-class">object</literal></reference></paragraph>
<index entries="[]"/>
<desc desctype="method">
<desc_signature fullname="Klass.m" module="pkg.mod"><desc_name>m</desc_name></desc_signature>
<desc_content><paragraph>Doc.</paragraph></desc_content>
</desc>
</desc_content>
</desc>
<desc desctype="function">
<desc_signature fullname="documented" module="pkg.mod"><desc_name>documented</desc_name></desc_signature>
<desc_content><paragraph>Return x.</paragraph></desc_content>
</desc>
</section>
</document>
"""

HTML_PAGE = """\
<html><body>
<section id="module-pkg"><h1>pkg<a class="headerlink" href="#module-pkg">#</a></h1>
<p><span class="problematic" id="id2"><a href="#id1">*args</a></span></p>
<a href="#">top</a> <a href="#present">ok</a> <span id="present"></span>
<img src="_images/ok.png"><img src="missing.png"><img src="https://x.org/y.png"><img src="data:image/png;base64,AA==">
</section></body></html>
"""


def test_empty_descriptions_finds_undocumented_class_and_table_row():
    hits = empty_descriptions_in(ET.fromstring(XML_PAGE))
    assert [h.object for h in hits] == ["pkg.mod.Klass", "undocumented"]


def test_unresolved_xrefs_skip_wrapped_refs_titles_and_autosummary_rows():
    hits = unresolved_xrefs_in(ET.fromstring(XML_PAGE))
    assert [h.evidence for h in hits] == ["pkg.Nowhere"]
    assert hits[0].object is None  # page-level prose, not inside a desc


def test_dangling_anchors_are_fragment_links_without_a_target():
    assert dangling_anchors(HTML_PAGE) == ["#id1"]


def test_missing_images_resolve_against_the_page_dir(tmp_path):
    (tmp_path / "_images").mkdir()
    (tmp_path / "_images" / "ok.png").write_bytes(b"")
    assert missing_images(HTML_PAGE, page_dir=tmp_path) == ["missing.png"]


# --------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------


def _text_dir(root: Path, pages: dict[str, str]) -> Path:
    for name, text in pages.items():
        target = root / f"{name}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return root


def test_snapshots_update_then_compare(tmp_path):
    rendered = _text_dir(tmp_path / "text", {"index": "Hello\n", "_autosummary/pkg": "pkg\n***\n"})
    snapshots = tmp_path / "snap"
    assert update_snapshots(rendered, snapshots) == 2
    assert compare_snapshots(rendered, snapshots).clean
    (rendered / "index.txt").write_text("Hello there\n")
    (rendered / "new.txt").write_text("new page\n")
    (rendered / "_autosummary" / "pkg.txt").unlink()
    diff = compare_snapshots(rendered, snapshots)
    assert list(diff.changed) == ["index"]
    assert "-Hello" in diff.changed["index"] and "+Hello there" in diff.changed["index"]
    assert diff.added == ["new"] and diff.removed == ["_autosummary/pkg"]


# --------------------------------------------------------------------------
# The level, with a backend that renders nothing
# --------------------------------------------------------------------------


@dataclass
class CannedBackend:
    """A RenderBackend whose output is whatever the test wrote on disk."""

    pages: dict[str, dict[str, str]]  # builder -> {docname: content}
    name: str = "canned"
    returncodes: dict[str, int] = field(default_factory=dict)

    def versions(self):
        return {"sphinx": None, "docutils": None}

    def build_warnings(self, project_dir):
        from epythet.validation.build import BuildResult

        return BuildResult(returncode=0)

    def resolve_docsrc(self, project_dir):
        return Path(project_dir) / "docsrc"

    def render(self, project_dir, *, builders=("html", "text", "xml"), outdir):
        result = RenderResult()
        for builder in builders:
            code = self.returncodes.get(builder, 0)
            result.returncodes[builder] = code
            if code not in (0, 1):
                continue
            suffix = {"html": ".html", "text": ".txt", "xml": ".xml"}[builder]
            if builder == "html":
                image = Path(outdir) / "html" / "_autosummary" / "_images" / "ok.png"
                image.parent.mkdir(parents=True, exist_ok=True)
                image.write_bytes(b"")
            for docname, content in self.pages.get(builder, {}).items():
                target = Path(outdir) / builder / f"{docname}{suffix}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            result.outdirs[builder] = Path(outdir) / builder
        return result


@pytest.fixture
def canned():
    return CannedBackend(
        pages={
            "xml": {"_autosummary/pkg.mod": XML_PAGE},
            "html": {"_autosummary/pkg": HTML_PAGE},
            "text": {"index": "Hello\n"},
        }
    )


def test_render_level_reports_every_detector(tmp_path, canned):
    findings, notes, artifacts = run_render_level(
        tmp_path, load_ledger(), backend=canned, outdir=tmp_path / "out"
    )
    by_rule = {}
    for f in findings:
        by_rule.setdefault(f.rule, []).append(f)
    assert set(by_rule) == {"DR026", "DR027", "DR036", "DR037"}
    assert len(by_rule["DR026"]) == 2 and by_rule["DR026"][0].level == 2
    assert by_rule["DR027"][0].evidence == "#id1"
    assert by_rule["DR036"][0].evidence == "pkg.Nowhere"
    assert by_rule["DR037"][0].evidence == "missing.png"
    assert all(f.detector == "render" for f in findings)
    assert set(artifacts.outdirs) == {"html", "text", "xml"}


def test_render_level_snapshot_drift_is_dr035(tmp_path, canned):
    ledger = load_ledger()
    snapshots = tmp_path / "snap"
    _, notes, _ = run_render_level(
        tmp_path, ledger, backend=canned, outdir=tmp_path / "o1", update=True, snapshot_dir=snapshots
    )
    assert any("1 text snapshots written" in n for n in notes)
    canned.pages["text"]["index"] = "Hello there\n"
    findings, notes, artifacts = run_render_level(
        tmp_path, ledger, backend=canned, outdir=tmp_path / "o2", snapshot=True, snapshot_dir=snapshots
    )
    drift = [f for f in findings if f.rule == "DR035"]
    assert len(drift) == 1 and drift[0].severity == "error" and drift[0].file == "index"
    assert "+Hello there" in drift[0].evidence
    assert artifacts.snapshot is not None and list(artifacts.snapshot.changed) == ["index"]


def test_render_level_without_snapshots_only_notes(tmp_path, canned):
    findings, notes, _ = run_render_level(
        tmp_path, load_ledger(), backend=canned, outdir=tmp_path / "o", snapshot=True, snapshot_dir=tmp_path / "none"
    )
    assert not [f for f in findings if f.rule == "DR035"]
    assert any("no snapshots" in n for n in notes)


def test_render_level_failed_builder_is_a_build_finding(tmp_path, canned):
    canned.returncodes["xml"] = 2
    findings, _, artifacts = run_render_level(tmp_path, load_ledger(), backend=canned, outdir=tmp_path / "o")
    build = [f for f in findings if f.rule == "BUILD"]
    assert len(build) == 1 and "-b xml failed" in build[0].message
    assert "xml" not in artifacts.outdirs


def test_render_level_no_docsrc_is_non_gating(tmp_path):
    backend = CannedBackend(pages={}, returncodes={b: NO_DOCSRC for b in ("html", "text", "xml")})
    findings, _, _ = run_render_level(tmp_path, load_ledger(), backend=backend, outdir=tmp_path / "o")
    assert [f.rule for f in findings] == ["NO_DOCSRC"] and findings[0].severity == "warning"


def test_validate_tier_3_exit_code_is_13(make_project, canned, tmp_path):
    project = make_project("pkg", {"mod.py": '"""Mod."""\n\n\ndef f(x):\n    """Return x."""\n'})
    report = validate(
        project,
        level=3,
        backend=canned,
        observations_path=tmp_path / "obs.jsonl",
        linters=False,
    )
    assert report.levels_run == [0, 0.5, 1, 2]
    assert report.failing_levels("warning") == [2]
    assert report.exit_code() == EXIT_FOR_LEVEL[2] == 13  # DR037 (missing image) is an error
    assert {f.rule for f in report.findings if f.level == 2} == {"DR026", "DR027", "DR036", "DR037"}


# --------------------------------------------------------------------------
# A real render (Sphinx)
# --------------------------------------------------------------------------

sphinx_available = shutil.which("sphinx-build") is not None or __import__("importlib.util").util.find_spec("sphinx")


@pytest.mark.skipif(not sphinx_available, reason="needs sphinx")
def test_real_render_finds_the_planted_artifacts(make_project, tmp_path):
    from epythet.scaffold import make_docsrc

    project = make_project(
        "rpkg",
        {
            "mod.py": textwrap.dedent(
                '''
                """Module docs."""


                def documented(x):
                    """Return x."""
                    return x


                def undocumented(x):
                    return x
                '''
            )
        },
        init='"""Package.\n\nSee :class:`rpkg.mod.Nowhere`.\n\n.. image:: missing.png\n"""\nfrom rpkg.mod import documented, undocumented\n',
    )
    make_docsrc(project, verbose=False)
    report = validate(project, levels=[2], observations_path=tmp_path / "obs.jsonl", render_dir=tmp_path / "render")
    rules = {f.rule for f in report.findings}
    assert {"DR026", "DR036", "DR037"} <= rules, report.findings
    assert (tmp_path / "render" / "text").is_dir() and (tmp_path / "render" / "xml").is_dir()
