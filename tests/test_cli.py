"""Characterization tests for epythet's command line interface.

These tests exist because ``epythet``'s CLI is consumed by
``actions/publish-github-pages/action.yml``, which every fleet repo's docs job
runs. The grammar recorded here is the grammar that action depends on, so these
are parity tests first and unit tests second: the expected values below were
captured from the previous ``argh`` implementation *before* the migration to
``cw`` and must not be "updated" to match new behaviour without a deliberate
decision to change the published CLI.

The single most load-bearing case is :func:`test_ignore_with_zero_values`.

v2 (0.2.0) deliberately changed two things, and the goldens were updated with
that decision: ``make-docsrc`` gained ``--ignore``, and ``quickstart`` now
calls one orchestrator (``load_config`` -> ``scaffold`` -> ``build``) instead of
the three legacy functions.
"""

import subprocess
import sys
import textwrap

import pytest

import cw
from epythet.cli import COMMANDS, mk_epythet_parser


def _parser():
    """The real CLI parser, with ``prog`` pinned so goldens are OS-independent.

    Pinning ``prog`` keeps Windows' ``epythet.exe`` out of the recorded text.
    ``mk_epythet_parser`` is what the console script builds: the flat
    ``COMMANDS`` plus the tool commands and the ``ledger`` group.
    """
    return mk_epythet_parser(prog="epythet")


def _usage(argv):
    """The ``usage:`` line for ``argv``, whitespace-collapsed.

    argparse wraps usage to the terminal width, so collapsing whitespace is what
    makes the golden independent of ``COLUMNS``. The usage line names every
    option a parser has, so a lost flag, a lost short flag, or a changed
    ``nargs`` all show up here.
    """
    parser = _parser()
    if argv:
        # Reach the subparser argparse would dispatch to.
        subparsers = next(
            a for a in parser._actions if hasattr(a, "choices") and a.choices
        )
        parser = subparsers.choices[argv[0]]
    return " ".join(parser.format_usage().split())


# --------------------------------------------------------------------------
# Tier 2: the usage line of every command. Recorded from argh.
# --------------------------------------------------------------------------

EXPECTED_USAGE = {
    (): (
        "usage: epythet [-h] "
        "{make-docsrc,make-autodocs,make,quickstart,check-pages,configure-pages,validate,"
        "ai-artifacts,repair,migrate-style,sweep,ledger} ..."
    ),
    (
        "make-docsrc",
    ): "usage: epythet make-docsrc [-h] [-v] [-i [IGNORE ...]] project-dir",
    ("make-autodocs",): (
        "usage: epythet make-autodocs [-h] [-o OUTPUT_DIRNAME] [-s] "
        "[-d DOCSRC_DIR] [-i [IGNORE ...]] project-dir"
    ),
    ("make",): "usage: epythet make [-h] project-dir [make-args ...]",
    ("quickstart",): "usage: epythet quickstart [-h] [-i [IGNORE ...]] project-dir",
    ("check-pages",): "usage: epythet check-pages [-h] [-n] repo",
    ("configure-pages",): (
        "usage: epythet configure-pages [-h] [-b BRANCH] [-p PATH] repo"
    ),
    ("ai-artifacts",): "usage: epythet ai-artifacts [-h] [-f FORMAT] project-dir",
    # v2 (0.2.3): the source-editing and fleet commands, and the ledger group.
    ("repair",): (
        "usage: epythet repair [-h] [-w] [-f FENCE_STYLE] [-i [IGNORE ...]] [-l LEDGER] "
        "[--no-napoleon] [--no-doctests] [-a APPLIER] [-q] path"
    ),
    ("migrate-style",): (
        "usage: epythet migrate-style [-h] [-t TO] [-w] [-i [IGNORE ...]] [-l LEDGER] "
        "[--no-napoleon] [--no-doctests] [-a APPLIER] [-q] path"
    ),
    ("sweep",): (
        "usage: epythet sweep [-h] [-m MANIFEST] [-p] [--linters] [-i [IGNORE ...]] "
        "[--ledger LEDGER] [--no-napoleon] [--no-observe] [--limit LIMIT] [-f FORMAT] "
        "[-t TOP] [-o OUTPUT] [-q] [dirs ...]"
    ),
    ("ledger",): "usage: epythet ledger [-h] {propose} ...",
}


