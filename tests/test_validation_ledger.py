"""The ledger's fixture corpus is its regression suite.

Every rule with a parse-level detector ships a sibling ``.py`` fixture whose
functions are tagged ``# ruleid: DRnnn`` (the rule must fire on that
docstring) or ``# ok: DRnnn`` (it must not). This module turns that corpus
into one test per specimen, and checks the catalog's own integrity (the
condition behind exit code 20).
"""

from pathlib import Path

import pytest

from epythet.validation.ledger import (
    BUNDLED_RULES_DIR,
    Ledger,
    LedgerError,
    iter_fixture_cases,
    load_ledger,
    load_rule,
    PARSE_KINDS,
)
from epythet.validation.parse import evaluate_rule, parse_docstring


@pytest.fixture(scope="module")
def ledger():
    return load_ledger()


def _specimens():
    """Every (rule, case) pair in the bundled corpus, as pytest ids ``DR001:bad_x``."""
    catalog = load_ledger()
    for rule in catalog.of_kind(*PARSE_KINDS):
        assert rule.fixture_path is not None, f"{rule.id} has no fixture"
        for case in iter_fixture_cases(rule.fixture_path):
            assert rule.id in case.rule_ids, (
                f"{rule.fixture_path}:{case.line} is tagged for {case.rule_ids}, not {rule.id}"
            )
            yield pytest.param(
                rule.id, case, id=f"{rule.id}:{case.name.split('.')[-1]}"
            )


@pytest.mark.parametrize("rule_id,case", list(_specimens()))
def test_fixture_specimen(ledger, rule_id, case):
    rule = ledger[rule_id]
    napoleon = rule.applies_to.get("napoleon", True)
    parsed = parse_docstring(case.docstring, napoleon=napoleon)
    hits = evaluate_rule(rule, parsed)
    if case.expect_hit:
        assert hits, (
            f"{rule_id} did not fire on {case.name} (messages: {parsed.messages})"
        )
    else:
        assert not hits, f"{rule_id} fired on control {case.name}: {hits}"


def test_every_parse_rule_has_a_bad_and_a_good_specimen(ledger):
    for rule in ledger.of_kind(*PARSE_KINDS):
        cases = list(iter_fixture_cases(rule.fixture_path))
        assert any(c.expect_hit for c in cases), f"{rule.id}: no ruleid specimen"
        assert any(not c.expect_hit for c in cases), f"{rule.id}: no ok specimen"


def test_bundled_ledger_loads_and_has_the_seed_rules(ledger):
    seed = {
        "DR001",
        "DR002",
        "DR003",
        "DR005",
        "DR010",
        "DR011",
        "DR012",
        "DR018",
        "DR019",
        "DR020",
        "DR021",
        "DR028",
        "DR029",
    }
    assert seed <= set(ledger.rules), seed - set(ledger.rules)
    assert len(ledger) >= 20


def test_build_rules_classify_their_example_warning(ledger):
    from epythet.validation.build import classify_warning, parse_warning_line

    for rule in ledger.of_kind("build-warning"):
        warning = parse_warning_line(rule.detector["example_warning"])
        assert warning is not None, rule.id
        assert classify_warning(warning, ledger).id == rule.id


def _copy_dr001(tmp_path, *, yaml_transform=lambda s: s):
    src = BUNDLED_RULES_DIR / "rendering" / "DR001.yaml"
    (tmp_path / "DR001.yaml").write_text(yaml_transform(src.read_text()))
    (tmp_path / "DR001.py").write_text(src.with_suffix(".py").read_text())


def test_duplicate_rule_id_is_a_ledger_error(tmp_path):
    _copy_dr001(tmp_path)
    catalog = Ledger()
    catalog.add_dir(BUNDLED_RULES_DIR)
    with pytest.raises(LedgerError, match="duplicate rule id"):
        catalog.add_dir(tmp_path)


def test_overlay_overrides_by_id(tmp_path):
    _copy_dr001(
        tmp_path,
        yaml_transform=lambda s: s.replace("severity: error", "severity: info"),
    )
    catalog = load_ledger(tmp_path)
    assert catalog["DR001"].severity == "info"
    assert str(tmp_path) in [str(p) for p in catalog.sources]


