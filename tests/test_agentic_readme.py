"""Tests for the README check of agentic aspects, the rendered section, and its placement.

Fixtures are small projects built on the fly: a package with a shipped skill, a
subagent and a ``CLAUDE.md``, with a README that either documents them or not.
The check must report each kind as ``ok``, ``warn`` or ``n/a``; ``--fail-on
warn`` alone makes the exit code non-zero; the rendered section follows the
policy (humour on or off, agents first or last) and the user's snippets; a
second write is a no-op and a moved section is updated where it is.
"""

import json

import pytest

from epythet.agentic_readme import (
    MARKER_END,
    MARKER_START,
    blurb,
    check_readme,
    draft_section,
    github_anchor,
    headings_of,
    place_section,
    render_section,
    splice_section,
    write_section,
)
from epythet.ai_artifacts import discover_artifacts
from epythet.config import load_config
from epythet.userconfig import ReadmePolicy, UserConfig, init_snippets, snippets_dir

SKILL_MD = "---\nname: pkg-quickstart\ndescription: Use pkg quickly. Use when starting.\n---\n\n# Body\n"
AGENT_MD = "---\nname: pkg-helper\ndescription: Helps with pkg tasks in a subagent.\ntools: Read\n---\n\nprompt\n"


@pytest.fixture
def project(make_project):
    """A package with a shipped skill, a subagent, a CLAUDE.md and a GitHub URL."""
    root = make_project("pkg", {"core.py": '"""Core."""\n\ndef f():\n    """F."""\n'})
    (root / "pyproject.toml").write_text(
        '[project]\nname = "pkg"\nversion = "0.0.1"\n'
        '[project.urls]\nHomepage = "https://github.com/org/pkg"\n'
    )
    skill = root / "pkg" / "data" / "skills" / "pkg-quickstart"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL_MD)
    agents = root / "pkg" / "data" / "agents"
    agents.mkdir()
    (agents / "pkg-helper.md").write_text(AGENT_MD)
    (root / "CLAUDE.md").write_text("# pkg\n")
    return root


def _statuses(report):
    return {c.kind: c.status for c in report.checks}


# --------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------


def test_undocumented_readme_warns_on_every_present_kind(project, config_dir):
    (project / "README.md").write_text("# pkg\n\nA package.\n\n## Install\n\npip install pkg\n")
    report = check_readme(project)
    assert report.readme == project / "README.md"
    assert _statuses(report) == {
        "skills": "warn",
        "subagents": "warn",
        "instruction_files": "warn",
        "agent_docs": "warn",
        "section": "warn",
    }
    assert report.status == "warn"
    assert {c.kind for c in report.warnings} == set(_statuses(report))
    assert report.policy.readme == ReadmePolicy()  # packaged defaults
    data = report.to_dict()
    assert data["status"] == "warn" and data["policy"]["readme"]["agentic_aspects"] == "warn"
    assert "warn: the README does not document" in report.table()


def test_documented_readme_is_ok(project, config_dir):
    (project / "README.md").write_text(
        "# pkg\n\n## For AI agents\n\n"
        "gh skill install org/pkg pkg-quickstart --agent claude-code\n"
        "Subagent `pkg-helper`. Read `CLAUDE.md`. The site serves llms.txt.\n"
    )
    report = check_readme(project)
    assert set(_statuses(report).values()) == {"ok"}
    assert "ok: every agentic aspect" in report.table()
    section = next(c for c in report.checks if c.kind == "section")
    assert "For AI agents" in section.evidence


def test_partially_documented_readme(project, config_dir):
    (project / "README.md").write_text("# pkg\n\nInstall the `pkg-quickstart` skill.\n")
    statuses = _statuses(check_readme(project))
    assert statuses["skills"] == "ok"
    assert statuses["subagents"] == "warn"
    assert statuses["section"] == "warn"


