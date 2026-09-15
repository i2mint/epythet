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
    SectionError,
    blurb,
    check_readme,
    draft_section,
    github_anchor,
    headings_of,
    marker_span,
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
    (project / "README.md").write_text(
        "# pkg\n\nA package.\n\n## Install\n\npip install pkg\n"
    )
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
    assert report.policy == ReadmePolicy()  # packaged defaults
    data = report.to_dict()
    assert (
        data["status"] == "warn"
        and data["policy"]["readme"]["agentic_aspects"] == "warn"
    )
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
    """A bare package with no site URL has nothing an agent could be pointed at."""
    root = make_project("bare", {"m.py": '"""M."""\n'})
    (root / "README.md").write_text("# bare\n")
    report = check_readme(root)
    assert set(_statuses(report).values()) == {"n/a"}
    assert report.status == "ok"


def test_agent_docs_present_only_with_a_site(make_project, config_dir):
    """With a GitHub URL the site's llms.txt and <pkg>.md become aspects to document."""
    root = make_project("sited", {"m.py": '"""M."""\n'})
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sited"\nversion = "0.0.1"\n[project.urls]\nHomepage = "https://github.com/o/sited"\n'
    )
    (root / "README.md").write_text("# sited\n")
    statuses = _statuses(check_readme(root))
    assert statuses["agent_docs"] == "warn" and statuses["section"] == "warn"
    assert statuses["skills"] == "n/a"


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
    text = (
        "# T\n\n```bash\n# not a heading\n```\n\n## Sub *x* `y`!\n\n~~~\n## nope\n~~~\n"
    )
    assert [(h.level, h.title) for h in headings_of(text)] == [
        (1, "T"),
        (2, "Sub *x* `y`!"),
    ]
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
    new = splice_section(
        text, f"{MARKER_START}\nnew\n{MARKER_END}", start=start, end=end
    )
    assert new == f"# T\n\n## A\n\n{MARKER_START}\nnew\n{MARKER_END}\n\n## B\n"


def test_blurb_is_the_first_sentence_shortened_at_a_clause():
    assert blurb("Find things. Use when lost.") == "find things"
    long = (
        "Run the sweep on one repository end to end, baseline, validate, " + "x " * 80
    )
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
    text = render_section(
        artifacts, config, policy=ReadmePolicy(humor=True), humans_link="[X](#x)"
    )
    assert "# Agents\n\nMine: pkg [X](#x)\nIf you are exactly you\n" in text


def test_section_without_repo_url_has_no_install_line(make_project, config_dir):
    root = make_project("nourl", {"m.py": '"""M."""\n'})
    skill = root / "nourl" / "data" / "skills" / "nourl-x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: nourl-x\ndescription: Do x.\n---\nbody\n"
    )
    config = load_config(root)
    text = render_section(
        discover_artifacts(root, package_dir=config.package_dir),
        config,
        policy=ReadmePolicy(),
    )
    assert "gh skill install" not in text
    assert "| `nourl-x` | do x |" in text
    assert "llms.txt" not in text  # no site URL: no published docs to point at


# --------------------------------------------------------------------------
# Draft and write
# --------------------------------------------------------------------------


def _policy(**readme):
    return UserConfig(readme=ReadmePolicy(**readme))


def test_write_adds_first_then_updates_in_place_and_is_idempotent(project, config_dir):
    readme = project / "README.md"
    readme.write_text(
        "# pkg\n\nA package.\n\n## Install\n\npip install pkg\n\n## Usage\n"
    )
    path, outcome = write_section(
        project, user_config=_policy(agentic_aspects="add", agentic_first=True)
    )
    assert (path, outcome) == (readme, "added")
    text = readme.read_text()
    assert text.index(MARKER_START) < text.index("## Install")
    assert "starting at [Install](#install)" in text
    assert "## For AI agents" in text
    assert _statuses(check_readme(project))["section"] == "ok"

    assert (
        write_section(project, user_config=_policy(agentic_first=True))[1]
        == "unchanged"
    )

    # the author moves the section; an update keeps it there
    moved = text.replace(
        text[text.index(MARKER_START) : text.index(MARKER_END) + len(MARKER_END) + 1],
        "",
    )
    moved = (
        moved
        + "\n"
        + text[text.index(MARKER_START) : text.index(MARKER_END) + len(MARKER_END)]
        + "\n"
    )
    readme.write_text(moved)
    _, outcome = write_section(
        project, user_config=_policy(humor=True, agentic_first=True)
    )
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
    section, text, start, end = draft_section(
        project, user_config=_policy(agentic_first=True)
    )
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
    assert {c["kind"] for c in data["checks"]} == {
        "section",
        "skills",
        "subagents",
        "instruction_files",
        "agent_docs",
    }
    assert data["policy"]["user"]["humor"] is False and data["policy"]["project"] == {}
    code, out = run("ai-readme-check", str(project), "--draft")
    assert (
        code == 0
        and out.startswith(MARKER_START)
        and MARKER_START not in (project / "README.md").read_text()
    )
    code, out = run("ai-readme-check", str(project), "--write", "--fail-on", "warn")
    assert code == 0 and out.startswith("added: ") and "ok: every agentic aspect" in out
    code, out = run("ai-readme-check", str(project), "--write", "--format", "json")
    data = json.loads(out)  # a write in JSON mode stays valid JSON
    assert data["write"]["outcome"] == "unchanged" and data["status"] == "ok"
    code, _ = run("ai-readme-check", str(project / "nowhere"))
    assert code == 2
    code, _ = run("ai-readme-check", str(project), "--draft", "--write")
    assert code == 2
    code, _ = run("ai-readme-check", str(project), "--fail-on", "error")
    assert code == 2


