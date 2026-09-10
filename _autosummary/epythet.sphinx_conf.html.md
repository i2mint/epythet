# epythet.sphinx_conf

The star-import target for a project’s `docsrc/conf.py`.

A generated `conf.py` is two lines:

```default
from epythet.sphinx_conf import *  # noqa: F401,F403
# optional overrides below, e.g. html_theme = "alabaster"
```

Importing this module locates the project (the `EPYTHET_PROJECT_DIR`
environment variable, else the nearest ancestor of the current directory with a
`pyproject.toml` or `setup.cfg`; Sphinx runs `conf.py` from the source
directory), loads its [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig), applies any overrides
passed in the `EPYTHET_OVERRIDES` environment variable (JSON, set by
[`epythet.build`](epythet.build.html.md#epythet.build) for command-line flags such as `--ignore`), and exports
the settings from [`epythet.confgen.sphinx_settings()`](epythet.confgen.html.md#epythet.confgen.sphinx_settings) as module globals.

### Module Attributes

| [`PROJECT_DIR_ENV`](#epythet.sphinx_conf.PROJECT_DIR_ENV)   | Environment variable naming the project root (set by `epythet make`).                                                            |
|--------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| [`OVERRIDES_ENV`](#epythet.sphinx_conf.OVERRIDES_ENV)     | Environment variable carrying JSON config overrides (set by `epythet make`).                                                     |
| [`epythet_config`](#epythet.sphinx_conf.epythet_config)    | The [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig) this configuration was generated from. |

### epythet.sphinx_conf.OVERRIDES_ENV *= 'EPYTHET_OVERRIDES'*

Environment variable carrying JSON config overrides (set by `epythet make`).

### epythet.sphinx_conf.PROJECT_DIR_ENV *= 'EPYTHET_PROJECT_DIR'*

Environment variable naming the project root (set by `epythet make`).

### epythet.sphinx_conf.epythet_config *= DocsConfig(project_dir=PosixPath('/home/runner/work/epythet/epythet'), name='epythet', version='0.2.0', author='', description='Beautiful, correct documentation from a Python package, with no boilerplate: Sphinx, README landing page, nested API tree, themes, docstring normalizer, agent-facing outputs, GitHub Pages', display_name='epythet', copyright='', repo_url='https://github.com/i2mint/epythet', theme='auto', accent='', mode='auto', theme_options={}, ignore=('tests/,scrap/,examples/',), api_generator='autosummary', agent_outputs=True, aggregates=('md',), package_dir=PosixPath('/home/runner/work/epythet/epythet/epythet'), docs_dir='docsrc')*

The [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig) this configuration was generated from.
