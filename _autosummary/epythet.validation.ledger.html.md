# epythet.validation.ledger

The artifact ledger: rule definitions (bundled YAML) and observations (user data dir).

Storage is split by mutability, as decided in the v2 decision record (D8):

- **Rules** are one YAML file per rule under `epythet/ledger/rules/<group>/`
  (the `build` namespace lives in `build_warnings/`: a directory named
  `build/` is dropped from wheels by the project’s `.gitignore`)
  with a sibling `.py` fixture that doubles as the regression test. They are
  human-edited, rarely, and ship inside epythet.
- **Observations** (occurrences with file paths and snippets from real repos)
  are append-only JSONL under the user data dir, never inside the repo, because
  they are derived from repositories that are not all public. Occurrence counts
  are a *derived view* over that file, computed on read.

The `ledger=` seam of `epythet.validation.validate()` accepts `None`
(bundled rules), a directory (bundled rules plus a package-local overlay,
same id overrides) or a ready [`Ledger`](#epythet.validation.ledger.Ledger).

### Module Attributes

| [`PARSE_KINDS`](#epythet.validation.ledger.PARSE_KINDS)   | Detector kinds evaluated per docstring at level 0.5.   |
|----------------------------------------------------------------|--------------------------------------------------------|

### Functions

| [`append_observations`](#epythet.validation.ledger.append_observations)(findings, \*, package[, ...])   | Append one JSONL line per finding; returns how many were written.                        |
|------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`iter_fixture_cases`](#epythet.validation.ledger.iter_fixture_cases)(fixture_path)                    | Yield the tagged specimens of a fixture file.                                            |
| [`iter_rule_files`](#epythet.validation.ledger.iter_rule_files)(rules_dir)                          | Every `*.yaml` under `rules_dir`, in a stable order.                                     |
| [`load_ledger`](#epythet.validation.ledger.load_ledger)([ledger])                               | Resolve the `ledger=` seam to a [`Ledger`](#epythet.validation.ledger.Ledger). |
| [`load_rule`](#epythet.validation.ledger.load_rule)(path)                                     | Load and validate one rule file.                                                         |
| [`observation_record`](#epythet.validation.ledger.observation_record)(finding, \*, package, ...)       | The JSONL line written for one finding.                                                  |
| [`observations_path`](#epythet.validation.ledger.observations_path)()                                 | Where observations are appended: `<user data dir>/ledger/observations.jsonl`.            |
| [`occurrence_counts`](#epythet.validation.ledger.occurrence_counts)([path])                           | Occurrences per rule id over the whole observations file (empty if absent).              |
| [`user_data_dir`](#epythet.validation.ledger.user_data_dir)()                                     | `$EPYTHET_DATA_DIR`, else `$XDG_DATA_HOME/epythet`, else `~/.local/share/epythet`.       |

### Classes

| [`FixtureCase`](#epythet.validation.ledger.FixtureCase)(name, line, expect_hit, ...)         | One specimen function in a fixture: its docstring and what the tag promises.   |
|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`Ledger`](#epythet.validation.ledger.Ledger)([rules, sources])                         | The loaded rule catalog: bundled rules plus any overlay, keyed by id.          |
| [`Rule`](#epythet.validation.ledger.Rule)(id, title, namespace, severity, ...[, ...]) | One ledger rule, loaded from its YAML file and validated.                      |

### Exceptions

| [`LedgerError`](#epythet.validation.ledger.LedgerError)   | A rule file is schema-invalid, a rule id is duplicated, or a fixture is missing.   |
|----------------------------------------------------------------|------------------------------------------------------------------------------------|

### *class* epythet.validation.ledger.FixtureCase(name, line, expect_hit, rule_ids, docstring)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One specimen function in a fixture: its docstring and what the tag promises.

### *class* epythet.validation.ledger.Ledger(rules=<factory>, sources=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The loaded rule catalog: bundled rules plus any overlay, keyed by id.

#### add_dir(rules_dir, , allow_override=False)

Load every rule under `rules_dir`; duplicates are an error unless overriding.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

#### check_build_examples()

Every build-warning rule’s `example_warning` must classify to that rule.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

#### of_kind(\*kinds, include_proposed=False)

Rules whose detector kind is one of `kinds`, in id order.

Proposed rules (`status: {proposed: ...}`) are left out unless asked
for: a proposal from level 3 must not gate anyone until a maintainer
promotes it.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Rule`](#epythet.validation.ledger.Rule)]

### *exception* epythet.validation.ledger.LedgerError

Bases: [`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)

A rule file is schema-invalid, a rule id is duplicated, or a fixture is missing.

`epythet validate` maps this to exit code 20 so CI can tell “the catalog is
broken” apart from “the package has problems”.

### epythet.validation.ledger.PARSE_KINDS *= ('regex', 'source', 'doctree')*

Detector kinds evaluated per docstring at level 0.5.

### *class* epythet.validation.ledger.Rule(id, title, namespace, severity, precision, detector, message, fix=<factory>, status=<factory>, applies_to=<factory>, explanation='', references=<factory>, path=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One ledger rule, loaded from its YAML file and validated.

`detector` is the raw mapping from the YAML; the compiled regex (for
`regex` and `source` kinds) is available as [`pattern`](#epythet.validation.ledger.Rule.pattern).

#### applies(, napoleon)

Whether the rule is live under the given napoleon setting.

A rule that declares `applies_to: {napoleon: false}` only makes sense
when Google/NumPy sections are *not* pre-processed (DR012 is the case).

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

#### *property* autofixable *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether `epythet repair` (WP3) can rewrite this one mechanically.

#### finding(, level, evidence='', file=None, line=None, object=None, message=None)

A `Finding` for this rule at one location.

* **Return type:**
  [`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)

#### *property* fix_hint *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The one-line fix hint shown next to each finding.

#### *property* fixture_path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)*

The sibling `.py` fixture, when the rule has one.

#### format_message(match)

Fill the rule’s message template with the matched evidence.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

#### *property* is_proposed *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether the rule is still a proposal (level 3 or a human wrote it, nobody promoted it).

#### *property* kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

one of `DETECTOR_KINDS`.

* **Type:**
  The detector kind

#### *property* pattern *: [Pattern](https://docs.python.org/3/library/re.html#re.Pattern) | [None](https://docs.python.org/3/library/constants.html#None)*

Compiled `detector.pattern` (multiline; case-insensitive on request).

### epythet.validation.ledger.append_observations(findings, , package, package_version=None, path=None)

Append one JSONL line per finding; returns how many were written.

* **Return type:**
  [`int`](https://docs.python.org/3/library/functions.html#int)

### epythet.validation.ledger.iter_fixture_cases(fixture_path)

Yield the tagged specimens of a fixture file.

A specimen is a `def` (or `class`) whose header line carries a
`# ruleid: DR001` (must fire) or `# ok: DR001` (must not fire) comment,
Semgrep style. Several ids may be listed, comma-separated.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`FixtureCase`](#epythet.validation.ledger.FixtureCase)]

### epythet.validation.ledger.iter_rule_files(rules_dir)

Every `*.yaml` under `rules_dir`, in a stable order.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]

### epythet.validation.ledger.load_ledger(ledger=None)

Resolve the `ledger=` seam to a [`Ledger`](#epythet.validation.ledger.Ledger).

`None` loads the bundled rules; a path loads the bundled rules and then
overlays the directory (same id overrides); a [`Ledger`](#epythet.validation.ledger.Ledger) is returned
as is.

* **Return type:**
  [`Ledger`](#epythet.validation.ledger.Ledger)

### epythet.validation.ledger.load_rule(path)

Load and validate one rule file.

* **Return type:**
  [`Rule`](#epythet.validation.ledger.Rule)

### epythet.validation.ledger.observation_record(finding, , package, package_version, run_id)

The JSONL line written for one finding.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### epythet.validation.ledger.observations_path()

Where observations are appended: `<user data dir>/ledger/observations.jsonl`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### epythet.validation.ledger.occurrence_counts(path=None)

Occurrences per rule id over the whole observations file (empty if absent).

This is the derived view that replaces an `occurrences` field in the rule
files; a malformed line is skipped rather than failing the run.

* **Return type:**
  [`Counter`](https://docs.python.org/3/library/collections.html#collections.Counter)

### epythet.validation.ledger.user_data_dir()

`$EPYTHET_DATA_DIR`, else `$XDG_DATA_HOME/epythet`, else `~/.local/share/epythet`.

Deliberately XDG-style on every platform (not `platformdirs`’s macOS
`Application Support`): it matches where the rest of epythet’s local
data already lives, and it is what the decision record names.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