def test_cli_reads_the_local_policy(project, config_dir, capsys):
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[readme]\nagentic_aspects = "add"\nhumor = true\nagentic_first = true\n'
    )
    (project / "README.md").write_text("# pkg\n\n## Install\n")
    code = cw.run(
        mk_epythet_parser(),
        ["ai-readme-check", str(project), "--format", "json"],
        convention=CONVENTION,
    )
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["policy"]["readme"] == {
        "agentic_aspects": "add",
        "humor": True,
        "agentic_first": True,
    }
    assert data["policy"]["path"] == str(config_dir / "config.toml")


# --------------------------------------------------------------------------
# Regressions from the adversarial review
# --------------------------------------------------------------------------


def _write_twice(project, text, **readme):
    path = project / "README.md"
    path.write_text(text)
    first = write_section(project, user_config=_policy(**readme))[1]
    second = write_section(project, user_config=_policy(**readme))[1]
    return first, second, path.read_text()


def test_level_is_stable_when_the_readme_has_no_atx_headings(project, config_dir):
    for text in ("Plain intro paragraph.\n", "pkg\n===\n\nsetext title\n", ""):
        first, second, final = _write_twice(project, text, agentic_first=True)
        assert (first, second) == ("added", "unchanged"), text
        assert "\n# For AI agents\n" in final and "## For AI agents" not in final
        # and a third, fourth write still change nothing
        assert (
            write_section(project, user_config=_policy(agentic_first=True))[1]
            == "unchanged"
        )


def test_title_only_readme_keeps_level_two(project, config_dir):
    first, second, final = _write_twice(project, "# pkg\n\nintro\n", agentic_first=True)
    assert (first, second) == ("added", "unchanged")
    assert "\n## For AI agents\n" in final and "### For AI agents" not in final


@pytest.mark.parametrize(
    "text",
    [
        f"# T\n\n## A\n\n{MARKER_START}\nold\nKEEP ME\n\n## B\n\nb\n",
        f"# T\n\n{MARKER_END}\n\n{MARKER_START}\n",
        f"# T\n\n{MARKER_START}\n{MARKER_END}\n{MARKER_START}\n{MARKER_END}\n",
    ],
)
def test_unpaired_or_repeated_markers_are_refused(project, config_dir, text):
    (project / "README.md").write_text(text)
    with pytest.raises(SectionError, match="unpaired or repeated"):
        write_section(project, user_config=_policy())
    assert (project / "README.md").read_text() == text  # nothing eaten
    assert (
        _statuses(check_readme(project))["section"] == "warn"
    )  # not counted as a section


def test_markers_inside_a_code_fence_are_not_the_section(project, config_dir):
    text = f"# T\n\n```\n{MARKER_START}\nexample\n{MARKER_END}\n```\n\n## A\n"
    assert marker_span(text) is None
    first, second, final = _write_twice(project, text, agentic_first=True)
    assert (first, second) == ("added", "unchanged")
    assert final.startswith(text[: text.index("## A")])  # the fenced example survives
    assert final.count(MARKER_START) == 2  # the example plus the real one


def test_crlf_line_endings_are_preserved(project, config_dir):
    path = project / "README.md"
    path.write_bytes(b"# pkg\r\n\r\nintro\r\n\r\n## A\r\n\r\na\r\n")
    assert write_section(project, user_config=_policy(agentic_first=True))[1] == "added"
    raw = path.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")
    assert (
        write_section(project, user_config=_policy(agentic_first=True))[1]
        == "unchanged"
    )


