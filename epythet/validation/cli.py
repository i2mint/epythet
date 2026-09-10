"""The ``epythet validate`` command: the CLI adapter over :func:`epythet.validation.validate`.

This is the only place that prints, and the only place that turns a report
into a process exit code. ``epythet.cli`` appends :func:`validate` to its
command list; ``python -m epythet.validation`` dispatches it on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cw

from epythet.validation.model import IMPLEMENTED_TIERS, SEVERITIES
from epythet.validation.lint import STYLES
from epythet.validation.render import FORMATS


def validate(
    package: str,
    *,
    level: int = 1,
    format: str = "table",
    fail_on: str = "error",
    ledger: str | None = None,
    style: str = "google",
    no_napoleon: bool = False,
    ignore: list[str] | None = None,
    docsrc: str | None = None,
    no_observe: bool = False,
    no_linters: bool = False,
    max_per_rule: int = 10,
    output: str | None = None,
    snapshot: bool = False,
    update_snapshots: bool = False,
    snapshot_dir: str | None = None,
    render_dir: str | None = None,
    review_pages: str = "changed",
    review_sample: int = 8,
    screenshots: bool = False,
    packet_dir: str | None = None,
    review_reply: str | None = None,
    fail_on_review: bool = False,
) -> None:
    """Check a package's docstrings for rendering artifacts and build problems.

    Exit codes: 0 clean; 10/11/12/13 findings at or above --fail-on at level
    0 (lint) / 0.5 (parse) / 1 (build) / 2 (render); 14 review findings, only
    with --fail-on-review; 20 ledger integrity failure; 1 internal error.

    :param package: Project root, package directory, or importable package name.
    :param level: 0 = lint (ruff D, pydoclint); 1 = lint + parse every docstring's
        doctree (default, no build needed); 2 = also run the Sphinx build;
        3 = also read the rendered XML/HTML/text; 4 = also write a review packet.
    :param format: table (human), json (full report), or jsonl (one finding per line).
    :param fail_on: Severity that makes the exit code non-zero: error, warning, or info.
    :param ledger: Directory of extra rule YAML files overlaid on the bundled ledger.
    :param style: Docstring convention for the linters: google, numpy, or sphinx.
    :param no_napoleon: Parse docstrings without napoleon's Google/NumPy pre-processing.
    :param ignore: Skip files whose path contains this string (repeat -i for several).
    :param docsrc: Sphinx source directory for level 2 (default: <project>/docsrc).
    :param no_observe: Do not append findings to the ledger's observations file.
    :param no_linters: Level 0 without ruff and pydoclint (coverage detectors only).
    :param max_per_rule: How many findings to show per rule in the table.
    :param output: Write the report to this file instead of stdout.
    :param snapshot: Level 3: diff the text render against docsrc/_snapshots/text.
    :param update_snapshots: Level 3: rewrite the text snapshots from this render.
    :param snapshot_dir: Where the text snapshots live (default docsrc/_snapshots/text).
    :param render_dir: Keep the rendered html/text/xml here instead of a temp dir.
    :param review_pages: Level 4: which pages go in the packet: changed, sample, or all.
    :param review_sample: Level 4: how many pages a sample packet holds.
    :param screenshots: Level 4: add Playwright screenshots to the packet if installed.
    :param packet_dir: Level 4: write the packet here (default: the user data dir).
    :param review_reply: Level 4: a review.json written by a reviewer, to ingest.
    :param fail_on_review: Exit 14 when the review reply reported findings.
    """
    from epythet.validation.build import SphinxBackend
    from epythet.validation.core import validate as _validate
    from epythet.validation.ledger import LedgerError
    from epythet.validation.render import render
    from epythet.validation.review import PAGE_MODES, ReplyError

    if level not in IMPLEMENTED_TIERS:
        raise cw.CommandError(
            f"--level must be one of {list(IMPLEMENTED_TIERS)}", code=2
        )
    if format not in FORMATS:
        raise cw.CommandError(f"--format must be one of {list(FORMATS)}", code=2)
    if fail_on not in SEVERITIES:
        raise cw.CommandError(f"--fail-on must be one of {list(SEVERITIES)}", code=2)
    if style not in STYLES:
        raise cw.CommandError(f"--style must be one of {list(STYLES)}", code=2)
    if review_pages not in PAGE_MODES:
        raise cw.CommandError(
            f"--review-pages must be one of {list(PAGE_MODES)}", code=2
        )
    try:
        report = _validate(
            package,
            level=level,
            ledger=ledger,
            backend=SphinxBackend(docsrc=docsrc),
            fail_on=fail_on,
            napoleon=not no_napoleon,
            style=style,
            ignore=ignore or (),
            observe=not no_observe,
            linters=not no_linters,
            snapshot=snapshot,
            update_snapshots=update_snapshots,
            snapshot_dir=snapshot_dir,
            render_dir=render_dir,
            review_pages=review_pages,
            review_sample=review_sample,
            screenshots=screenshots,
            packet_dir=packet_dir,
            review_reply=review_reply,
        )
    except LedgerError as e:
        raise cw.CommandError(f"ledger integrity failure: {e}", code=20) from e
    except (FileNotFoundError, ReplyError) as e:
        raise cw.CommandError(str(e), code=2) from e
    text = render(
        report, format, **({"max_per_rule": max_per_rule} if format == "table" else {})
    )
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    code = report.exit_code(fail_on, fail_on_review=fail_on_review)
    if code:
        failing = ", ".join(
            f"{lv:g}"
            for lv in report.failing_levels(fail_on, fail_on_review=fail_on_review)
        )
        raise cw.CommandError(
            f"findings at or above {fail_on} at level(s) {failing} (exit {code})",
            code=code,
        )


COMMANDS = [validate]
