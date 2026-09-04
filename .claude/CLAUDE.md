# Epythet

Documentation generation and publishing tools built on Sphinx.
"Less humdrum, more automation, earlier at the pub."

## What epythet does

1. **Generates Sphinx docs** from Python docstrings (`make_docsrc`, `make_autodocs`, `make`)
2. **Publishes to GitHub Pages** via a CI action (`actions/publish-github-pages`)
3. **Diagnoses and repairs** docstring formatting issues (`repair_package`, `diagnose_doctest_code_blocks`)
4. **Manages GitHub Pages settings** programmatically (`check_pages_setup`, `enable_pages`, `configure_pages`)

## Architecture

```
epythet/
  __init__.py          # Re-exports from submodules
  cli.py               # argh-based CLI: epythet {make-docsrc,make-autodocs,make,quickstart,check-pages,configure-pages}
  autogen.py           # RST generation from module docstrings
  setup_docsrc.py      # One-time Sphinx docsrc scaffolding
  call_make.py         # Thin wrapper around Sphinx's Makefile
  config_parser.py     # Reads project metadata from setup.cfg or pyproject.toml
  templates.py         # RST templates (RstTitle, AutoDocs enums)
  _static/             # Static files copied into docsrc
  tools/
    __init__.py        # Re-exports diagnosis and pages tools
    docstring_diagnosis.py  # Detects/repairs missing blank lines before doctests
    published_docs.py       # GitHub Pages config, diagnosis, and publishing checks
actions/
  publish-github-pages/action.yml  # Composite GitHub Action for CI docs publishing
```

## Key conventions

- **CLI** uses `argh`. Each CLI command is a plain function decorated with `@argh.arg` as needed, added to the `argh_kwargs["functions"]` list in `cli.py`.
- **GitHub API access** has dual paths: uses `GITHUB_TOKEN` env var + `requests` when available, falls back to `gh` CLI subprocess. The `_github_api_get` and `_github_api_request` helpers in `published_docs.py` handle this.
- **Config parsing** supports both `setup.cfg` (`[metadata]` section) and `pyproject.toml` (`[project]` section). The `[tool.epythet]` section in pyproject.toml can override copyright/display_name.
- **Optional dependencies**: `pandas` (for `published_doc_diagnosis_df`), `hubcap` (for org-level repo listing), `tec` (for flexible package reading in `repair_package`). These are imported lazily and guarded by `suppress(ImportError)`.

## Testing

```bash
pytest tests/ -v
python -m doctest epythet/tools/docstring_diagnosis.py
```

## Common repo_stub pattern

Many functions take a `repo_stub` (e.g., `"owner/repo"`). The `repo_stub_from_local_dir(path)` utility extracts this from a local `.git/config`.

## GitHub Pages setup flow

The most common issue: CI pushes docs to the `gh-pages` branch, but Pages isn't
enabled in repo settings. The target setting is **source branch `gh-pages`,
folder `/ (root)`**. The fix is:

```python
from epythet import enable_pages

enable_pages("owner/repo")  # uses gh CLI or GITHUB_TOKEN
```

Or via CLI: `epythet configure-pages owner/repo`

### Raw `gh` equivalent

`enable_pages` is a thin wrapper over the GitHub Pages REST API. The equivalent
of clicking *Settings > Pages → Branch `gh-pages`, folder `/ (root)` → Save* is:

```bash
# Read current config (empty/404 means Pages is NOT enabled — GitHub's default)
gh api repos/OWNER/REPO/pages --jq '{branch:.source.branch, path:.source.path}'

# Enable Pages — POST creates the Pages site (use when Pages is not yet enabled)
gh api repos/OWNER/REPO/pages -X POST -f 'source[branch]=gh-pages' -f 'source[path]=/'

# Change an existing Pages config — PUT updates it (use when Pages already exists)
gh api repos/OWNER/REPO/pages -X PUT  -f 'source[branch]=gh-pages' -f 'source[path]=/'
```

`enable_pages` tries `POST` first and falls back to `PUT` if Pages already
exists. See `_gh_api` / `_flatten_json` in `epythet/tools/published_docs.py`,
which turn the nested `{"source": {"branch": ..., "path": ...}}` body into
`gh api`'s `source[branch]=…` / `source[path]=…` bracket form.
