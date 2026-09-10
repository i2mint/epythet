"""Level 3: the review packet, reply validation and ingestion (exit 14), and ``ledger propose``."""

import json
from pathlib import Path

import pytest

from epythet.validation import EXIT_FOR_LEVEL, Report, load_ledger
from epythet.validation.model import Finding
from epythet.validation.propose import next_rule_id, propose
from epythet.validation.review import (
    PACKET_RULE,
    REPLY_SCHEMA_VERSION,
    ReplyError,
    load_reply,
    run_review_level,
    select_pages,
    write_packet,
)


@pytest.fixture
def outdirs(tmp_path):
    text = tmp_path / "text"
    for name, body in {"index": "Index.\n", "api": "API.\n", "_autosummary/pkg": "pkg\n", "_autosummary/pkg.mod": "mod\n"}.items():
        target = text / f"{name}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    return {"text": text}


def test_select_pages_modes():
    pages = ["index", "api", "_autosummary/pkg", "_autosummary/pkg.mod"]
    assert select_pages(pages, mode="all") == pages
    assert select_pages(pages, mode="sample", sample=3) == ["index", "_autosummary/pkg", "_autosummary/pkg.mod"]
    assert select_pages(pages, mode="changed", changed=["api", "gone"]) == ["api"]
    assert select_pages(pages, mode="changed", changed=None, sample=1) == ["index"]
    with pytest.raises(ValueError):
        select_pages(pages, mode="nope")


def test_packet_layout_and_manifest(outdirs, data_dir):
    packet = write_packet(package="pkg", package_version="1.0", outdirs=outdirs, ledger=load_ledger(), mode="all")
    assert packet.path.parent.parent == data_dir / "review"
    names = {p.name for p in packet.path.iterdir()}
    assert {"packet.json", "rubric.md", "schema.json", "INSTRUCTIONS.md", "pages"} <= names
    assert (packet.path / "pages" / "_autosummary" / "pkg.mod.txt").read_text() == "mod\n"
    manifest = json.loads((packet.path / "packet.json").read_text())
    assert manifest["pages"] == packet.pages and manifest["prompt_hash"] == packet.prompt_hash
    rubric = (packet.path / "rubric.md").read_text()
    assert "DR001: RST field list leaked into prose" in rubric and "| A. Summary |" in rubric
    assert json.loads((data_dir / "review" / "pkg" / "latest.json").read_text())["packet"] == str(packet.path)


def _reply(prompt_hash="0123456789abcdef", **overrides):
    reply = {
        "schema_version": REPLY_SCHEMA_VERSION,
        "model": "test-model",
        "prompt_hash": prompt_hash,
        "findings": [
            {"page": "index", "object": "pkg.f", "rule": "DR001", "severity": "warning", "message": "leaked", "evidence": ":param x:"},
            {"page": "api", "object": None, "rule": "proposed", "dimension": "A", "severity": "info", "message": "restates the name"},
        ],
        "proposed_rules": [
            {
                "title": "Placeholder description",
                "namespace": "semantics",
                "severity": "info",
                "precision": "medium",
                "detector": {"kind": "regex", "node": "paragraph", "pattern": r"\bthe thing\b"},
                "message": "placeholder: {match!r}",
                "fix": {"hint": "Say what it is."},
                "example_bad": "Do it.\n\nArgs:\n    x: the thing\n",
                "example_good": "Do it.\n\nArgs:\n    x: the number of retries\n",
            }
        ],
    }
    reply.update(overrides)
    return reply


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r.pop("model"), "missing required key 'model'"),
        (lambda r: r.__setitem__("schema_version", "9"), "must be '1'"),
        (lambda r: r["findings"][0].__setitem__("rule", "bogus"), "does not match"),
        (lambda r: r["findings"][0].__setitem__("severity", "fatal"), "must be one of"),
        (lambda r: r.__setitem__("extra", 1), "unknown key"),
        (lambda r: r["proposed_rules"][0].pop("example_good"), "missing required key 'example_good'"),
    ],
)
def test_reply_schema_is_strict(tmp_path, mutation, match):
    reply = _reply()
    mutation(reply)
    path = tmp_path / "review.json"
    path.write_text(json.dumps(reply))
    with pytest.raises(ReplyError, match=match):
        load_reply(path)


