---
name: epythet-setup
description: >-
  Set up documentation for a Python package with epythet: run the quickstart,
  read what it produces, configure `[tool.epythet]` in pyproject.toml, add the
  GitHub Pages publishing workflow, and upgrade a 0.1.x docsrc. Use when asked
  to "add docs", "generate documentation", "set up Sphinx", "publish docs to
  GitHub Pages", "configure epythet", "what does [tool.epythet] accept", or
  when a project has docstrings but no documentation site. Convention over
  configuration: nothing needs to be added to the package.
license: Apache-2.0
metadata:
  audience: users
---

# epythet-setup: documentation for a Python package, with no boilerplate

epythet turns a package's existing conventions (README, docstrings, package layout, `pyproject.toml` metadata) into a Sphinx site plus agent-readable twins. You do not write `conf.py`, `index.rst` or per-module pages.

## The one command

```bash
pip install epythet
epythet quickstart /path/to/project --ignore tests/ scrap/ examples/
```

Open `/path/to/project/docsrc/_build/html/index.html`. The site has:

- a landing page that **is the README** (badges, relative images, GitHub `> [!NOTE]` alerts, mermaid fences all render),
- a **nested API tree** from the package layout, one page per module,
- RST field lists and Google/NumPy sections rendered side by side; types come from annotations,
- a theme with light/dark mode and an accent colour derived from the package name,
- agent outputs: `llms.txt`, a `.md` twin of every page, a flat `<package>.md`, `objects.inv`.

Same from Python:

```python
from epythet import quickstart
quickstart("/path/to/project", ignore=["tests/"])   # returns the html directory
```

## What epythet reads (in this order)

1. `pyproject.toml`: `[project]` for name, version, authors, description, URLs; `[tool.epythet]` for documentation choices.
2. `setup.cfg` `[metadata]` for legacy projects. When both exist, `pyproject.toml` wins.
3. The package directory, found by convention: `<name>/` or `src/<name>/` (hyphens become underscores), else the single top-level package. Set `package_dir` if that guess fails.
4. `README.md` (or `.rst`, `.txt`) for the landing page.

## `[tool.epythet]` reference

All keys optional. Omit the section and you get the defaults shown.

```toml
[tool.epythet]
display_name = "Dol"            # site title; default: the project name
copyright = "2024, Jane Doe"    # footer; default: no copyright line at all
theme = "auto"                  # "auto" | "furo" | "shibuya" | "pydata" | "sphinxawesome" | "book" | "alabaster" | "rtd" | any installed theme
accent = "#3661ac"              # default: derived from the package name (OKLCH, WCAG AA on white by construction)
mode = "auto"                   # "auto" | "light" | "dark"  (where the theme supports forcing it)
ignore = ["tests/", "scrap/", "examples/"]   # path substrings to skip; `--ignore` on the CLI overrides
api_generator = "auto"          # "auto" (autosummary if the package imports, else autoapi) | "autosummary" | "autoapi"
agent_outputs = true            # llms.txt, .md twins, <link rel="alternate"> relations
aggregates = ["md"]             # flat single-document twins at the site root: "md", "pdf"
ai_artifacts = true             # "For AI agents" page when skills / subagents / CLAUDE.md exist
ai_artifacts_template = ""      # project-relative file overriding that page's template
package_dir = "src/dol"         # default: found by convention
docs_dir = "docsrc"             # where the Sphinx sources are generated

[tool.epythet.theme_options]    # verbatim passthrough into Sphinx's html_theme_options; always wins
announcement = "v2 is in beta"
```

Notes agents get wrong:

- `ignore` matches **path substrings**, so `tests/` skips `pkg/tests/` and `pkg/sub/tests/`. Under `autosummary` the ignored modules are still imported once during discovery; if importing them fails, switch to `api_generator = "autoapi"`.
- `theme` and `accent` are the knobs to change a site's look. Never hand-edit `docsrc/conf.py` for that; epythet regenerates it. The `epythet-theme` skill has the decision procedure.
- Unknown keys are a `ConfigError`, so a typo fails fast rather than being ignored.
- `setup.cfg` projects use the same keys under `[tool.epythet]` (or `display_name` / `copyright` under `[metadata]`).

## What gets generated, and what to commit

`epythet quickstart` (or `epythet make-docsrc`) writes `docsrc/` with a two-line `conf.py` shim:

```python
from epythet.sphinx_conf import *  # noqa: F401,F403
```

and an `index.md` that includes the README with a hidden toctree. API pages and agent outputs are produced at build time. **You do not need to commit `docsrc/`**: CI regenerates it. If a repository has a committed 0.1.x `docsrc/` (template `conf.py`, `index.rst`, `table_of_contents.rst`, `module_docs/`, `Makefile`), the next quickstart recognises and replaces it; the recommended sweep step is to delete `docsrc/` and add it to `.gitignore`, keeping it only where hand-written pages exist. A hand-written `conf.py` without the shim import is never overwritten.

Overrides that must survive regeneration go **below the import** in the shim: anything defined there wins over the generated value.

Other commands: `epythet make PROJECT_DIR [html|doctest|markdown|github|clean]` runs `sphinx-build` with the current interpreter (`github` copies HTML into `PROJECT_DIR/docs`). `epythet validate PROJECT_DIR` checks docstrings (see `epythet-validate`). `epythet ai-artifacts PROJECT_DIR` lists a repo's skills and agents (see `epythet-ai-artifacts`).

## Publishing to GitHub Pages

Add `.github/workflows/publish-docs.yml`:

```yaml
name: GitHub Pages
on:
  workflow_run:
    workflows: ["Continuous Integration"]
    types: [completed]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: i2mint/epythet/actions/publish-github-pages@master
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          ignore: "tests/,scrap/,examples/"
          python-version: "3.12"
```

The action installs epythet and the project, runs `epythet quickstart . --ignore ...`, pushes `docsrc/_build/html/` to the `gh-pages` branch, and enables Pages. If the site 404s after the first run, Pages was not enabled: run `epythet configure-pages owner/repo` (the `epythet-pages` skill covers diagnosis).

Fleet note: until epythet 0.2 is validated across the fleet, the `@master` action pins `epythet<0.2`; sites built by it keep the 0.1.x look. Local builds use whatever epythet is installed.

## Docstring conventions the site rewards

epythet's build-time normalizer fixes the common slips (doctest glued to prose, Markdown fences, `Returns: text` one-liners, `## Heading`, `*args` in prose, `[text](url)`), so existing docstrings render. New docstrings should follow the dialect in the `epythet-docstring-style` skill: Google sections, doctests as examples, types in annotations only.

## Checklist for a new project

1. `pyproject.toml` has `[project] name` and a GitHub URL in `[project.urls]` (the URL drives "GitHub" links and the Pages URL).
2. `epythet quickstart . --ignore tests/` builds without a `ConfigError`.
3. Landing page shows the README; sidebar shows the module tree; `docsrc/_build/html/llms.txt` and `<name>.md` exist.
4. `epythet validate .` is clean at `--fail-on error`, or its findings are filed.
5. Add the workflow, push, then `epythet check-pages owner/repo`.
6. Add `docsrc/` to `.gitignore` unless it holds hand-written pages.
