# epythet.validation

`epythet validate`: tiered documentation validation with a growing artifact ledger.

Levels 0 (lint), 0.5 (parse) and 1 (build) live here; levels 2 and 3 are
reserved for a later work package. The ledger of known rendering artifacts is
under `epythet/ledger/rules` (one YAML per rule with a sibling `.py`
fixture); observations from real runs are appended outside the repository.

```pycon
>>> from epythet.validation import validate
>>> report = validate("path/to/project", level=1)
>>> report.exit_code()
0
```

### Modules

| [`build`](epythet.validation.build.html.md#module-epythet.validation.build)              | Level 1: run the documentation build and turn its warning stream into findings.       |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`cli`](epythet.validation.cli.html.md#module-epythet.validation.cli)                  | The `epythet validate` command: the CLI adapter over `epythet.validation.validate()`. |
| [`core`](epythet.validation.core.html.md#module-epythet.validation.core)                | The `validate` orchestrator: resolve the package, run the levels, build the report.   |
| [`detectors`](epythet.validation.detectors.html.md#module-epythet.validation.detectors)      | Named doctree detectors, referenced from ledger rules by `detector.function`.         |
| [`docstrings`](epythet.validation.docstrings.html.md#module-epythet.validation.docstrings)    | Docstring extraction from Python source, without importing anything.                  |
| [`lint`](epythet.validation.lint.html.md#module-epythet.validation.lint)                | Level 0: static docstring linters, normalised into the finding model.                 |
| [`model`](epythet.validation.model.html.md#module-epythet.validation.model)              | The finding and report model shared by every level of `epythet validate`.             |
| [`parse`](epythet.validation.parse.html.md#module-epythet.validation.parse)              | Level 0.5: parse each docstring's docutils doctree and run the ledger's detectors.    |
| [`render`](epythet.validation.render.html.md#epythet.validation.render)(report[, format]) | Render with the named format (`table`, `json` or `jsonl`).                            |