def test_absent_kinds_are_not_applicable(make_project, config_dir):
    root = make_project("bare", {"m.py": '"""M."""\n'})
    (root / "README.md").write_text("# bare\n")
    statuses = _statuses(check_readme(root))
    assert statuses["skills"] == statuses["subagents"] == statuses["instruction_files"] == "n/a"
    assert statuses["agent_docs"] == "warn"  # agent_outputs is on by default
    assert statuses["section"] == "warn"


def test_no_agent_outputs_means_nothing_to_document(make_project, config_dir):
    root = make_project("quiet", {"m.py": '"""M."""\n'})
    (root / "pyproject.toml").write_text(
        '[project]\nname = "quiet"\nversion = "0.0.1"\n[tool.epythet]\nagent_outputs = false\n'
    )
    (root / "README.md").write_text("# quiet\n")
    report = check_readme(root)
    assert set(_statuses(report).values()) == {"n/a"}
    assert report.status == "ok"


def test_missing_readme_warns(project, config_dir):
    report = check_readme(project)
    assert report.readme is None
    assert report.status == "warn"
    assert "none found" in report.table()


def test_non_python_tree_is_checked_too(tmp_path, config_dir):
    root = tmp_path / "notpy"
    (root / "skills" / "do-it").mkdir(parents=True)
    (root / "skills" / "do-it" / "SKILL.md").write_text(
        "---\nname: do-it\ndescription: Does it.\n---\nbody\n"
    )
    (root / "README.md").write_text("# notpy\n")
    statuses = _statuses(check_readme(root))
    assert statuses["skills"] == "warn"
    assert statuses["agent_docs"] == "n/a"


# --------------------------------------------------------------------------
# README structure helpers
# --------------------------------------------------------------------------


def test_headings_skip_fences_and_anchors_match_github():
    text = "# T\n\n```bash\n# not a heading\n```\n\n## Sub *x* `y`!\n\n~~~\n## nope\n~~~\n"
    assert [(h.level, h.title) for h in headings_of(text)] == [(1, "T"), (2, "Sub *x* `y`!")]
    assert github_anchor("Sub *x* `y`!") == "sub-x-y"
    assert github_anchor("What it fixes without touching your docstrings") == (
        "what-it-fixes-without-touching-your-docstrings"
    )


def test_place_section_first_goes_before_the_first_section_heading():
    text = "# T\n\nintro\n\n```\n# fence\n```\n\n## A\n\na\n\n## B\n"
    start, end, heading, level = place_section(text, agentic_first=True)
    assert text[start:end] == "" and text[start:].startswith("## A")
    assert heading.title == "A" and level == 2


def test_place_section_last_goes_at_the_end():
    text = "# T\n\n## A\n\na\n"
    start, end, heading, level = place_section(text, agentic_first=False)
    assert start == end == len(text) and heading is None and level == 2


def test_place_section_with_only_a_title_or_no_headings():
    assert place_section("# T\n\nintro\n", agentic_first=True)[3] == 2
    assert place_section("just text\n", agentic_first=True)[1] == len("just text\n")
    assert place_section("", agentic_first=False) == (0, 0, None, 1)


def test_place_section_finds_and_keeps_an_existing_marked_section():
    text = f"# T\n\n## A\n\n{MARKER_START}\nold\n{MARKER_END}\n\n## B\n"
    start, end, heading, level = place_section(text, agentic_first=False)
    assert text[start:end] == f"{MARKER_START}\nold\n{MARKER_END}\n"
    assert heading.title == "B" and level == 2
    new = splice_section(text, f"{MARKER_START}\nnew\n{MARKER_END}", start=start, end=end)
    assert new == f"# T\n\n## A\n\n{MARKER_START}\nnew\n{MARKER_END}\n\n## B\n"


