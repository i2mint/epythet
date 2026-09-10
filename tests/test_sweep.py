"""``epythet sweep``: many packages read-only, the distribution, the queue, the manifest, the CLI."""

import json
import os

import pytest

import cw
from epythet.sweep import packages_from_manifest, queue_score, render_sweep, sweep, sweep_command

BAD = '''\
"""Bad module."""


def leaky(x):
    """Do a thing.
    :param x: the x value
    """


def glued():
    """Do a thing.
    >>> f(1)
    1
    """


def undocumented(x):
    return x
'''

CLEAN = '''\
"""Clean module."""


def fine(x):
    """Return x unchanged.

    >>> fine(1)
    1
    """
'''


@pytest.fixture
def two_projects(make_project):
    bad = make_project("badpkg", {"mod.py": BAD}, init='"""Bad package."""\nfrom badpkg.mod import leaky, glued\n')
    good = make_project("goodpkg", {"mod.py": CLEAN}, init='"""Good package."""\nfrom goodpkg.mod import fine\n')
    return bad, good


def _mtimes(root):
    return {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


def test_sweep_is_read_only_and_ranks_the_bad_package_first(two_projects, tmp_path, data_dir):
    bad, good = two_projects
    before = {**_mtimes(bad), **_mtimes(good)}
    result = sweep([bad, good, tmp_path / "missing"], observations_path=tmp_path / "obs.jsonl")
    assert {**_mtimes(bad), **_mtimes(good)} == before
    assert [p.name for p in result.swept] == ["badpkg", "goodpkg"]
    assert result.packages[2].error and "missing" in result.packages[2].path
    assert [p.name for p in result.queue()] == ["badpkg", "goodpkg"]
    rules = {row["rule"] for row in result.distribution()}
    assert {"DR001", "DR003", "DQ001", "DQ002"} <= rules
    bad_counts = result.swept[0].counts
    assert bad_counts["DR001"] == 1 and bad_counts["DR003"] == 1 and bad_counts["DQ002"] == 1
    assert result.swept[1].counts == {}
    # observations went to the file, the sweep summary to the data dir
    assert (tmp_path / "obs.jsonl").exists()
    sweeps = (data_dir / "ledger" / "sweeps.jsonl").read_text().splitlines()
    assert len(sweeps) == 1 and json.loads(sweeps[0])["queue"][0]["name"] == "badpkg"


def test_distribution_rows_are_complete(two_projects, tmp_path, data_dir):
    bad, good = two_projects
    result = sweep([bad, good], observations_path=tmp_path / "obs.jsonl", record=False)
    row = next(r for r in result.distribution() if r["rule"] == "DR001")
    assert row["findings"] == 1 and row["packages"] == 1 and row["package_share"] == 0.5
    assert row["severity"] == "error" and row["title"] == "RST field list leaked into prose"
    assert row["per_100_objects"] == round(100 / sum(p.objects for p in result.swept), 2)


def test_queue_score_weights_entry_points_first():
    assert queue_score({"DQ002": 1}, severities={}) > queue_score({"DQ003": 3}, severities={})
    assert queue_score({"DR001": 1}, severities={"DR001": "error"}) == 5.0


def test_manifest_is_read_only_and_parsed(two_projects, tmp_path, data_dir):
    bad, good = two_projects
    manifest = tmp_path / "my_packages.pth"
    manifest.write_text(f"# comment\n{bad}\n\nimport sys\n{good}\n")
    before = manifest.read_bytes()
    assert packages_from_manifest(manifest) == [bad, good]
    result = sweep(manifest=manifest, observations_path=tmp_path / "obs.jsonl", record=False, limit=1)
    assert [p.name for p in result.packages] == ["badpkg"]
    assert manifest.read_bytes() == before


def test_render_and_cli_json(two_projects, tmp_path, data_dir, capsys):
    bad, good = two_projects
    result = sweep([bad, good], observations_path=tmp_path / "obs.jsonl", record=False)
    text = render_sweep(result)
    assert text.startswith("epythet sweep: 2 package(s) swept") and "queue (top 20" in text
    assert "DR001     error" in text
    out = tmp_path / "sweep.json"
    sweep_command(str(bad), str(good), no_observe=True, format="json", output=str(out), quiet=True)
    data = json.loads(out.read_text())
    assert data["queue"][0]["name"] == "badpkg" and data["packages"][1]["counts"] == {}
    with pytest.raises(cw.CommandError) as info:
        sweep_command(format="table")
    assert info.value.code == 2