@pytest.mark.parametrize(
    "transform,match",
    [
        (lambda s: s + "applies_to_extra: 1\n", "unknown field"),
        (
            lambda s: s.replace("  autofixable: true", '  autofixable: "true"'),
            "YAML boolean",
        ),
        (
            lambda s: s.replace("applies_to:\n", "applies_to:\n  napoleon: 'false'\n"),
            "YAML boolean",
        ),
    ],
)
def test_strict_schema(tmp_path, transform, match):
    _copy_dr001(tmp_path, yaml_transform=transform)
    with pytest.raises(LedgerError, match=match):
        load_rule(tmp_path / "DR001.yaml")


def test_untagged_fixture_is_a_ledger_error(tmp_path):
    _copy_dr001(tmp_path)
    (tmp_path / "DR001.py").write_text('"""x"""\n\n\ndef f():\n    """Do."""\n')
    with pytest.raises(LedgerError, match="ruleid"):
        load_rule(tmp_path / "DR001.yaml")


def test_proposed_rules_do_not_run_by_default(tmp_path):
    _copy_dr001(
        tmp_path,
        yaml_transform=lambda s: s.replace(
            'status: {stable_since: "0.2.0"}',
            'status: {proposed: "0.3.0", proposed_by: llm}',
        ),
    )
    catalog = load_ledger(tmp_path)
    assert "DR001" not in {r.id for r in catalog.of_kind("regex")}
    assert "DR001" in {r.id for r in catalog.of_kind("regex", include_proposed=True)}


def test_build_example_must_classify_to_its_rule(tmp_path):
    src = BUNDLED_RULES_DIR / "build_warnings" / "DR024.yaml"
    (tmp_path / "DR024.yaml").write_text(
        src.read_text().replace(
            "warning_type: image.not_readable", "warning_type: image.nope"
        )
    )
    with pytest.raises(LedgerError, match="classifies to"):
        load_ledger(tmp_path)


def test_literal_text_never_trips_a_prose_regex(ledger):
    from epythet.validation.docstrings import Docstring
    from epythet.validation.parse import findings_for, parse_docstring

    text = "Insert a blank line before the first ``:param x:`` line; ``>>> f()`` is a prompt."
    doc = Docstring("m.py", 1, 1, "m.f", "function", text, repr(text), False)
    found = list(
        findings_for(parse_docstring(doc), ledger.of_kind("regex", "source", "doctree"))
    )
    assert [f.rule for f in found] == []


def test_catch_all_dr032_is_suppressed_by_a_specific_rule(ledger):
    from epythet.validation.docstrings import Docstring
    from epythet.validation.parse import findings_for, parse_docstring

    rules = ledger.of_kind("regex", "source", "doctree")
    doc = Docstring("m.py", 1, 1, "m.f", "function", "Call f(*args) now.", "", False)
    fired = {f.rule for f in findings_for(parse_docstring(doc), rules)}
    assert "DR010" in fired and "DR032" not in fired
    doc = Docstring(
        "m.py",
        1,
        1,
        "m.f",
        "function",
        "Do a thing.\n\nA paragraph.\n\n        deep\n    less deep\n",
        "",
        False,
    )
    fired = {f.rule for f in findings_for(parse_docstring(doc), rules)}
    assert "DR032" in fired


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("severity: error", "severity must be"),
        ("id: DR001", "must match rule id"),
        ("kind: regex", "detector.kind must be"),
    ],
)
def test_schema_violations_are_ledger_errors(tmp_path, mutation, match):
    src = (BUNDLED_RULES_DIR / "rendering" / "DR001.yaml").read_text()
    broken = {
        "severity: error": src.replace("severity: error", "severity: fatal"),
        "id: DR001": src.replace("id: DR001", "id: DR999"),
        "kind: regex": src.replace("kind: regex", "kind: magic"),
    }[mutation]
    (tmp_path / "DR001.yaml").write_text(broken)
    (tmp_path / "DR001.py").write_text(
        (BUNDLED_RULES_DIR / "rendering" / "DR001.py").read_text()
    )
    with pytest.raises(LedgerError, match=match):
        load_rule(tmp_path / "DR001.yaml")


def test_parse_rule_without_fixture_is_a_ledger_error(tmp_path):
    (tmp_path / "DR001.yaml").write_text(
        (BUNDLED_RULES_DIR / "rendering" / "DR001.yaml").read_text()
    )
    with pytest.raises(LedgerError, match="fixture"):
        load_rule(tmp_path / "DR001.yaml")