@pytest.mark.parametrize("argv,expected", sorted(EXPECTED_USAGE.items()))
def test_usage_line_is_unchanged(argv, expected):
    """Every command's grammar matches what argh published."""
    assert _usage(list(argv)) == expected


def test_command_set_and_order():
    """The commands, in the order ``--help`` lists them."""
    parser = _parser()
    subparsers = next(a for a in parser._actions if hasattr(a, "choices") and a.choices)
    assert list(subparsers.choices) == [
        "make-docsrc",
        "make-autodocs",
        "make",
        "quickstart",
        "check-pages",
        "configure-pages",
        "validate",
        "ai-artifacts",
        "repair",
        "migrate-style",
        "sweep",
        "ledger",
    ]


# --------------------------------------------------------------------------
# The blast-radius case.
# --------------------------------------------------------------------------
#
# actions/publish-github-pages/action.yml runs:
#
#     epythet quickstart . --ignore ${{ inputs.ignore }}
#
# `inputs.ignore` has no default, so when a caller does not set it the shell
# sees `epythet quickstart . --ignore` with ZERO values after the flag. That
# parses only because `ignore` takes nargs='*'. If it ever stops yielding [],
# every fleet repo's docs job exits 2.


@pytest.mark.parametrize("flag", ["--ignore", "-i"])
def test_ignore_with_zero_values(flag):
    """``--ignore`` with no values parses, and yields an empty list.

    This is the exact shape the published GitHub Action emits when its
    ``ignore`` input is unset. It must never raise SystemExit.
    """
    ns = _parser().parse_args(["quickstart", ".", flag])
    assert ns.ignore == []


def test_ignore_absent_is_none():
    """Omitting the flag entirely leaves the parameter default in place."""
    ns = _parser().parse_args(["quickstart", "."])
    assert ns.ignore is None


def test_ignore_with_several_values():
    ns = _parser().parse_args(["quickstart", ".", "--ignore", "tests/", "scrap/"])
    assert ns.ignore == ["tests/", "scrap/"]


def test_make_autodocs_ignore_with_zero_values():
    """``make-autodocs`` carries the same nargs='*' contract as ``quickstart``."""
    ns = _parser().parse_args(["make-autodocs", ".", "--ignore"])
    assert ns.ignore == []