def test_non_utf8_readme_is_refused(project, config_dir):
    (project / "README.md").write_bytes(b"# caf\xe9\n")
    with pytest.raises(SectionError, match="not UTF-8"):
        write_section(project, user_config=_policy())
    assert check_readme(project).readme is not None  # the check still runs


def test_user_template_must_keep_the_markers(project, config_dir):
    init_snippets()
    (snippets_dir() / "agentic-readme-section.md").write_text(
        "{heading} Agents\n\n{name}\n"
    )
    (project / "README.md").write_text("# pkg\n")
    with pytest.raises(SectionError, match="must start with"):
        write_section(project, user_config=_policy())
    assert (project / "README.md").read_text() == "# pkg\n"


@pytest.mark.parametrize(
    "template",
    [
        "{marker_start}\n{nope}\n{marker_end}",
        "{marker_start} { {marker_end}",
        "{marker_start} {} {marker_end}",
    ],
)
def test_broken_user_template_is_an_actionable_error(
    project, config_dir, template, capsys
):
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    init_snippets()
    (snippets_dir() / "agentic-readme-section.md").write_text(template)
    with pytest.raises(SectionError, match="does not format"):
        draft_section(project, user_config=_policy())
    code = cw.run(
        mk_epythet_parser(),
        ["ai-readme-check", str(project), "--draft"],
        convention=CONVENTION,
    )
    assert code == 2
    assert "agentic-readme-section" in capsys.readouterr().err


def test_project_override_pins_the_policy(project, config_dir, capsys):
    """[tool.epythet.readme] wins over the user's config so a committed README is reproducible."""
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        "[readme]\nhumor = false\nagentic_first = false\n"
    )
    (project / "pyproject.toml").write_text(
        (project / "pyproject.toml").read_text()
        + "[tool.epythet.readme]\nhumor = true\nagentic_first = true\n"
    )
    (project / "README.md").write_text("# pkg\n\n## Install\n")
    code = cw.run(
        mk_epythet_parser(),
        ["ai-readme-check", str(project), "--format", "json"],
        convention=CONVENTION,
    )
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["policy"]["readme"] == {
        "agentic_aspects": "warn",
        "humor": True,
        "agentic_first": True,
    }
    assert data["policy"]["user"]["humor"] is False
    assert data["policy"]["project"] == {"humor": True, "agentic_first": True}
    write_section(project)
    text = (project / "README.md").read_text()
    assert text.index(MARKER_START) < text.index("## Install")
    assert "If you are a human" not in text
    (project / "pyproject.toml").write_text(
        (project / "pyproject.toml").read_text() + "humour = 1\n"
    )
    with pytest.raises(Exception, match="humour"):
        check_readme(project)


def test_ai_artifacts_env_switch_drops_the_page_link(project, config_dir, monkeypatch):
    config = load_config(project)
    artifacts = discover_artifacts(project, package_dir=config.package_dir)
    assert "ai-agents.html" in render_section(artifacts, config, policy=ReadmePolicy())
    monkeypatch.setenv("EPYTHET_AI_ARTIFACTS", "0")
    assert "ai-agents.html" not in render_section(
        artifacts, config, policy=ReadmePolicy()
    )


def test_install_line_prefers_a_setup_skill(project, config_dir):
    extra = project / "pkg" / "data" / "skills" / "aaa-first"
    extra.mkdir()
    (extra / "SKILL.md").write_text(
        "---\nname: aaa-first\ndescription: First alphabetically.\n---\nbody\n"
    )
    setup = project / "pkg" / "data" / "skills" / "pkg-setup"
    setup.mkdir()
    (setup / "SKILL.md").write_text(
        "---\nname: pkg-setup\ndescription: Set up pkg.\n---\nbody\n"
    )
    config = load_config(project)
    text = render_section(
        discover_artifacts(project, package_dir=config.package_dir),
        config,
        policy=ReadmePolicy(),
    )
    assert "gh skill install org/pkg pkg-setup --agent claude-code" in text


def test_mentions_are_whole_tokens(project, config_dir):
    (project / "README.md").write_text(
        "# pkg\n\nSee pkg-quickstart-legacy and CLAUDE.mdx\n"
    )
    statuses = _statuses(check_readme(project))
    assert statuses["skills"] == "warn"
    assert statuses["instruction_files"] == "warn"
    (project / "README.md").write_text("# pkg\n\nSee `pkg-quickstart` and CLAUDE.md.\n")
    statuses = _statuses(check_readme(project))
    assert statuses["skills"] == "ok" and statuses["instruction_files"] == "ok"


