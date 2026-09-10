# epythet

Beautiful, correct documentation from a Python package, with no boilerplate.

Point epythet at a project and its conventions (README, docstrings, package
layout, `pyproject.toml` metadata) produce the site:

```default
epythet quickstart PROJECT_DIR --ignore tests/ scrap/ examples/
```

which writes `PROJECT_DIR/docsrc/_build/html/`: a landing page that *is* the
README, a nested API tree, a light/dark theme with an accent derived from the
package name, and agent-facing twins (`llms.txt`, a `.md` per page, a flat
`<package>.md`, `objects.inv`).

The same, from Python:

```default
from epythet import quickstart
quickstart(PROJECT_DIR, ignore=["tests/"])
```

Or step by step: `make_docsrc()` writes `docsrc/` (a two-line `conf.py`
shim and `index.md`), `make()` runs Sphinx (`html` by default). All
configuration lives in `[tool.epythet]` of `pyproject.toml`; see
[`epythet.config`](epythet.config.html.md#module-epythet.config) for the keys and [`epythet.themes`](epythet.themes.html.md#module-epythet.themes) for the themes.

Rendering fixes for common docstring slips (a doctest glued to the prose above
it, a Markdown fence, `Returns: text` on one line, a stray `*args`) are
applied at build time by [`epythet.normalizer`](epythet.normalizer.html.md#module-epythet.normalizer), so existing docstrings
render correctly without edits.

GitHub Pages helpers (`check_pages_setup()`, `enable_pages()`) and
docstring diagnosis tools (`diagnose_doctest_code_blocks()`,
`repair_package()`) live in [`epythet.tools`](epythet.tools.html.md#module-epythet.tools).

### Functions

| [`quickstart`](#epythet.quickstart)(project_dir, \*[, ignore])   | Scaffold `docsrc` and build the HTML site; returns the output directory.   |
|------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|

### epythet.quickstart(project_dir, , ignore=None)

Scaffold `docsrc` and build the HTML site; returns the output directory.

* **Parameters:**
  * **project_dir** – the project root
  * **ignore** – path substrings to skip (default: `[tool.epythet] ignore`)

### Modules

| [`agent_outputs`](epythet.agent_outputs.html.md#module-epythet.agent_outputs)              | Agent-facing outputs: `llms.txt`, Markdown twins, link relations, aggregates.                                                        |
|----------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| [`build`](epythet.build.html.md#epythet.build)(config[, target, overrides])        | Run one build target for a loaded configuration; returns the output directory.                                                       |
| [`call_make`](epythet.call_make.html.md#module-epythet.call_make)                      | Compatibility module: `make` now lives in [`epythet.build`](epythet.build.html.md#epythet.build).              |
| [`cli`](epythet.cli.html.md#module-epythet.cli)                                  | Command line access to epythet.                                                                                                      |
| [`confgen`](epythet.confgen.html.md#module-epythet.confgen)                          | Generate the Sphinx configuration from a [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig).      |
| [`config`](epythet.config.html.md#module-epythet.config)                            | Single source of truth for a project's documentation configuration.                                                                  |
| [`config_parser`](epythet.config_parser.html.md#module-epythet.config_parser)              | Legacy configuration accessor kept for the frozen `docsrc/conf.py` copies.                                                           |
| [`docs_gen`](epythet.docs_gen.html.md#module-epythet.docs_gen)                        | Documentation generation entry points (re-exported for compatibility).                                                               |
| [`normalizer`](epythet.normalizer.html.md#module-epythet.normalizer)                    | Build-time docstring normalizer: fix the markup artifacts people actually write.                                                     |
| [`scaffold`](epythet.scaffold.html.md#epythet.scaffold)(config, \*[, verbose, pages]) | Write the docsrc files for an already-loaded configuration.                                                                          |
| [`setup_docsrc`](epythet.setup_docsrc.html.md#module-epythet.setup_docsrc)                | Compatibility module: `make_docsrc` now lives in [`epythet.scaffold`](epythet.scaffold.html.md#epythet.scaffold). |
| [`sphinx_conf`](epythet.sphinx_conf.html.md#module-epythet.sphinx_conf)                  | The star-import target for a project's `docsrc/conf.py`.                                                                             |
| [`sphinx_ext`](epythet.sphinx_ext.html.md#module-epythet.sphinx_ext)                    | epythet's Sphinx extension: the normalizer, agent link relations and theme CSS.                                                      |
| [`templates`](epythet.templates.html.md#module-epythet.templates)                      | Text templates for the generated `docsrc` files.                                                                                     |
| [`themes`](epythet.themes.html.md#module-epythet.themes)                            | Theme registry, deterministic theme choice, and the OKLCH accent palette.                                                            |
| [`tools`](epythet.tools.html.md#module-epythet.tools)                              | Tools to diagnose (and sometimes, repair) documentation                                                                              |
| [`validation`](epythet.validation.html.md#module-epythet.validation)                    | `epythet validate`: tiered documentation validation with a growing artifact ledger.                                                  |
