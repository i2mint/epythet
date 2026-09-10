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

Levels 2 (render) and 3 (review) are declared in the model and reserved for
WP3; asking for them raises [`NotImplementedError`](https://docs.python.org/3/library/exceptions.html#NotImplementedError) with a pointer.

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

### epythet.validation.core.validate(package, , level=1, levels=None, ledger=None, backend=None, fail_on='error', napoleon=True, style='google', ignore=(), observe=True, observations_path=None)

Validate a package’s documentation and return a `Report`.

* **Parameters:**
  * **package** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike)) – A project root, a package directory, or an importable name.
  * **level** ([`int`](https://docs.python.org/3/library/functions.html#int)) – The CLI tier: `0` lint only, `1` lint + parse (default),
    `2` adds the Sphinx build. Tiers 3 and 4 belong to WP3.
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
* **Return type:**
  [`Report`](epythet.validation.model.html.md#epythet.validation.model.Report)