def test_github_anchor_keeps_underscores():
    assert github_anchor("my_function and my_other") == "my_function-and-my_other"
    assert github_anchor("See [dol](https://x) 2.0") == "see-dol-20"


def test_template_chrome_outside_the_markers_is_refused(project, config_dir):
    init_snippets()
    for template in (
        "{marker_start}\n{heading} A\n{marker_end}\nSee also.\n",
        "Intro\n{marker_start}\n{marker_end}\n",
        "{marker_start} {heading} A\n{marker_end}\n",
        "{marker_end}\n{marker_start}\n",
    ):
        (snippets_dir() / "agentic-readme-section.md").write_text(template)
        with pytest.raises(SectionError, match="must start with"):
            draft_section(project, user_config=_policy())


@pytest.mark.parametrize(
    "template",
    [
        "{marker_start}\n{name.foo}\n{marker_end}",
        "{marker_start}\n{name[x]}\n{marker_end}",
    ],
)
def test_any_format_failure_is_a_section_error(project, config_dir, template):
    init_snippets()
    (snippets_dir() / "agentic-readme-section.md").write_text(template)
    with pytest.raises(SectionError, match="does not format"):
        draft_section(project, user_config=_policy())


def test_broken_pyproject_is_an_error_not_a_silent_fallback(
    project, config_dir, capsys
):
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    (project / "pyproject.toml").write_text(
        (project / "pyproject.toml").read_text()
        + "[tool.epythet]\nbogus = 1\n[tool.epythet.readme]\nhumor = true\n"
    )
    (project / "README.md").write_text("# pkg\n")
    with pytest.raises(Exception, match="bogus"):
        check_readme(project)
    code = cw.run(
        mk_epythet_parser(),
        ["ai-readme-check", str(project), "--write"],
        convention=CONVENTION,
    )
    assert code == 2 and "bogus" in capsys.readouterr().err
    assert (project / "README.md").read_text() == "# pkg\n"
    (project / "pyproject.toml").write_text(
        '[project]\nname = "pkg"\n[tool.epythet.readme]\nhumor = "yes"\n'
    )
    code = cw.run(
        mk_epythet_parser(), ["ai-readme-check", str(project)], convention=CONVENTION
    )
    assert code == 2 and "[tool.epythet.readme] humor" in capsys.readouterr().err


def test_docs_only_project_gets_the_shorter_section(make_project, config_dir):
    """No skills, subagents or instruction files: the section must not claim tooling (#27, item 3)."""
    from epythet.agentic_readme import (
        DOCS_ONLY_SECTION_SNIPPET,
        SECTION_SNIPPET,
        section_snippet_for,
    )

    root = make_project("onlydocs", {"core.py": '"""Core."""\n'})
    (root / "pyproject.toml").write_text(
        '[project]\nname = "onlydocs"\nversion = "0.0.1"\n'
        '[project.urls]\nHomepage = "https://github.com/org/onlydocs"\n'
    )
    config = load_config(root)
    artifacts = discover_artifacts(root, package_dir=config.package_dir)
    assert section_snippet_for(artifacts) == DOCS_ONLY_SECTION_SNIPPET
    text = render_section(artifacts, config, policy=ReadmePolicy(), level=2)
    assert text.startswith(MARKER_START) and text.rstrip().endswith(MARKER_END)
    assert "ships tooling" not in text
    assert "publishes its documentation in forms made for coding agents" in text
    assert "[`llms.txt`](https://org.github.io/onlydocs/llms.txt)" in text
    assert "gh skill install" not in text and "Subagents" not in text
    assert "If you are a human, the rest of this README" in text
    # the docs-only check still passes as a "section" to document, so --write works
    report = check_readme(root, user_config=_policy())
    assert _statuses(report)["agent_docs"] == "warn"


def test_project_with_tooling_keeps_the_full_section(project, config_dir):
    from epythet.agentic_readme import SECTION_SNIPPET, section_snippet_for

    config = load_config(project)
    artifacts = discover_artifacts(project, package_dir=config.package_dir)
    assert section_snippet_for(artifacts) == SECTION_SNIPPET
    assert "ships tooling for coding agents" in render_section(
        artifacts, config, policy=ReadmePolicy()
    )


def test_write_refuses_when_nothing_is_agentic(make_project, config_dir):
    root = make_project("bare", {"m.py": '"""M."""\n'})
    (root / "README.md").write_text("# bare\n")
    with pytest.raises(SectionError, match="nothing agentic"):
        write_section(root, user_config=_policy())
    assert (root / "README.md").read_text() == "# bare\n"
