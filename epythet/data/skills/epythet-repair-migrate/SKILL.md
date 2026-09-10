---
name: epythet-repair-migrate
description: >-
  The per-repository documentation sweep for packages documented with epythet:
  baseline, validate, repair rendering artifacts in source, improve coverage,
  correctness and completeness of docstrings, choose a theme, remove a
  committed docsrc/, and land the change. Use when asked to "migrate the docs
  to epythet 0.2", "fix the docstrings across this repo", "run the docs sweep",
  "repair the rendering artifacts", "upgrade docsrc", or "clean up this
  package's documentation". Marks which commands exist today and which are
  coming in a later epythet release.
license: Apache-2.0
metadata:
  audience: users
---

# epythet-repair-migrate: the per-repository sweep

One session per repository. The sweep couples two things on purpose: fixing rendering artifacts, and improving what the docstrings *say* while you are in them (coverage, correctness, completeness), under the behaviour-claim policy of the `epythet-docstring-style` skill. **Never invent behaviour.** An undocumented function is neutral; a wrong docstring costs agents measurably.

## Tool availability

| Step | Tool | Status |
|---|---|---|
| validate levels 0 / 0.5 / 1 | `epythet validate` | shipped (0.2.1) |
| repair: blank line before doctests | `epythet.repair_package(path, write_to_files=True)` | shipped (since 0.1.x) |
| repair: all safe normalizer rewrites to source, with a diff | `epythet repair` | **coming in WP3** |
| RST field lists to Google sections, per module, opt-in | `epythet migrate-style` | **coming in WP3** |
| fleet-wide artifact frequency run | `epythet sweep` | **coming in WP3** |
| validate levels 2 (render) and 3 (review) | `epythet validate --level 3/4` | **coming in WP3**; use the `docs-reviewer` subagent meanwhile |

Until `epythet repair` ships, every artifact beyond the missing blank line before a doctest is fixed by hand, guided by the `fix` hint on each finding. Do not write a competing repair script into the repository.

## Procedure

### 0. Baseline (gate)

```bash
git switch -c docs/epythet-sweep
pytest -q                          # must be green before you touch anything
pytest --doctest-modules -q PKG    # record how many doctests run and pass
epythet validate . --format json --output /tmp/before.json
epythet validate . --level 2 --format table   # the Sphinx warnings, for the before count
```

A sweep landing on a red package cannot tell its own damage from pre-existing damage. If tests are red, stop and report.

Record the public surface: `__all__` in `__init__.py` when present; otherwise every non-underscore name bound in `__init__` plus non-underscore module-level callables in non-underscore modules. That is the denominator for every coverage number. Read the README and the top-level docstring together and write down the package's one-sentence purpose and three main entry points; if you cannot, that is finding number one.

### 1. Repair rendering artifacts (mechanical)

```python
from epythet import repair_package
repair_package("PKG")                        # dry run: prints what would change
repair_package("PKG", write_to_files=True)   # inserts the blank line before glued doctests
```

Then work through `epythet validate .` findings by rule, most frequent first. Each finding's `fix` says what to change. Safe edits (formatting only): blank lines before lists, doctests and field lists; `Returns: text` one-liners to a section; Markdown fences to indented literal blocks; `## Heading` to a bold phrase. Keep RST field lists as RST; do not convert styles in this step.

Re-run `pytest --doctest-modules`: a doctest that was glued to prose was never executed before, and may fail now that it runs. Fix the example or the expected output **only after running the code**; if the example is wrong and you cannot determine the right output, mark it `# doctest: +SKIP` and file it.

### 2. Coverage pass

Gates: a module docstring on every non-underscore module (Ruff `D100`); a docstring on every name in the public surface (`D101` to `D103`, `D106`). Queue items: at least one runnable doctest on every **entry point** (not every helper); private helpers get a one-line summary only; flag lazy docstrings (summary content words a subset of the name's content words) as uncovered.

### 3. Correctness pass

Gates: documented parameters match the signature in name and order (`D417`, pydoclint); `Returns:` present iff the function returns a value, `Yields:` iff it yields, `Raises:` entries correspond to actual `raise` statements (`DOC201`/`DOC202`/`DOC501`/`DOC502` or pydoclint); every doctest runs. Queue items: every backticked identifier and `See Also` target resolves; prose types that contradict the annotation are deleted (the annotation is the SSOT).

### 4. Completeness pass

Score entry points against the six-dimension rubric (summary, parameter semantics, example, failure modes, cross-references, module orientation). Anything scoring 0 on summary or example is a work item. Apply the three-size rubric: tiny helpers get one line; entry points get intent, semantics, a run doctest plus a variation, `Raises:` with triggers, 1 to 3 `See Also`; complex classes add attributes, a lifecycle doctest and state invariants. Module docstrings: purpose, 2 to 5 named entry points, one minimal doctest. Do not triple the docstring length; length is a smell.

Every added example is executed first and its real output pasted. Everything you could not verify goes into the report as "not changed because behaviour could not be verified".

### 5. README pass (queue)

Line 1: what it is, one sentence, no marketing. Then install and the smallest complete runnable example (imports included). Then paragraphs, then details, then a link to the rendered docs and to the flat `<package>.md` aggregate. Do not duplicate API reference into the README.

### 6. Theme

Build locally (`epythet quickstart . --ignore tests/`) and look at the landing page and one API page. `theme = "auto"` is the fleet default and is fine for most packages; change it only when the `epythet-theme` decision procedure says so (brand or landing page: shibuya; data/ML: pydata; notebook-heavy: book; 5 pages or fewer: alabaster). Write only `[tool.epythet] theme` / `accent` / `mode`, never `docsrc/conf.py`.

### 7. Remove the committed `docsrc/`

If the repository commits a `docsrc/` that is a stale epythet template (template `conf.py`, `index.rst`, `table_of_contents.rst`, `module_docs/`, `Makefile`), delete it and add `docsrc/` to `.gitignore`: CI regenerates it on every build, and the 0.2 scaffold is two files anyway. Keep `docsrc/` only where hand-written pages exist; in that case run `epythet make-docsrc .` so `conf.py` becomes the two-line shim and hand-written pages stay untouched.

Also remove `docsrc/` references from packaging config if any, and check `[tool.wads.ci.docs]` or the Pages workflow still passes the right `ignore` list.

### 8. Exit (gate)

```bash
pytest -q && pytest --doctest-modules -q PKG
epythet validate . --format json --output /tmp/after.json
epythet validate . --level 2
```

Both must be green (or the remaining findings explicitly accepted). Compose the per-package report: coverage before and after, validate counts per rule before and after, Sphinx warning count before and after, rubric distribution for entry points, and the list of claims declined for lack of verification.

### 9. Land

One pull request per repository, titled for the sweep, body carrying the report. Squash-merge. The Pages workflow republishes the site on merge; check `epythet check-pages owner/repo` if the site does not update. Append any newly seen artifact class as a proposed ledger rule (the `epythet-validate` skill says how).

## Delegation

The `docs-migrator` subagent shipped with epythet runs this procedure end to end for one repository; the `docs-reviewer` subagent reviews rendered pages and proposes ledger rules. Both are in the package's `data/agents/` directory and on the "For AI agents" page of epythet's documentation.
