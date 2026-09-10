# epythet.validation

`epythet validate`: tiered documentation validation with a growing artifact ledger.

Levels 0 (lint and coverage), 0.5 (parse), 1 (build), 2 (render) and 3
(review packet) live here. The ledger of known rendering artifacts is under
`epythet/ledger/rules` (one YAML per rule with a sibling `.py` fixture);
observations from real runs are appended outside the repository, and rules a
reviewer proposes go to an overlay there too (`epythet ledger propose`).

```pycon
>>> from epythet.validation import validate
>>> report = validate("path/to/project", level=1)
>>> report.exit_code()
0
```

### Modules

| [`build`](epythet.validation.build.html.md#module-epythet.validation.build)                                 | Level 1: run the documentation build and turn its warning stream into findings.        |
|------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`cli`](epythet.validation.cli.html.md#module-epythet.validation.cli)                                     | The `epythet validate` command: the CLI adapter over `epythet.validation.validate()`.  |
| [`core`](epythet.validation.core.html.md#module-epythet.validation.core)                                   | The `validate` orchestrator: resolve the package, run the levels, build the report.    |
| [`coverage`](epythet.validation.coverage.html.md#module-epythet.validation.coverage)                           | Level 0 coverage and quality smells: the queue signals, computed from the `ast` alone. |
| [`detectors`](epythet.validation.detectors.html.md#module-epythet.validation.detectors)                         | Named doctree detectors, referenced from ledger rules by `detector.function`.          |
| [`docstrings`](epythet.validation.docstrings.html.md#module-epythet.validation.docstrings)                       | Docstring extraction from Python source, without importing anything.                   |
| [`lint`](epythet.validation.lint.html.md#module-epythet.validation.lint)                                   | Level 0: static docstring linters, normalised into the finding model.                  |
| [`model`](epythet.validation.model.html.md#module-epythet.validation.model)                                 | The finding and report model shared by every level of `epythet validate`.              |
| [`parse`](epythet.validation.parse.html.md#module-epythet.validation.parse)                                 | Level 0.5: parse each docstring's docutils doctree and run the ledger's detectors.     |
| [`propose`](epythet.validation.propose.html.md#epythet.validation.propose)(reply_path, \*[, overlay, ledger]) | Write every `proposed_rules` entry of a reply into `overlay` as a proposed rule.       |
| [`render`](epythet.validation.render.html.md#epythet.validation.render)(report[, format])                    | Render with the named format (`table`, `json` or `jsonl`).                             |
| [`rendered`](epythet.validation.rendered.html.md#module-epythet.validation.rendered)                           | Level 2: read the *rendered* output (XML, HTML, text) and report what the build hid.   |
| [`review`](epythet.validation.review.html.md#module-epythet.validation.review)                               | Level 3: a review *packet* for an in-session agent, and the ingestion of its reply.    |
