---
name: epythet-validate
description: >-
  Check a Python package's docstrings for rendering artifacts and build
  problems with `epythet validate`: the validation levels (lint, parse, build,
  render, review), the exit codes, output formats, the artifact ledger of rules
  (DR001...), how findings are recorded, and how to propose a new rule. Use when
  asked to "validate the docs", "check docstrings before publishing", "why does
  this docstring render wrong", "gate docs in CI", "what does DR003 mean", or
  when reading or extending epythet's ledger of documentation problems.
license: Apache-2.0
metadata:
  audience: users
---

# epythet-validate: tiered docstring validation and the artifact ledger

Most docstring rendering problems are **silent**: a strict Sphinx build (`-W -n`) flags 9 of 21 known artifact classes, and the other 12 render wrongly with no warning. `epythet validate` therefore reads the docutils doctree of every docstring in isolation, without a build, and matches it against a ledger of known artifacts.

## Run it

```bash
pip install "epythet[validate]"          # adds pyyaml, ruff, pydoclint
epythet validate PROJECT_DIR             # level 1: lint + parse, no build, seconds
epythet validate PROJECT_DIR --level 2   # also the Sphinx build
epythet validate PROJECT_DIR --format json --output report.json
epythet validate PROJECT_DIR --fail-on warning -i tests/ -i scrap/
python -m epythet.validation PROJECT_DIR # same command without the console script
```

`PROJECT_DIR` may be a project root (with `pyproject.toml`), a package directory, or an importable package name.

```python
from epythet.validation import validate

report = validate("path/to/project", level=1)
report.exit_code()  # 0 when clean at the default threshold
report.findings  # list of Finding (rule, severity, level, object, file, line, message, fix, ...)
```

## Levels: named by what they read

| Level | Name | Reads | Catches | Cost | Gates CI? |
|---|---|---|---|---|---|
| 0 | lint | the source text of each docstring (ruff `D`, pydoclint) | undocumented or misnamed parameters, missing `Returns`, coverage, `\` in a non-raw docstring | about 2 s | yes |
| 0.5 | parse | the docutils doctree of each docstring, parsed alone with stub Sphinx roles and napoleon pre-processing | rendering artifacts: leaked `:param`, `>>>` inside a paragraph, glued bullet lists, accidental definition lists, Markdown fences, `Returns: text` one-liners | under a second per thousand docstrings | yes, the main gate |
| 1 | build | the Sphinx warning stream (`sphinx-build -W`, warnings classified by `[type]` suffix) | broken cross-references, unknown directives, duplicate objects, toctree problems | 10 to 40 s | yes |
| 2 | render | the built text/HTML output | empty pages, unresolved xrefs, dangling anchors, missing images, snapshot drift | 5 to 20 s | yes, snapshot diff |
| 3 | review | an LLM over rendered text of changed pages | unknown unknowns; **proposes** new ledger rules | minutes | **never** |

The CLI `--level` is a *tier*: `0` runs level 0; `1` (default) runs 0 and 0.5; `2` adds level 1 (which needs a `docsrc/conf.py`: run `epythet quickstart` first, or pass `--docsrc`); the next two tiers will run levels 2 and 3. Levels 2 and 3 are **coming in WP3** (see the tracking issue linked below); until then, Level 3 is performed by the `docs-reviewer` subagent shipped with epythet, which produces proposed rules rather than pass/fail.

Options: `--style google|numpy|sphinx` (the convention passed to the linters), `--no-napoleon` (parse without Google/NumPy pre-processing), `--ledger DIR` (overlay extra rules), `--docsrc DIR` (Sphinx sources for the build level), `--no-observe` (do not record observations), `--max-per-rule N` (table verbosity).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | clean, or every finding is below `--fail-on` |
| 1 | internal error in `epythet validate` itself |
| 10 | level 0 (lint) findings at or above the threshold |
| 11 | level 0.5 (parse) findings |
| 12 | level 1 (build) findings, or the build failed |
| 13 / 14 | levels 2 / 3 (reserved; 14 only ever with an explicit review gate) |
| 20 | ledger integrity failure: a rule file is schema-invalid, an id is duplicated, or a fixture is missing |

`--fail-on {error,warning,info}` (default `error`) is a separate knob, so a sweep can report everything while gating on little. A CI job that must stay green fleet-wide uses `--fail-on error`; `DR011` (single backticks rendering as italics under Sphinx defaults) ships at `info` because epythet sites set `default_role = "code"` and it is a no-op there.

## Output

`--format table` groups one line per finding by rule, with "N more of DRxxx" trailers. `--format json` is the full report (`schema_version`, `package`, `package_dir`, `epythet_version`, `sphinx_version`, `docutils_version`, `levels_run`, `ledger_sources`, `summary` with counts and durations, `notes`, `findings`). `--format jsonl` streams one finding per line. All three are views of one `Report`, so they cannot disagree. A finding carries: `rule`, `severity`, `level`, `object` (dotted path), `file`, `line`, `detector`, `message`, `evidence`, `fix`, `autofixable`, `ledger_occurrences`.

## Reading a finding

Each rule id (`DR001`, `DR003`, ...) names a ledger rule. The message says what docutils did; `fix` says what to change; `autofixable: true` means `epythet.repair_package` (today) or `epythet repair` (WP3) can rewrite the source safely. The most frequent ones on real packages:

| Rule | Title | Fix |
|---|---|---|
| DR001 | RST field list leaked into prose | blank line before the first `:param` |
| DR003 | doctest rendered as prose | blank line before the first `>>>` |
| DR008 | bullet list glued to prose | blank line before the list |
| DR029 | `Returns: text` one-liner | put the text on an indented line under `Returns:` |
| DR010 | unbalanced inline markup (`*args`) | leave as is in epythet sites (normalized at build) or use double backticks |
| DR006 | Markdown fence | indent as a literal block, or leave it (normalized at build) |
| DR016 | unexpected indentation became a block quote | dedent the continuation, or add a blank line |
| DR030 | docstring starts with a doctest | one summary line first |
| DR011 | single backticks (italic under Sphinx defaults) | info only; fine on epythet sites |

Rule explanations (`## What it does` / `## Why is this bad?`) live in each rule's YAML under `epythet/ledger/rules/`.

