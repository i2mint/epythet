# epythet.config_parser

Legacy configuration accessor kept for the frozen `docsrc/conf.py` copies.

Over a hundred projects committed a `docsrc/conf.py` that does:

```default
project, copyright, author, release, display_name = parse_config(
    Path(__file__).absolute().parent.parent / "setup.cfg"
)
```

That 5-tuple is a published contract, so it stays. New code should use
[`epythet.config.load_config()`](epythet.config.html.md#epythet.config.load_config), which returns the full
[`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig).

### Functions

| [`parse_config`](#epythet.config_parser.parse_config)(config_file)   | Project metadata for Sphinx's `conf.py`, as a 5-tuple.   |
|------------------------------------------------------------------------------|----------------------------------------------------------|

### epythet.config_parser.parse_config(config_file)

Project metadata for Sphinx’s `conf.py`, as a 5-tuple.

`config_file` may be a `setup.cfg` path, a `pyproject.toml` path or the
project directory itself. Whatever is passed, the project directory is what
gets resolved: `pyproject.toml` (with a `[project]` table) wins over
`setup.cfg` when both exist. See [`epythet.config`](epythet.config.html.md#module-epythet.config) for the keys.

`copyright` is an empty string when unset, and the generated docs render no
copyright line in that case.

* **Parameters:**
  **config_file** – `PROJECT_DIR/setup.cfg`, `PROJECT_DIR/pyproject.toml`
  or `PROJECT_DIR`
* **Returns:**
  `(name, copyright, author, version, display_name)`
* **Raises:**
  [**FileNotFoundError**](https://docs.python.org/3/library/exceptions.html#FileNotFoundError) – when neither configuration file exists
