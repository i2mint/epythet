# epythet.validation.model

The finding and report model shared by every level of `epythet validate`.

One in-memory model, several renderers: the human table, the JSON document and
the JSONL stream are all views over the same [`Report`](#epythet.validation.model.Report), so they can never
disagree. The vocabulary here (severities, levels, exit codes) is the one fixed
in the epythet v2 decision record (discussion #15, decision D8).

Levels are named by *what artifact they read*, not by when they run:

|   level | name   | reads                                                 |
|---------|--------|-------------------------------------------------------|
|     0   | lint   | the source text of each docstring (ruff, pydoclint)   |
|     0.5 | parse  | the docutils doctree of each docstring, in isolation  |
|     1   | build  | the Sphinx warning stream                             |
|     2   | render | the built output (owned by WP3, not implemented here) |
|     3   | review | an LLM review of rendered pages (WP3, never gates)    |

The CLI exposes them as a *tier index* (`--level 0` runs level 0,
`--level 1` runs levels 0 and 0.5, `--level 2` adds the build), which is
what [`TIERS`](#epythet.validation.model.TIERS) and [`levels_for_tier()`](#epythet.validation.model.levels_for_tier) translate.

### Module Attributes

| [`SEVERITY_RANK`](#epythet.validation.model.SEVERITY_RANK)      | Lower rank is worse.                                                       |
|---------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`LEVELS`](#epythet.validation.model.LEVELS)             | Level number -> level name, in run order.                                  |
| [`TIERS`](#epythet.validation.model.TIERS)              | Run order of the levels; index into this list is the CLI `--level` tier.   |
| [`IMPLEMENTED_TIERS`](#epythet.validation.model.IMPLEMENTED_TIERS)  | Tiers this work package implements.                                        |
| [`IMPLEMENTED_LEVELS`](#epythet.validation.model.IMPLEMENTED_LEVELS) | The levels those tiers run.                                                |
| [`EXIT_FOR_LEVEL`](#epythet.validation.model.EXIT_FOR_LEVEL)     | Level -> exit code when that level has findings at or above the threshold. |

### Functions

| [`levels_for_tier`](#epythet.validation.model.levels_for_tier)(tier)                     | The levels a CLI tier runs: every level up to and including the tier's.   |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`severity_at_or_above`](#epythet.validation.model.severity_at_or_above)(severity, threshold) | True when `severity` is at least as serious as `threshold`.               |
| [`sort_findings`](#epythet.validation.model.sort_findings)(findings)                   | Stable order for every renderer: severity, then rule id, then location.   |

### Classes

| [`Finding`](#epythet.validation.model.Finding)(rule, severity, level, message[, ...])   | One problem found in one place.                                              |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`Report`](#epythet.validation.model.Report)(package, package_dir, levels_run[, ...])  | Everything one `validate` run produced, plus enough context to reproduce it. |
| [`Timer`](#epythet.validation.model.Timer)(durations, key)                            | Records how long each level took, as `report.durations[level_name]`.         |

### epythet.validation.model.EXIT_FOR_LEVEL *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[float](https://docs.python.org/3/library/functions.html#float), [int](https://docs.python.org/3/library/functions.html#int)]* *= {0: 10, 0.5: 11, 1: 12, 2: 13, 3: 14}*

Level -> exit code when that level has findings at or above the threshold.

### *class* epythet.validation.model.Finding(rule, severity, level, message, file=None, line=None, object=None, detector='', evidence='', fix='', autofixable=False, strategy='', tool='epythet', ledger_occurrences=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One problem found in one place.

`rule` is a ledger rule id (`DR001`) for levels 0.5 and 1, or the
upstream tool’s code (`D102`, `DOC101`) for level 0, in which case
`tool` names the tool. `line` is 1-based and, for docstring findings,
the line the docstring literal starts on.

#### *property* location *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

`file:line` for the table renderer, or `-` when unknown.

#### to_dict()

JSON-ready dict; the JSON and JSONL renderers emit exactly this.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### epythet.validation.model.IMPLEMENTED_LEVELS *= (0, 0.5, 1)*

The levels those tiers run.

### epythet.validation.model.IMPLEMENTED_TIERS *= (0, 1, 2)*

Tiers this work package implements. Tiers 3 and 4 (levels 2 and 3) are WP3.

### epythet.validation.model.LEVELS *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[float](https://docs.python.org/3/library/functions.html#float), [str](https://docs.python.org/3/library/stdtypes.html#str)]* *= {0: 'lint', 0.5: 'parse', 1: 'build', 2: 'render', 3: 'review'}*

Level number -> level name, in run order.

### *class* epythet.validation.model.Report(package, package_dir, levels_run, findings=<factory>, durations=<factory>, objects_checked=0, objects_undocumented=0, notes=<factory>, epythet_version=None, sphinx_version=None, docutils_version=None, ledger_sources=<factory>, schema_version='1')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Everything one `validate` run produced, plus enough context to reproduce it.

#### counts_by_severity()

`{"error": n, "warning": n, "info": n}` over all findings.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`int`](https://docs.python.org/3/library/functions.html#int)]

#### exit_code(fail_on='error')

The process exit code: `0` when clean, else the code of the first failing level.

The *first* (lowest) failing level is reported because it is the first
gate a CI pipeline would have stopped at.

* **Return type:**
  [`int`](https://docs.python.org/3/library/functions.html#int)

```pycon
>>> r = Report("p", "/p", [0, 0.5])
>>> r.exit_code()
0
>>> r.findings.append(Finding("DR001", "error", 0.5, "leak"))
>>> r.exit_code(), r.exit_code("info")
(11, 11)
>>> r.findings.append(Finding("D102", "warning", 0, "missing"))
>>> r.exit_code(), r.exit_code("warning")
(11, 10)
```

#### failing_levels(fail_on='error')

Levels with at least one finding at or above `fail_on`, in run order.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`float`](https://docs.python.org/3/library/functions.html#float)]

#### summary()

The `summary` block of the JSON document.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### to_dict()

The JSON document described in decision D8.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### epythet.validation.model.SEVERITY_RANK *= {'error': 0, 'info': 2, 'warning': 1}*

Lower rank is worse. Used for `--fail-on` comparisons.

### epythet.validation.model.TIERS *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[float](https://docs.python.org/3/library/functions.html#float)]* *= [0, 0.5, 1, 2, 3]*

Run order of the levels; index into this list is the CLI `--level` tier.

### *class* epythet.validation.model.Timer(durations, key)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Records how long each level took, as `report.durations[level_name]`.

```pycon
>>> durations = {}
>>> with Timer(durations, "parse"):
...     pass
>>> list(durations) == ["parse"] and durations["parse"] >= 0
True
```

### epythet.validation.model.levels_for_tier(tier)

The levels a CLI tier runs: every level up to and including the tier’s.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`float`](https://docs.python.org/3/library/functions.html#float)]

```pycon
>>> levels_for_tier(0)
[0]
>>> levels_for_tier(1)
[0, 0.5]
>>> levels_for_tier(2)
[0, 0.5, 1]
```

### epythet.validation.model.severity_at_or_above(severity, threshold)

True when `severity` is at least as serious as `threshold`.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

```pycon
>>> severity_at_or_above("error", "warning")
True
>>> severity_at_or_above("info", "warning")
False
```

### epythet.validation.model.sort_findings(findings)

Stable order for every renderer: severity, then rule id, then location.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](#epythet.validation.model.Finding)]
