# epythet.sweep

`epythet sweep`: validate many packages read-only and rank the queue.

The fleet has some two hundred packages and one question about each rule:
how often does it fire, and where? Severities in the ledger are decided by
that distribution, not by intuition (decision D9). The sweep runs
`epythet.validation.validate()` at level 0 (the coverage detectors, no
linters unless asked) and level 0.5 (the doctree of every docstring) over
each package, never writes into any of them, appends what it saw to the
observations file outside the repositories, and reports two things:

- the **rule distribution**: per rule, how many findings, in how many
  packages, and the rate per hundred public objects;
- the **queue**: packages ranked by how much documentation work they hold,
  weighted the way the doc-quality research orders the work (entry points
  first: an entry point without an example outranks a helper without a
  summary; a rendering error outranks both).

Packages come from directories on the command line, or from a manifest: a
`.pth`-style file with one project directory per line (the local package
manifest is exactly that). The manifest is read, never written.

```pycon
>>> from epythet.sweep import queue_score
>>> queue_score({"DQ002": 3, "DR003": 1, "DQ004": 2}, severities={"DR003": "error"})
18.0
```

### Module Attributes

| [`RULE_WEIGHTS`](#epythet.sweep.RULE_WEIGHTS)     | How much one finding of a rule weighs in the queue (research_doc_quality §4.3: examples first, then correctness, then the summary, then parameter semantics).   |
|-------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`SEVERITY_WEIGHTS`](#epythet.sweep.SEVERITY_WEIGHTS) | Weight per severity for rendering findings (level 0.5) not listed above.                                                                                        |

### Functions

| [`packages_from_manifest`](#epythet.sweep.packages_from_manifest)(path)                       | Project directories listed in a `.pth`-style manifest (one per line, `#` comments).   |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`queue_score`](#epythet.sweep.queue_score)(counts, \*, severities)                | The queue weight of a package from its per-rule finding counts.                       |
| [`render_sweep`](#epythet.sweep.render_sweep)(result, \*[, top])                    | The human report: distribution table, then the queue.                                 |
| [`sweep`](#epythet.sweep.sweep)([dirs, manifest, levels, ignore, ...])       | Validate every package under `dirs` and `manifest` read-only; return the result.      |
| [`sweep_command`](#epythet.sweep.sweep_command)(\*dirs[, manifest, parse_only, ...]) | Validate many packages read-only; print the rule distribution and the work queue.     |
| [`sweeps_path`](#epythet.sweep.sweeps_path)()                                      | Where sweep summaries are appended: `<user data dir>/ledger/sweeps.jsonl`.            |

### Classes

| [`PackageSweep`](#epythet.sweep.PackageSweep)(path, name[, version, objects, ...])   | What the sweep saw in one package.                               |
|------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`SweepResult`](#epythet.sweep.SweepResult)([packages, levels, started, ...])       | Every package swept, the rule distribution and the ranked queue. |

### *class* epythet.sweep.PackageSweep(path, name, version=None, objects=0, undocumented=0, counts=<factory>, severities=<factory>, duration_s=0.0, error=None, notes=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What the sweep saw in one package.

### epythet.sweep.RULE_WEIGHTS *= {'DQ001': 3.0, 'DQ002': 4.0, 'DQ003': 1.0, 'DQ004': 0.5, 'DQ005': 1.0}*

How much one finding of a rule weighs in the queue (research_doc_quality §4.3:
examples first, then correctness, then the summary, then parameter semantics).

### epythet.sweep.SEVERITY_WEIGHTS *= {'error': 5.0, 'info': 0.5, 'warning': 2.0}*

Weight per severity for rendering findings (level 0.5) not listed above.

### *class* epythet.sweep.SweepResult(packages=<factory>, levels=(0, 0.5), started='', duration_s=0.0, ledger_severity=<factory>, ledger_title=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Every package swept, the rule distribution and the ranked queue.

#### distribution()

Per rule: findings, packages affected, rate per 100 public objects; most frequent first.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

#### queue()

Packages by descending queue score.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`PackageSweep`](#epythet.sweep.PackageSweep)]

### epythet.sweep.packages_from_manifest(path)

Project directories listed in a `.pth`-style manifest (one per line, `#` comments).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]

### epythet.sweep.queue_score(counts, , severities)

The queue weight of a package from its per-rule finding counts.

* **Return type:**
  [`float`](https://docs.python.org/3/library/functions.html#float)

### epythet.sweep.render_sweep(result, , top=20)

The human report: distribution table, then the queue.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.sweep.sweep(dirs=(), , manifest=None, levels=(0, 0.5), ignore=(), ledger=None, napoleon=True, linters=False, observe=True, observations_path=None, record=True, limit=None, on_package=None)

Validate every package under `dirs` and `manifest` read-only; return the result.

* **Parameters:**
  * **dirs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike)]) – Project or package directories.
  * **manifest** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – A `.pth`-style file of project directories, read only.
  * **levels** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`float`](https://docs.python.org/3/library/functions.html#float)]) – The validate levels to run (`0` coverage, `0.5` parse by default).
  * **ignore** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – Path substrings to skip inside each package.
  * **ledger** (`Ledger` | [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – The rule catalog (`None` = bundled).
  * **napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Parse docstrings with napoleon’s pre-processing.
  * **linters** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Also shell out to ruff and pydoclint at level 0.
  * **observe** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Append each package’s findings to the observations file.
  * **observations_path** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Override the observations file (tests use this).
  * **record** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Append the sweep summary to `sweeps.jsonl` under the user data dir.
  * **limit** ([`int`](https://docs.python.org/3/library/functions.html#int) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Sweep at most this many packages.
  * **on_package** – Called with each [`PackageSweep`](#epythet.sweep.PackageSweep) as it completes.
* **Return type:**
  [`SweepResult`](#epythet.sweep.SweepResult)

### epythet.sweep.sweep_command(\*dirs, manifest=None, parse_only=False, linters=False, ignore=None, ledger=None, no_napoleon=False, no_observe=False, limit=None, format='table', top=20, output=None, quiet=False)

Validate many packages read-only; print the rule distribution and the work queue.

Runs level 0 (coverage detectors) and level 0.5 (every docstring’s
doctree) over each package; never writes into a package or the manifest.

* **Parameters:**
  * **dirs** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Project or package directories to sweep.
  * **manifest** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – A .pth-style file listing project directories, one per line (read only).
  * **parse_only** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Run level 0.5 only (skip the coverage detectors).
  * **linters** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Also run ruff and pydoclint at level 0 (slower).
  * **ignore** ([`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)) – Skip files whose path contains this string (repeat -i for several).
  * **ledger** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Directory of extra rule YAML files overlaid on the bundled ledger.
  * **no_napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Parse docstrings without napoleon’s Google/NumPy pre-processing.
  * **no_observe** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Do not append findings (or the sweep summary) to the user data dir.
  * **limit** ([`int`](https://docs.python.org/3/library/functions.html#int) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Sweep at most this many packages.
  * **format** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – table (human) or json (the full result).
  * **top** ([`int`](https://docs.python.org/3/library/functions.html#int)) – How many packages the queue shows.
  * **output** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Write the report to this file instead of stdout.
  * **quiet** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Do not print progress on stderr.
* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.sweep.sweeps_path()

Where sweep summaries are appended: `<user data dir>/ledger/sweeps.jsonl`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
