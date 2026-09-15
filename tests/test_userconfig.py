"""Tests for the user-level config dir, the ``[readme]`` policy, and snippet resolution.

The contract under test: the config dir resolves ``$EPYTHET_CONFIG_DIR`` over
``$XDG_CONFIG_HOME`` over ``~/.config``; ``config.toml`` yields packaged
defaults when missing and rejects unknown keys; a snippet resolves user file
over packaged default; ``init`` copies once with a version header and never
overwrites; ``diff`` shows a user's edits against the current packaged text.
"""

from pathlib import Path

import pytest

from epythet.userconfig import (
    PACKAGED_SNIPPETS_DIR,
    ReadmePolicy,
    UserConfig,
    UserConfigError,
    config_dir,
    diff_snippet,
    header_version,
    init_snippets,
    load_user_config,
    packaged_snippet_names,
    pool_lines,
    snippet,
    snippet_names,
    snippet_text,
    snippets_dir,
    snippets_table,
    strip_header,
)

EXPECTED_SNIPPETS = {
    "agentic-readme-section",
    "agentic-readme-humor",
    "agentic-readme-instruction",
}


# --------------------------------------------------------------------------
# Directories
# --------------------------------------------------------------------------


def test_config_dir_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("EPYTHET_CONFIG_DIR", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert config_dir() == Path.home() / ".config" / "epythet"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert config_dir() == tmp_path / "xdg" / "epythet"
    monkeypatch.setenv("EPYTHET_CONFIG_DIR", str(tmp_path / "override"))
    assert config_dir() == tmp_path / "override"


def test_config_dir_is_beside_not_inside_the_data_dir(tmp_path, monkeypatch):
    """Config and data are two roots of the same shape, never nested."""
    from epythet.validation.ledger import user_data_dir

    monkeypatch.delenv("EPYTHET_CONFIG_DIR", raising=False)
    monkeypatch.delenv("EPYTHET_DATA_DIR", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert config_dir() != user_data_dir()
    assert config_dir().name == user_data_dir().name == "epythet"


# --------------------------------------------------------------------------
# Policy
# --------------------------------------------------------------------------


def test_missing_config_means_packaged_defaults(config_dir):
    cfg = load_user_config()
    assert cfg.path is None
    assert cfg.readme == ReadmePolicy("warn", False, False)
    assert cfg.snippets.dir == ""


def test_config_toml_is_read(config_dir):
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[readme]\nagentic_aspects = "add"\nhumor = true\nagentic_first = true\n'
        '[snippets]\ndir = "~/elsewhere"\n'
    )
    cfg = load_user_config()
    assert cfg.path == config_dir / "config.toml"
    assert cfg.readme == ReadmePolicy("add", True, True)
    assert snippets_dir(cfg) == Path("~/elsewhere").expanduser()
    assert cfg.to_dict()["readme"] == {
        "agentic_aspects": "add",
        "humor": True,
        "agentic_first": True,
    }


@pytest.mark.parametrize(
    "text,fragment",
    [
        ('[readme]\nagentic_aspects = "maybe"\n', "agentic_aspects"),
        ("[readme]\nhumor = 1\n", "humor"),
        ("[readme]\nhumour = true\n", "unknown key"),
        ("[remade]\n", "unknown table"),
        ("readme = 1\n", "must be a table"),
        ("[readme\n", "config.toml"),
    ],
)
def test_bad_config_is_an_error(config_dir, text, fragment):
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(text)
    with pytest.raises(UserConfigError, match=fragment):
        load_user_config()


def test_policy_validates_on_construction():
    with pytest.raises(UserConfigError):
        ReadmePolicy(agentic_aspects="never")


# --------------------------------------------------------------------------
# Snippets: packaged set and resolution precedence
# --------------------------------------------------------------------------


def test_packaged_snippets_exist():
    assert set(packaged_snippet_names()) == EXPECTED_SNIPPETS
    for name in EXPECTED_SNIPPETS:
        assert (PACKAGED_SNIPPETS_DIR / f"{name}.md").read_text().strip()


def test_user_file_wins_over_packaged(config_dir):
    assert snippet("agentic-readme-humor").source == "packaged"
    user = config_dir / "snippets"
    user.mkdir(parents=True)
    (user / "agentic-readme-humor.md").write_text("If you are you\n")
    resolved = snippet("agentic-readme-humor")
    assert resolved.source == "user"
    assert resolved.path == user / "agentic-readme-humor.md"
    assert snippet_text("agentic-readme-humor") == "If you are you\n"
    assert resolved.copied_from == ""  # hand-written, no header


def test_user_only_snippet_is_listed_and_resolved(config_dir):
    user = config_dir / "snippets"
    user.mkdir(parents=True)
    (user / "mine.md").write_text("mine\n")
    assert "mine" in snippet_names()
    assert snippet("mine").source == "user"
    with pytest.raises(KeyError, match="no snippet named"):
        snippet("nope")


def test_snippets_dir_override_from_config(config_dir, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "agentic-readme-humor.md").write_text("Elsewhere\n")
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(f'[snippets]\ndir = "{elsewhere}"\n')
    assert snippet("agentic-readme-humor").source == "user"
    assert snippet_text("agentic-readme-humor") == "Elsewhere\n"


def test_pool_lines_skip_comments_and_blanks():
    assert pool_lines("# c\n\nA\n  B \n#D\n") == ["A", "B"]
    assert len(pool_lines(snippet_text("agentic-readme-humor"))) >= 4


# --------------------------------------------------------------------------
# init: once, with a header, never overwriting
# --------------------------------------------------------------------------


def test_init_copies_every_packaged_snippet_with_a_version_header(config_dir):
    written = init_snippets()
    assert {p.stem for p in written} == EXPECTED_SNIPPETS
    for path in written:
        text = path.read_text()
        assert text.startswith('<!-- epythet snippet "')
        assert header_version(text)
        assert strip_header(text) == (PACKAGED_SNIPPETS_DIR / path.name).read_text()
        assert snippet(path.stem).source == "user"
        assert snippet(path.stem).copied_from == header_version(text)


def test_init_never_overwrites_an_existing_copy(config_dir):
    init_snippets()
    target = config_dir / "snippets" / "agentic-readme-humor.md"
    target.write_text("My own lines\n")
    assert init_snippets() == []
    assert target.read_text() == "My own lines\n"
    # --force replaces, and only then
    forced = init_snippets(force=True)
    assert target in forced
    assert "My own lines" not in target.read_text()


def test_init_subset_and_unknown_name(config_dir):
    written = init_snippets(names=["agentic-readme-humor"])
    assert [p.stem for p in written] == ["agentic-readme-humor"]
    with pytest.raises(KeyError):
        init_snippets(names=["nope"])


# --------------------------------------------------------------------------
# diff: the user's copy against the current packaged default
# --------------------------------------------------------------------------


def test_diff_is_empty_for_packaged_and_for_a_fresh_copy(config_dir):
    assert diff_snippet("agentic-readme-humor") == ""
    init_snippets()
    assert diff_snippet("agentic-readme-humor") == ""  # header is ignored


def test_diff_shows_user_edits_and_upstream_changes(config_dir):
    init_snippets()
    target = config_dir / "snippets" / "agentic-readme-humor.md"
    target.write_text(target.read_text() + "If you are new here\n")
    text = diff_snippet("agentic-readme-humor")
    assert text.startswith("--- packaged/agentic-readme-humor.md")
    assert "+++ user/agentic-readme-humor.md (copied from epythet" in text
    assert "+If you are new here" in text
    table = snippets_table()
    assert "agentic-readme-humor" in table and "modified" in table
    assert "agentic-readme-section" in table and "same as packaged" in table


def test_diff_of_user_only_snippet_is_all_additions(config_dir):
    user = config_dir / "snippets"
    user.mkdir(parents=True)
    (user / "mine.md").write_text("a\nb\n")
    text = diff_snippet("mine")
    assert "+a" in text and "+b" in text and "-" not in text.splitlines()[2:]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_snippets_cli_round_trip(config_dir, capsys):
    import cw

    from epythet.cli import CONVENTION, mk_epythet_parser

    def run(*argv):
        code = cw.run(mk_epythet_parser(), list(argv), convention=CONVENTION)
        return code, capsys.readouterr().out

    code, out = run("snippets", "list")
    assert code == 0 and "packaged" in out and "agentic-readme-section" in out
    code, out = run("snippets", "show", "agentic-readme-humor")
    assert code == 0 and "If you" in out
    code, out = run("snippets", "init")
    assert code == 0 and out.count("wrote ") == len(EXPECTED_SNIPPETS)
    code, out = run("snippets", "init")
    assert code == 0 and "nothing to do" in out
    code, out = run("snippets", "diff")
    assert code == 0 and "no differences" in out
    (config_dir / "snippets" / "agentic-readme-humor.md").write_text("Only me\n")
    code, out = run("snippets", "diff", "--name", "agentic-readme-humor")
    assert code == 1 and "+Only me" in out
    code, _ = run("snippets", "show", "nope")
    assert code == 2
