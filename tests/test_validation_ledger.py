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
    napoleon = napoleon not in (False, "false")
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


def test_duplicate_rule_id_is_a_ledger_error(tmp_path):
    src = BUNDLED_RULES_DIR / "rendering" / "DR001.yaml"
    (tmp_path / "DR001.yaml").write_text(src.read_text())
    (tmp_path / "DR001.py").write_text('"""x"""\n')
    catalog = Ledger()
    catalog.add_dir(BUNDLED_RULES_DIR)
    with pytest.raises(LedgerError, match="duplicate rule id"):
        catalog.add_dir(tmp_path)


def test_overlay_overrides_by_id(tmp_path):
    src = BUNDLED_RULES_DIR / "rendering" / "DR001.yaml"
    (tmp_path / "DR001.yaml").write_text(
        src.read_text().replace("severity: error", "severity: info")
    )
    (tmp_path / "DR001.py").write_text('"""x"""\n')
    catalog = load_ledger(tmp_path)
    assert catalog["DR001"].severity == "info"


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
    (tmp_path / "DR001.py").write_text('"""x"""\n')
    with pytest.raises(LedgerError, match=match):
        load_rule(tmp_path / "DR001.yaml")


def test_parse_rule_without_fixture_is_a_ledger_error(tmp_path):
    (tmp_path / "DR001.yaml").write_text(
        (BUNDLED_RULES_DIR / "rendering" / "DR001.yaml").read_text()
    )
    with pytest.raises(LedgerError, match="fixture"):
        load_rule(tmp_path / "DR001.yaml")