def test_review_level_writes_packet_and_ingests_reply(outdirs, data_dir, tmp_path):
    ledger = load_ledger()
    findings, notes = run_review_level(package="pkg", package_version=None, outdirs=outdirs, ledger=ledger, mode="all")
    assert [f.rule for f in findings] == [PACKET_RULE] and findings[0].level == 3 and findings[0].severity == "info"
    packet_dir = Path(findings[0].message.split("written to ")[1].split(" (")[0])
    prompt_hash = json.loads((packet_dir / "packet.json").read_text())["prompt_hash"]
    reply_path = tmp_path / "review.json"
    reply_path.write_text(json.dumps(_reply(prompt_hash)))
    findings, notes = run_review_level(
        package="pkg", package_version=None, outdirs=outdirs, ledger=ledger, mode="all", packet_dir=packet_dir, reply=reply_path
    )
    rules = [f.rule for f in findings]
    assert rules == [PACKET_RULE, "DR001", "REVIEW-PROPOSED"]
    assert findings[1].fix and findings[1].tool == "review:test-model" and findings[1].detector == "llm"
    assert any("1 proposed rule(s)" in n for n in notes)
    assert not any("differs" in n for n in notes)


def test_review_never_gates_unless_asked():
    report = Report("p", "/p", [3], [Finding(PACKET_RULE, "info", 3, "packet")])
    assert report.exit_code("info") == 0
    assert report.exit_code("info", fail_on_review=True) == 0  # a packet is not a defect
    report.findings.append(Finding("DR001", "error", 3, "reviewer"))
    assert report.exit_code("error") == 0
    assert report.exit_code("error", fail_on_review=True) == EXIT_FOR_LEVEL[3] == 14


# --------------------------------------------------------------------------
# ledger propose
# --------------------------------------------------------------------------


def test_next_rule_id_per_prefix():
    assert next_rule_id(["DR001", "DR035", "DQ003"], prefix="DR") == "DR036"
    assert next_rule_id(["DR001"], prefix="DS") == "DS001"


def test_propose_writes_a_loadable_proposed_rule_that_does_not_run_by_default(tmp_path, data_dir):
    reply_path = tmp_path / "review.json"
    reply_path.write_text(json.dumps(_reply()))
    result = propose(reply_path)
    assert result.written == ["DS001"] and not result.rejected
    assert result.overlay == data_dir / "ledger" / "proposed"
    yaml_text = (result.overlay / "DS001.yaml").read_text()
    assert "status: {proposed:" in yaml_text and "kind: regex" in yaml_text
    fixture = (result.overlay / "DS001.py").read_text()
    assert "# ruleid: DS001" in fixture and "# ok: DS001" in fixture
    ledger = load_ledger(result.overlay)
    assert ledger["DS001"].is_proposed
    assert "DS001" not in {r.id for r in ledger.of_kind("regex")}
    assert "DS001" in {r.id for r in ledger.of_kind("regex", include_proposed=True)}
    # a second proposal gets the next id
    result = propose(reply_path)
    assert result.written == ["DS002"]


def test_propose_rejects_a_rule_whose_examples_do_not_behave(tmp_path):
    reply = _reply()
    reply["proposed_rules"][0]["example_good"] = "Do it.\n\nArgs:\n    x: the thing\n"  # fires on the good one
    reply_path = tmp_path / "review.json"
    reply_path.write_text(json.dumps(reply))
    result = propose(reply_path, overlay=tmp_path / "overlay")
    assert not result.written and len(result.rejected) == 1
    assert "fires on example_good" in result.rejected[0]
    assert not list((tmp_path / "overlay").glob("*"))