def test_blurb_is_the_first_sentence_shortened_at_a_clause():
    assert blurb("Find things. Use when lost.") == "find things"
    long = "Run the sweep on one repository end to end, baseline, validate, " + "x " * 80
    assert blurb(long) == "run the sweep on one repository end to end"
    assert blurb("HTTP things and more. Rest.") == "HTTP things and more"
    assert blurb("") == ""
    assert blurb("word " * 60).endswith("…")


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def test_section_lists_every_kind_with_links(project, config_dir):
    config = load_config(project)
    artifacts = discover_artifacts(project, package_dir=config.package_dir)
    text = render_section(artifacts, config, policy=ReadmePolicy(), level=2)
    assert text.startswith(MARKER_START) and text.rstrip().endswith(MARKER_END)
    assert "## For AI agents" in text
    assert "gh skill install org/pkg pkg-quickstart --agent claude-code" in text
    assert "| `pkg-quickstart` | use pkg quickly |" in text
    assert "`pkg-helper` (helps with pkg tasks in a subagent)" in text
    assert "`CLAUDE.md` (Claude Code)" in text
    assert "[`llms.txt`](https://org.github.io/pkg/llms.txt)" in text
    assert "[`pkg.md`](https://org.github.io/pkg/pkg.md)" in text
    assert "https://org.github.io/pkg/ai-agents.html" in text
    assert "If you are a human, the rest of this README" in text
    assert "—" not in text  # no em-dashes, ever


def test_humor_draws_a_stable_line_from_the_pool(project, config_dir):
    config = load_config(project)
    artifacts = discover_artifacts(project, package_dir=config.package_dir)
    policy = ReadmePolicy(humor=True)
    first = render_section(artifacts, config, policy=policy)
    assert first == render_section(artifacts, config, policy=policy)
    line = next(l for l in first.splitlines() if "rest of this README" in l)
    assert not line.startswith("If you are a human")
    assert line.startswith("If you")


def test_section_uses_user_snippets(project, config_dir):
    init_snippets()
    (snippets_dir() / "agentic-readme-humor.md").write_text("If you are exactly you\n")
    (snippets_dir() / "agentic-readme-section.md").write_text(
        "{marker_start}\n{heading} Agents\n\nMine: {name} {humans_link}\n{for_humans_intro}\n{marker_end}\n"
    )
    config = load_config(project)
    artifacts = discover_artifacts(project, package_dir=config.package_dir)
    text = render_section(artifacts, config, policy=ReadmePolicy(humor=True), humans_link="[X](#x)")
    assert "# Agents\n\nMine: pkg [X](#x)\nIf you are exactly you\n" in text


def test_section_without_repo_url_has_no_install_line(make_project, config_dir):
    root = make_project("nourl", {"m.py": '"""M."""\n'})
    skill = root / "nourl" / "data" / "skills" / "nourl-x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: nourl-x\ndescription: Do x.\n---\nbody\n")
    config = load_config(root)
    text = render_section(discover_artifacts(root, package_dir=config.package_dir), config, policy=ReadmePolicy())
    assert "gh skill install" not in text
    assert "| `nourl-x` | do x |" in text
    assert "`llms.txt` indexes every page" in text  # no site URL, no link


# --------------------------------------------------------------------------
# Draft and write
# --------------------------------------------------------------------------


def _policy(**readme):
    return UserConfig(readme=ReadmePolicy(**readme))


