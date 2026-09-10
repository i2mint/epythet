# epythet.validation.core

The `validate` orchestrator: resolve the package, run the levels, build the report.

This module is the single source of truth every surface calls. It returns a
[`Report`](epythet.validation.model.html.md#epythet.validation.model.Report) (JSON-able via `to_dict`), never
prints and never exits, so the CLI, a future MCP tool or an HTTP endpoint all
wrap the same function.

Seams (one keyword argument each, as in decision D8):

- `backend=` — the build backend for level 1; defaults to
  [`SphinxBackend`](epythet.validation.build.html.md#epythet.validation.build.SphinxBackend). Levels 0 and 0.5 never
  > touch it.
- `ledger=` — the rule catalog; `None` is the bundled ledger, a directory
  is a package-local overlay.

Level 2 (render) reuses the backend through its `render` method (a
[`RenderBackend`](epythet.validation.build.html.md#epythet.validation.build.RenderBackend)) and level 3 (review) reads
what level 2 rendered, so a tier-4 run builds exactly once.

### Functions

| [`resolve_package`](#epythet.validation.core.resolve_package)(package)                    | Turn `<package_dir_or_import_name>` into a [`ResolvedPackage`](#epythet.validation.core.ResolvedPackage).   |
|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| [`validate`](#epythet.validation.core.validate)(package, \*[, level, levels, ...]) | Validate a package's documentation and return a `Report`.                                                      |

### Classes

| [`ResolvedPackage`](#epythet.validation.core.ResolvedPackage)(name, package_dir, project_dir)   | Where the package's source lives and which project it belongs to.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|

### *class* epythet.validation.core.ResolvedPackage(name, package_dir, project_dir, version=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Where the package’s source lives and which project it belongs to.

### epythet.validation.core.resolve_package(package)

Turn `<package_dir_or_import_name>` into a [`ResolvedPackage`](#epythet.validation.core.ResolvedPackage).

Accepts a project root (contains `pyproject.toml`/`setup.cfg`), a
package directory (contains `__init__.py`) or an importable name.

* **Return type:**
  [`ResolvedPackage`](#epythet.validation.core.ResolvedPackage)

### epythet.validation.core.validate(package, , level=1, levels=None, ledger=None, backend=None, fail_on='error', napoleon=True, style='google', ignore=(), observe=True, observations_path=None, linters=True, snapshot=False, update_snapshots=False, snapshot_dir=None, render_dir=None, review_pages='changed', review_sample=8, screenshots=False, packet_dir=None, review_reply=None)

Validate a package’s documentation and return a `Report`.

* **Parameters:**
  * **package** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike)) – A project root, a package directory, or an importable name.
  * **level** ([`int`](https://docs.python.org/3/library/functions.html#int)) – The CLI tier: `0` lint only, `1` lint + parse (default),
    `2` adds the Sphinx build, `3` the rendered-output checks,
    `4` the review packet.
  * **levels** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`float`](https://docs.python.org/3/library/functions.html#float)]]) – An explicit set of levels (`[0.5]` for a parse-only sweep);
    overrides `level` when given.
  * **ledger** (`Ledger` | [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – `None` for the bundled rules, or a directory overlay.
  * **backend** – The build backend for level 1 (default: `SphinxBackend()`).
  * **fail_on** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Severity threshold recorded on the report for exit codes.
  * **napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Pre-process Google/NumPy sections the way the fleet’s
    `conf.py` does. Set `False` for a package built without napoleon.
  * **style** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Docstring convention passed to ruff and pydoclint.
  * **ignore** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – Path substrings to skip, as `epythet quickstart --ignore`.
  * **observe** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Append findings to the observations JSONL (outside the repo).
  * **observations_path** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Override the observations file (tests use this).
  * **linters** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 0: shell out to ruff and pydoclint (`False` keeps the
    coverage detectors only; the fleet sweep uses it).
  * **snapshot** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 2: diff the `-b text` render against the stored snapshots.
  * **update_snapshots** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 2: re-baseline the snapshots instead of diffing.
  * **snapshot_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Where snapshots live (default `<docsrc>/_snapshots/text`).
  * **render_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Keep level 2’s rendered output here instead of a temp dir.
  * **review_pages** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Level 3: `changed` (against the snapshot, else a
    sample), `sample` or `all` pages into the packet.
  * **review_sample** ([`int`](https://docs.python.org/3/library/functions.html#int)) – How many pages `sample` takes.
  * **screenshots** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Level 3: add Playwright screenshots when it is installed.
  * **packet_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Level 3: write the packet here instead of the user data dir.
  * **review_reply** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Level 3: a `review.json` to ingest as level-3 findings.
* **Return type:**
  [`Report`](epythet.validation.model.html.md#epythet.validation.model.Report)