def test_action_invocation_reaches_the_build_with_default_ignore():
    """End-to-end: the action's argv reaches the orchestrator with ``ignore=[]``.

    An empty ``ignore`` means "use the configured default", so no override is
    forwarded to the build. Runs the real dispatch path in a subprocess with the
    three side-effecting steps replaced by recorders, so no Sphinx build happens.
    """
    program = textwrap.dedent(
        """
        import sys, json
        import epythet.cli as cli

        calls = {}
        cli.load_config = lambda d, **k: calls.__setitem__('load_config', (d, k)) or 'CFG'
        cli.scaffold = lambda cfg, **k: calls.__setitem__('scaffold', (cfg, k))
        cli.build = lambda cfg, target, **k: calls.__setitem__('build', (cfg, target, k))

        sys.argv = ['epythet', 'quickstart', '.', '--ignore']
        try:
            cli.epythet_cli()
        except SystemExit as e:
            assert not e.code, f'exited {e.code}'
        print(json.dumps(calls))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    import json

    calls = json.loads(result.stdout)
    assert calls["load_config"] == [".", {}]
    assert calls["scaffold"] == ["CFG", {"verbose": True}]
    assert calls["build"] == ["CFG", "html", {"overrides": {}}]


def test_explicit_ignore_is_forwarded_as_an_override():
    program = textwrap.dedent(
        """
        import sys, json
        import epythet.cli as cli

        calls = {}
        cli.load_config = lambda d, **k: calls.__setitem__('load_config', (d, k)) or 'CFG'
        cli.scaffold = lambda cfg, **k: None
        cli.build = lambda cfg, target, **k: calls.__setitem__('build', (cfg, target, k))
        sys.argv = ['epythet', 'quickstart', '.', '--ignore', 'tests/', 'scrap/']
        try:
            cli.epythet_cli()
        except SystemExit as e:
            assert not e.code
        print(json.dumps(calls))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    import json

    calls = json.loads(result.stdout)
    assert calls["load_config"] == [".", {"ignore": ["tests/", "scrap/"]}]
    assert calls["build"] == [
        "CFG",
        "html",
        {"overrides": {"ignore": ["tests/", "scrap/"]}},
    ]


# --------------------------------------------------------------------------
# Other grammar shapes worth pinning.
# --------------------------------------------------------------------------


def test_make_is_variadic():
    """``epythet make . html`` -- ``make(project_dir, *make_args)``."""
    ns = _parser().parse_args(["make", ".", "html"])
    assert getattr(ns, "make-args") == ["html"]


def test_make_accepts_no_make_args():
    ns = _parser().parse_args(["make", "."])
    assert getattr(ns, "make-args") == []


def test_make_accepts_several_make_args():
    ns = _parser().parse_args(["make", ".", "html", "doctest"])
    assert getattr(ns, "make-args") == ["html", "doctest"]


def test_short_flags_are_preserved():
    """argh minted a short flag for every keyword-only parameter."""
    ns = _parser().parse_args(
        ["make-autodocs", ".", "-o", "docs", "-s", "-d", "src", "-i", "a"]
    )
    assert (ns.output_dirname, ns.skip_existing, ns.docsrc_dir, ns.ignore) == (
        "docs",
        False,
        "src",
        ["a"],
    )


def test_boolean_flag_inverts_a_true_default():
    """``make_docsrc(verbose=True)`` -- passing ``-v`` turns it off, as in argh."""
    assert _parser().parse_args(["make-docsrc", "."]).verbose is True
    assert _parser().parse_args(["make-docsrc", ".", "-v"]).verbose is False


# --------------------------------------------------------------------------
# Exit codes. argh exits by itself; cw.dispatch RETURNS a code, so the entry
# point must `raise SystemExit(...)`. Nothing else in this file would notice.
# --------------------------------------------------------------------------


def _run_cli(*args):
    program = (
        "import sys; sys.argv[0] = 'epythet'; "
        "from epythet.cli import epythet_cli; epythet_cli()"
    )
    return subprocess.run(
        [sys.executable, "-c", program, *args],
        capture_output=True,
        text=True,
        timeout=60,
        env={"COLUMNS": "100", "PYTHONUTF8": "1", **_clean_env()},
    )


def _clean_env():
    import os

    return {k: v for k, v in os.environ.items() if k not in ("COLUMNS", "PYTHONUTF8")}


def test_no_arguments_prints_usage_and_exits_zero():
    """argh's behaviour, which plain argparse does not have: usage, stdout, rc 0."""
    result = _run_cli()
    assert result.returncode == 0
    assert result.stdout.startswith("usage: epythet")
    assert result.stderr == ""


def test_help_exits_zero_and_lists_every_command():
    result = _run_cli("--help")
    assert result.returncode == 0
    for name in (
        "make-docsrc",
        "make-autodocs",
        "make",
        "quickstart",
        "check-pages",
        "configure-pages",
    ):
        assert name in result.stdout


def test_unknown_command_exits_two():
    """The non-zero-exit vector: proves the entry point propagates the code."""
    result = _run_cli("no-such-command")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_missing_required_argument_exits_two():
    result = _run_cli("quickstart")
    assert result.returncode == 2
