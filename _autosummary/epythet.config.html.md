# epythet.config

Single source of truth for a project’s documentation configuration.

Everything epythet needs to build a site comes from two places, read in this
order of precedence:

1. `pyproject.toml`: the `[project]` table for name, version and authors,
   and the `[tool.epythet]` table for documentation choices.
2. `setup.cfg`: the `[metadata]` section (legacy projects).

When both files exist, `pyproject.toml` wins as soon as it has a `[project]`
table. (epythet 0.1.x silently preferred `setup.cfg`, which was wrong for the
projects that had migrated to `pyproject.toml` but kept a stale `setup.cfg`.)

The result is a [`DocsConfig`](#epythet.config.DocsConfig), an immutable dataclass. The legacy 5-tuple
accessor [`epythet.config_parser.parse_config()`](epythet.config_parser.html.md#epythet.config_parser.parse_config) is derived from it and keeps
its signature, so old `docsrc/conf.py` copies keep working.

The `[tool.epythet]` keys, all optional:

```default
[tool.epythet]
display_name = "Dol"          # site title; default: the project name
copyright = "2024, Jane Doe"  # footer line; default: none rendered
theme = "auto"                # "auto" | "furo" | "shibuya" | ... | any installed theme
accent = "#3661ac"            # default: derived from the package name (OKLCH)
mode = "auto"                 # "auto" | "light" | "dark"
ignore = ["tests/", "scrap/", "examples/"]  # path substrings to skip
api_generator = "autosummary" # "autosummary" (imports the package) | "autoapi" (static)
agent_outputs = true          # llms.txt + .md twins of every page
aggregates = ["md"]           # flat single-document twins at the site root
ai_artifacts = true           # "For AI agents" page when skills/agents/CLAUDE.md exist
ai_artifacts_template = ""    # project-relative file overriding that page's template
package_dir = "src/dol"       # default: found by convention
docs_dir = "docsrc"           # where the Sphinx sources live

[tool.epythet.theme_options]  # verbatim passthrough into html_theme_options
announcement = "v2 is in beta"
```

```pycon
>>> import tempfile, pathlib
>>> d = pathlib.Path(tempfile.mkdtemp())
>>> _ = (d / "pyproject.toml").write_text('''
... [project]
... name = "my-pkg"
... version = "1.2.3"
... authors = [{name = "Jane Doe"}]
... [tool.epythet]
... theme = "furo"
... ''')
>>> _ = (d / "my_pkg").mkdir()
>>> _ = (d / "my_pkg" / "__init__.py").write_text("")
>>> cfg = load_config(d)
>>> cfg.name, cfg.version, cfg.author, cfg.theme, cfg.package_dir.name
('my-pkg', '1.2.3', 'Jane Doe', 'furo', 'my_pkg')
```

### Module Attributes

| [`DEFAULT_IGNORE`](#epythet.config.DEFAULT_IGNORE)         | Path substrings skipped by default when discovering modules to document.       |
|-------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`DEFAULT_DOCS_DIR`](#epythet.config.DEFAULT_DOCS_DIR)       | Directory under the project root holding the Sphinx sources.                   |
| [`PACKAGE_DIR_CANDIDATES`](#epythet.config.PACKAGE_DIR_CANDIDATES) | Directory candidates (relative to the project root) that may hold the package. |
| [`NON_PACKAGE_DIRS`](#epythet.config.NON_PACKAGE_DIRS)       | Top-level directories never taken for the package when guessing by convention. |

### Functions

| [`find_package_dir`](#epythet.config.find_package_dir)(project_dir, name)     | Locate the package directory for `name` under `project_dir` by convention.   |
|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`load_config`](#epythet.config.load_config)(project_dir, \*\*overrides) | Read a project's documentation configuration.                                |

### Classes

| [`DocsConfig`](#epythet.config.DocsConfig)(project_dir, name[, version, ...])   | Everything needed to generate a project's documentation.   |
|--------------------------------------------------------------------------------------------------|------------------------------------------------------------|

### Exceptions

| [`ConfigError`](#epythet.config.ConfigError)   | A project's documentation configuration is missing or invalid.   |
|----------------------------------------------------------------|------------------------------------------------------------------|

### *exception* epythet.config.ConfigError

Bases: [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

A project’s documentation configuration is missing or invalid.

### epythet.config.DEFAULT_DOCS_DIR *= 'docsrc'*

Directory under the project root holding the Sphinx sources.

### epythet.config.DEFAULT_IGNORE *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('tests/', 'scrap/', 'examples/')*

Path substrings skipped by default when discovering modules to document.

### *class* epythet.config.DocsConfig(project_dir, name, version='', author='', description='', display_name='', copyright='', repo_url='', theme='auto', accent='', mode='auto', theme_options=<factory>, ignore=('tests/', 'scrap/', 'examples/'), api_generator='autosummary', agent_outputs=True, aggregates=('md', ), ai_artifacts=True, ai_artifacts_template='', package_dir=None, docs_dir='docsrc')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Everything needed to generate a project’s documentation.

Attributes mirror the `[tool.epythet]` keys; see the module docstring.
`project_dir` and `package_dir` are absolute paths.

#### *property* docsrc_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

Absolute path of the Sphinx source directory.

#### *property* legacy_tuple *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]*

The 5-tuple that [`epythet.config_parser.parse_config()`](epythet.config_parser.html.md#epythet.config_parser.parse_config) returns.

#### *property* package_name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The importable package name (`my-pkg` becomes `my_pkg`).

#### with_overrides(\*\*changes)

A copy with some fields replaced (`None` values are ignored).

* **Return type:**
  [`DocsConfig`](#epythet.config.DocsConfig)

### epythet.config.NON_PACKAGE_DIRS *= frozenset({'docs', 'docsrc', 'examples', 'misc', 'scrap', 'test', 'tests'})*

Top-level directories never taken for the package when guessing by convention.

### epythet.config.PACKAGE_DIR_CANDIDATES *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('{name}', 'src/{name}')*

Directory candidates (relative to the project root) that may hold the package.

### epythet.config.find_package_dir(project_dir, name)

Locate the package directory for `name` under `project_dir` by convention.

Tries `<name>/` then `src/<name>/` (with `-` mapped to `_`), returning
the first that contains an `__init__.py`; `None` when nothing matches.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> find_package_dir("/nonexistent", "nothing") is None
True
```

### epythet.config.load_config(project_dir, \*\*overrides)

Read a project’s documentation configuration.

* **Parameters:**
  * **project_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – the project root (holding `pyproject.toml` or `setup.cfg`),
    or a path to one of those files.
  * **overrides** – field values that win over the files (`None` is ignored),
    e.g. `ignore=["tests/"]` from a command line flag.
* **Raises:**
  [**ConfigError**](#epythet.config.ConfigError) – when neither configuration file is found.
* **Return type:**
  [`DocsConfig`](#epythet.config.DocsConfig)
