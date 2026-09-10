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
    max_per_rule: int = 10,
    output: str | None = None,
) -> None:
    """Check a package's docstrings for rendering artifacts and build problems.

    Exit codes: 0 clean; 10/11/12 findings at or above --fail-on at level
    0 (lint) / 0.5 (parse) / 1 (build); 20 ledger integrity failure; 1 internal error.

    :param package: Project root, package directory, or importable package name.
    :param level: 0 = lint (ruff D, pydoclint); 1 = lint + parse every docstring's
        doctree (default, no build needed); 2 = also run the Sphinx build.
    :param format: table (human), json (full report), or jsonl (one finding per line).
    :param fail_on: Severity that makes the exit code non-zero: error, warning, or info.
    :param ledger: Directory of extra rule YAML files overlaid on the bundled ledger.
    :param style: Docstring convention for the linters: google, numpy, or sphinx.
    :param no_napoleon: Parse docstrings without napoleon's Google/NumPy pre-processing.
    :param ignore: Skip files whose path contains any of these strings.
    :param docsrc: Sphinx source directory for level 2 (default: <project>/docsrc).
    :param no_observe: Do not append findings to the ledger's observations file.
    :param max_per_rule: How many findings to show per rule in the table.
    :param output: Write the report to this file instead of stdout.
    """
    from epythet.validation.build import SphinxBackend
    from epythet.validation.core import validate as _validate
    from epythet.validation.ledger import LedgerError
    from epythet.validation.render import render

    if level not in IMPLEMENTED_TIERS:
        raise cw.CommandError(
            f"--level must be one of {list(IMPLEMENTED_TIERS)}", code=2
        )
    if format not in FORMATS:
        raise cw.CommandError(f"--format must be one of {list(FORMATS)}", code=2)
    if fail_on not in SEVERITIES:
        raise cw.CommandError(f"--fail-on must be one of {list(SEVERITIES)}", code=2)
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
        )
    except LedgerError as e:
        raise cw.CommandError(f"ledger integrity failure: {e}", code=20) from e
    except FileNotFoundError as e:
        raise cw.CommandError(str(e), code=2) from e
    text = render(
        report, format, **({"max_per_rule": max_per_rule} if format == "table" else {})
    )
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    code = report.exit_code(fail_on)
    if code:
        failing = ", ".join(f"{lv:g}" for lv in report.failing_levels(fail_on))
        raise cw.CommandError(
            f"findings at or above {fail_on} at level(s) {failing} (exit {code})",
            code=code,
        )


COMMANDS = [validate]
