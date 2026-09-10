# epythet.validation.lint

Level 0: static docstring linters, normalised into the finding model.

Two tools are shelled out to. `ruff check --select D` covers pydocstyle
(presence, summary lines, section formatting for the configured convention).
`pydoclint` covers signature consistency (`DOC1xx`/`DOC2xx`/`DOC4xx`/
`DOC5xx`: undocumented or misnamed parameters, missing returns), which ruff
only previews a handful of; it is optional and skipped with a note when it is
not installed.

Findings keep the tool’s own code as `rule` (`D102`, `DOC101`) and name
the tool in `tool`, so they never collide with ledger ids.

### Module Attributes

| [`STYLES`](#epythet.validation.lint.STYLES)            | Docstring styles ruff's pydocstyle convention and pydoclint's `--style` both accept.                        |
|--------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| [`PYDOCLINT_OPTIONS`](#epythet.validation.lint.PYDOCLINT_OPTIONS) | the house convention is types in annotations, never in the docstring, and not every signature is annotated. |

### Functions

| [`pydoclint_severity`](#epythet.validation.lint.pydoclint_severity)(code)                           | `DOC1xx` (arguments disagree with the signature) are warnings; the rest info.   |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`ruff_severity`](#epythet.validation.lint.ruff_severity)(code)                                | `D1xx` (missing docstrings) are warnings; other `D` rules are style, so info.   |
| [`run_lint_level`](#epythet.validation.lint.run_lint_level)(package_dir, \*, project_dir)       | Level 0: ruff D plus pydoclint, with notes for anything skipped.                |
| [`run_pydoclint`](#epythet.validation.lint.run_pydoclint)(package_dir, \*, project_dir[, ...]) | Run `pydoclint` if installed; otherwise return a note and no findings.          |
| [`run_ruff`](#epythet.validation.lint.run_ruff)(package_dir, \*, project_dir[, style])    | Run `ruff check --select D` and translate its JSON output.                      |

### epythet.validation.lint.PYDOCLINT_OPTIONS *= ('--quiet', '--skip-checking-short-docstrings', 'true', '--arg-type-hints-in-docstring', 'false', '--arg-type-hints-in-signature', 'false', '--check-return-types', 'false', '--check-yield-types', 'false')*

the house convention
is types in annotations, never in the docstring, and not every signature is annotated.

* **Type:**
  pydoclint options that silence its type-hint bookkeeping

### epythet.validation.lint.STYLES *= ('google', 'numpy', 'sphinx')*

Docstring styles ruff’s pydocstyle convention and pydoclint’s `--style` both accept.

### epythet.validation.lint.pydoclint_severity(code)

`DOC1xx` (arguments disagree with the signature) are warnings; the rest info.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> pydoclint_severity("DOC101"), pydoclint_severity("DOC201")
('warning', 'info')
```

### epythet.validation.lint.ruff_severity(code)

`D1xx` (missing docstrings) are warnings; other `D` rules are style, so info.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> ruff_severity("D102"), ruff_severity("D205")
('warning', 'info')
```

### epythet.validation.lint.run_lint_level(package_dir, , project_dir, style='google')

Level 0: ruff D plus pydoclint, with notes for anything skipped.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]

### epythet.validation.lint.run_pydoclint(package_dir, , project_dir, style='google')

Run `pydoclint` if installed; otherwise return a note and no findings.

pydoclint writes its report to stderr, so both streams are parsed.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]

### epythet.validation.lint.run_ruff(package_dir, , project_dir, style='google')

Run `ruff check --select D` and translate its JSON output.

Returns `(findings, notes)`; `notes` explains a skipped run.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]