## The ledger

Rules and observations are stored separately, by mutability:

- **Rules** ship inside epythet, one YAML per rule under `epythet/ledger/rules/<group>/DRnnn.yaml` (groups: `rendering`, `source`, `build_warnings`), each with a sibling `DRnnn.py` fixture whose functions are tagged `# ruleid: DRnnn` (must fire) or `# ok: DRnnn` (must not). The fixture is the regression test. Build-warning rules carry an `example_warning` that must classify to themselves.
- **Observations** (occurrences with file paths and snippets from the packages you validate) are appended as JSONL to `~/.local/share/epythet/ledger/observations.jsonl` (override the directory with `EPYTHET_DATA_DIR`), never inside a repository, because they derive from code that is not all public. `ledger_occurrences` on a finding is a count over that file. `--no-observe` skips the append.

Rule schema (the fields validated on load; exit 20 when broken):

```yaml
id: DR003
title: Doctest rendered as prose
namespace: rendering                  # rendering | source | semantics | build | links | coverage
status: {stable_since: "0.2.0"}      # or {proposed: "0.3.0", proposed_by: llm|human} or {deprecated_since: ...}
severity: error                       # error | warning | info
precision: very-high                  # very-high | high | medium | low (certainty, separate from severity)
detector:
  kind: regex                         # regex | source | doctree | build-warning | html | llm
  node: paragraph
  pattern: |
    ^\s*>>>\s.*
message: "doctest glued to the preceding paragraph: {match!r}"
fix: {hint: "Insert a blank line before the first '>>>' line.", autofixable: true, strategy: insert-blank-line-before-doctest}
applies_to: {styles: [rest, google, numpy], backends: [sphinx, mkdocs]}
explanation: |
  ## What it does
  ...
  ## Why is this bad?
  ...
references: [https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#doctest-blocks]
```

## Proposing a rule

1. Reproduce the artifact in a minimal docstring and confirm how it renders (`epythet.normalize_text` shows what the build-time normalizer would do; a `--level 2` run shows whether Sphinx warns).
2. Write `DRnnn.yaml` with the next free id, `status: {proposed: "<next epythet version>", proposed_by: human}` (or `llm` when the `docs-reviewer` subagent drafted it), a `detector` of the right kind, `precision` honestly estimated, and the two-part `explanation`.
3. Write the sibling `DRnnn.py` with at least one `# ruleid:` specimen and one `# ok:` control (real Python, importable).
4. Test it against your package without touching epythet: put both files in a directory and run `epythet validate PKG --ledger that/dir`. Proposed rules are loaded but excluded from gating counts until promoted.
5. Open a pull request on epythet with both files. A maintainer promotes the rule by changing `status` to `{stable_since: "<version>"}`.

Level 3 findings from a reviewer are always `proposed`; they never gate and never count.

## Links

- Decision record (levels, ledger design, evidence): https://github.com/i2mint/epythet/discussions/15 (decision D8)
- Tracking issue with baseline counts per rule on real packages: https://github.com/i2mint/epythet/issues/16
- Related skills: `epythet-docstring-style` (what to write instead), `epythet-repair-migrate` (fixing a repository).
