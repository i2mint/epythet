# epythet.validation.cli

The `epythet validate` command: the CLI adapter over `epythet.validation.validate()`.

This is the only place that prints, and the only place that turns a report
into a process exit code. `epythet.cli` appends [`validate()`](#epythet.validation.cli.validate) to its
command list; `python -m epythet.validation` dispatches it on its own.

### Functions

| [`validate`](#epythet.validation.cli.validate)(package, \*[, level, format, ...])   | Check a package's docstrings for rendering artifacts and build problems.   |
|------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|

### epythet.validation.cli.validate(package, , level=1, format='table', fail_on='error', ledger=None, style='google', no_napoleon=False, ignore=None, docsrc=None, no_observe=False, no_linters=False, max_per_rule=10, output=None, snapshot=False, update_snapshots=False, snapshot_dir=None, render_dir=None, review_pages='changed', review_sample=8, screenshots=False, packet_dir=None, review_reply=None, fail_on_review=False)

Check a package’s docstrings for rendering artifacts and build problems.

Exit codes: 0 clean; 10/11/12/13 findings at or above –fail-on at level
0 (lint) / 0.5 (parse) / 1 (build) / 2 (render); 14 review findings, only
with –fail-on-review; 20 ledger integrity failure; 1 internal error.

* **Parameters:**
  * **package** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Project root, package directory, or importable package name.
  * **level** ([`int`](https://docs.python.org/3/library/functions.html#int)) – 0 = lint (ruff D, pydoclint); 1 = lint + parse every docstring’s
    doctree (default, no build needed); 2 = also run the Sphinx build;
    3 = also read the rendered XML/HTML/text; 4 = also write a review packet.
  * **format** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – table (human), json (full report), or jsonl (one finding per line).
  * **fail_on** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Severity that makes the exit code non-zero: error, warning, or info.
  * **ledger** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Directory of extra rule YAML files overlaid on the bundled ledger.
  * **style** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Docstring convention for the linters: google, numpy, or sphinx.
  * **no_napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Parse docstrings without napoleon’s Google/NumPy pre-processing.
  * **ignore** ([`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)) – Skip files whose path contains this string (repeat -i for several).
  * **docsrc** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Sphinx source directory for level 2 (default: <project>/docsrc).
  * **no_observe** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Do not append findings to the ledger’s observations file.
  * **no_linters** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 0 without ruff and pydoclint (coverage detectors only).
  * **max_per_rule** ([`int`](https://docs.python.org/3/library/functions.html#int)) – How many findings to show per rule in the table.
  * **output** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Write the report to this file instead of stdout.
  * **snapshot** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 3: diff the text render against docsrc/_snapshots/text.
  * **update_snapshots** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 3: rewrite the text snapshots from this render.
  * **snapshot_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Where the text snapshots live (default docsrc/_snapshots/text).
  * **render_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Keep the rendered html/text/xml here instead of a temp dir.
  * **review_pages** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Level 4: which pages go in the packet: changed, sample, or all.
  * **review_sample** ([`int`](https://docs.python.org/3/library/functions.html#int)) – Level 4: how many pages a sample packet holds.
  * **screenshots** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 4: add Playwright screenshots to the packet if installed.
  * **packet_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Level 4: write the packet here (default: the user data dir).
  * **review_reply** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Level 4: a review.json written by a reviewer, to ingest.
  * **fail_on_review** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Exit 14 when the review reply reported findings.
* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)