def test_write_adds_first_then_updates_in_place_and_is_idempotent(project, config_dir):
    readme = project / "README.md"
    readme.write_text("# pkg\n\nA package.\n\n## Install\n\npip install pkg\n\n## Usage\n")
    path, outcome = write_section(project, user_config=_policy(agentic_aspects="add", agentic_first=True))
    assert (path, outcome) == (readme, "added")
    text = readme.read_text()
    assert text.index(MARKER_START) < text.index("## Install")
    assert "starting at [Install](#install)" in text
    assert "## For AI agents" in text
    assert _statuses(check_readme(project))["section"] == "ok"

    assert write_section(project, user_config=_policy(agentic_first=True))[1] == "unchanged"

    # the author moves the section; an update keeps it there
    moved = text.replace(text[text.index(MARKER_START) : text.index(MARKER_END) + len(MARKER_END) + 1], "")
    moved = moved + "\n" + text[text.index(MARKER_START) : text.index(MARKER_END) + len(MARKER_END)] + "\n"
    readme.write_text(moved)
    _, outcome = write_section(project, user_config=_policy(humor=True, agentic_first=True))
    assert outcome == "updated"
    final = readme.read_text()
    assert final.index("## Usage") < final.index(MARKER_START)
    assert final.count(MARKER_START) == final.count(MARKER_END) == 1
    assert "starting at the top of the page" in final


def test_write_last_when_not_agentic_first(project, config_dir):
    readme = project / "README.md"
    readme.write_text("# pkg\n\n## Install\n")
    write_section(project, user_config=_policy())
    text = readme.read_text()
    assert text.index("## Install") < text.index(MARKER_START)
    assert text.endswith(MARKER_END + "\n")


def test_write_creates_a_readme_when_none_exists(project, config_dir):
    path, outcome = write_section(project, user_config=_policy())
    assert outcome == "added" and path.name == "README.md"
    assert path.read_text().startswith(MARKER_START)


def test_write_refuses_a_non_markdown_readme(project, config_dir):
    (project / "README.rst").write_text("pkg\n===\n")
    with pytest.raises(ValueError, match="not Markdown"):
        write_section(project, user_config=_policy())


def test_draft_does_not_write(project, config_dir):
    (project / "README.md").write_text("# pkg\n\n## A\n")
    section, text, start, end = draft_section(project, user_config=_policy(agentic_first=True))
    assert section.startswith(MARKER_START)
    assert (project / "README.md").read_text() == text == "# pkg\n\n## A\n"
    assert start == end == text.index("## A")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_outputs_and_exit_codes(project, config_dir, capsys):
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    def run(*argv):
        code = cw.run(mk_epythet_parser(), list(argv), convention=CONVENTION)
        return code, capsys.readouterr().out

    (project / "README.md").write_text("# pkg\n\n## Install\n")
    code, out = run("ai-readme-check", str(project))
    assert code == 0 and "warn: the README does not document" in out
    code, out = run("ai-readme-check", str(project), "--fail-on", "warn")
    assert code == 1
    code, out = run("ai-readme-check", str(project), "--format", "json")
    data = json.loads(out)
    assert data["status"] == "warn" and data["policy"]["readme"]["humor"] is False
    assert {c["kind"] for c in data["checks"]} == {"section", "skills", "subagents", "instruction_files", "agent_docs"}
    code, out = run("ai-readme-check", str(project), "--draft")
    assert code == 0 and out.startswith(MARKER_START) and MARKER_START not in (project / "README.md").read_text()
    code, out = run("ai-readme-check", str(project), "--write", "--fail-on", "warn")
    assert code == 0 and out.startswith("added: ") and "ok: every agentic aspect" in out
    code, _ = run("ai-readme-check", str(project), "--draft", "--write")
    assert code == 2
    code, _ = run("ai-readme-check", str(project), "--fail-on", "error")
    assert code == 2


def test_cli_reads_the_local_policy(project, config_dir, capsys):
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    config_dir.mkdir()
    (config_dir / "config.toml").write_text('[readme]\nagentic_aspects = "add"\nhumor = true\nagentic_first = true\n')
    (project / "README.md").write_text("# pkg\n\n## Install\n")
    code = cw.run(mk_epythet_parser(), ["ai-readme-check", str(project), "--format", "json"], convention=CONVENTION)
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["policy"]["readme"] == {"agentic_aspects": "add", "humor": True, "agentic_first": True}
    assert data["policy"]["path"] == str(config_dir / "config.toml")
