"""Level 0 coverage detectors: every fixture specimen, the public surface, entry points, ``__all__``."""

import pytest

from epythet.validation import load_ledger, validate
from epythet.validation.coverage import (
    Param,
    entry_point_names,
    evaluate_coverage_rule,
    iter_coverage_cases,
    iter_public_objects,
    restates_type,
    trivial_summary_words,
)


def _specimens():
    catalog = load_ledger()
    for rule in catalog.of_kind("coverage"):
        for case in iter_coverage_cases(rule.fixture_path):
            if rule.id in case.rule_ids:
                yield pytest.param(rule.id, case, id=f"{rule.id}:{case.name.split('.')[-1]}")


@pytest.mark.parametrize("rule_id,case", list(_specimens()))
def test_coverage_specimen(rule_id, case):
    rule = load_ledger()[rule_id]
    hits = evaluate_coverage_rule(rule, case.object)
    assert bool(hits) == case.expect_hit, (rule_id, case.name, hits)


def test_every_coverage_rule_has_both_specimens():
    for rule in load_ledger().of_kind("coverage"):
        cases = [c for c in iter_coverage_cases(rule.fixture_path) if rule.id in c.rule_ids]
        assert any(c.expect_hit for c in cases) and any(not c.expect_hit for c in cases), rule.id


@pytest.mark.parametrize(
    "name,summary,trivial",
    [
        ("load_config", "Load the config.", True),
        ("load_config", "Loads configs.", True),
        ("DocsConfig", "The docs config.", True),
        ("load_config", "Read pyproject.toml into a DocsConfig.", False),
        ("f", "", False),
    ],
)
def test_trivial_summary_heuristic(name, summary, trivial):
    assert trivial_summary_words(name, summary) is trivial


def test_type_restatement_heuristic():
    assert restates_type(Param("n", "int", "an integer"))
    assert restates_type(Param("names", "list[str]", "a list of strings"))
    assert not restates_type(Param("n", "int", "how many retries"))
    assert not restates_type(Param("n", None, "an integer"))


def test_public_surface_and_entry_points(make_project):
    project = make_project(
        "pkg",
        {
            "mod.py": '"""Mod."""\n\n__all__ = ["exported"]\n\n\ndef exported():\n    """Exported."""\n\n\ndef hidden():\n    """Not in __all__."""\n\n\nclass K:\n    """K."""\n\n    def method(self):\n        """M."""\n\n    def _private(self):\n        pass\n',
            "_internal.py": '"""Private module."""\n\n\ndef f():\n    pass\n',
        },
        init='"""Package."""\nfrom pkg.mod import exported\n',
    )
    package_dir = project / "pkg"
    assert entry_point_names(package_dir) == {"exported"}
    objects = list(iter_public_objects(package_dir))
    names = [o.qualname for o in objects]
    assert names == ["pkg", "pkg.mod", "pkg.mod.exported"]
    assert objects[2].is_entry_point


def test_all_in_init_narrows_entry_points(make_project):
    project = make_project("pkg", {"mod.py": '"""Mod."""\n\n\ndef a():\n    """A."""\n\n\ndef b():\n    """B."""\n'}, init='"""P."""\n__all__ = ["a"]\nfrom pkg.mod import a, b\n')
    assert entry_point_names(project / "pkg") == {"a"}
    objects = {o.qualname: o for o in iter_public_objects(project / "pkg")}
    assert objects["pkg.mod.a"].is_entry_point and not objects["pkg.mod.b"].is_entry_point


def test_level_0_without_linters_reports_coverage_only(make_project, tmp_path):
    project = make_project("pkg", {"mod.py": '"""Mod."""\n\n\ndef load_config(path):\n    """Load the config."""\n\n\ndef bare(x):\n    return x\n'}, init='"""P."""\nfrom pkg.mod import load_config\n')
    report = validate(project, level=0, linters=False, observations_path=tmp_path / "obs.jsonl")
    rules = sorted(f.rule for f in report.findings)
    assert rules == ["DQ001", "DQ002", "DQ003"]
    assert report.objects_checked == 4 and report.objects_undocumented == 1
    assert all(f.tool == "epythet" and f.level == 0 for f in report.findings)
    assert report.exit_code("warning") == 10 and report.exit_code() == 0
