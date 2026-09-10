---
name: epythet-pages
description: >-
  Diagnose and fix GitHub Pages publishing for Python documentation built with
  epythet (or any Sphinx site pushed to a gh-pages branch). Use when docs give a
  404, the site does not update, Pages is not enabled, the gh-pages branch is
  missing, the docs CI fails, or when enabling Pages for one repo or every repo
  in an organisation. Covers `epythet check-pages`, `epythet configure-pages`,
  the Python API, the raw `gh api` equivalent, and batch operations.
license: Apache-2.0
metadata:
  audience: users
---

# epythet-pages: GitHub Pages diagnosis and repair

## Prerequisites

- `pip install epythet`
- `gh` CLI installed and authenticated (recommended), or a `GITHUB_TOKEN` environment variable with repo administration rights.

## "My docs page gives a 404"

The most common cause: CI built the docs and pushed the `gh-pages` branch, but GitHub Pages was never enabled in the repository settings. The target setting is **source branch `gh-pages`, folder `/ (root)`**.

Diagnose:

```bash
epythet check-pages owner/repo        # or a local checkout: epythet check-pages .
```

```python
from epythet import check_pages_setup
result = check_pages_setup("owner/repo")
print(result["diagnosis"])
```

The result dict has `gh_pages_branch_exists`, `pages_enabled`, `source_branch`, `source_path`, `correctly_configured`, `docs_url`, `docs_url_responding` and a one-line `diagnosis`.

| Diagnosis | Fix |
|---|---|
| gh-pages branch exists but Pages NOT enabled | `epythet configure-pages owner/repo` |
| Pages configured with wrong branch/path | `epythet configure-pages owner/repo` (updates the existing config) |
| gh-pages branch does not exist | CI has not run or failed: check the Actions tab; check the workflow trigger (`workflow_run` needs the named CI workflow to exist and complete) |
| Pages configured but URL not responding | Wait a few minutes for the Pages deploy, or re-run the workflow |
| `docs_url_responding` false, everything else true | Cached 404: reload without cache; check `index.html` exists at the branch root |

Fix:

```bash
epythet configure-pages owner/repo                    # branch gh-pages, path /
epythet configure-pages owner/repo -b docs -p /site   # other branch or folder
```

```python
from epythet import enable_pages
enable_pages("owner/repo")
```

`enable_pages` tries `POST` (create the Pages site) and falls back to `PUT` (update an existing one), so it is idempotent.

## The raw `gh` equivalent

`configure-pages` is a thin wrapper over the GitHub Pages REST API. Clicking *Settings > Pages, branch `gh-pages`, folder `/ (root)`, Save* is:

```bash
# Read the current config (404 means Pages is NOT enabled, GitHub's default)
gh api repos/OWNER/REPO/pages --jq '{branch:.source.branch, path:.source.path}'

# Enable Pages (POST creates the site; use when it is not yet enabled)
gh api repos/OWNER/REPO/pages -X POST -f 'source[branch]=gh-pages' -f 'source[path]=/'

# Change an existing config (PUT)
gh api repos/OWNER/REPO/pages -X PUT -f 'source[branch]=gh-pages' -f 'source[path]=/'
```

## Setting up publishing from scratch

1. Build locally once to check the project configures: `epythet quickstart . --ignore tests/ scrap/ examples/`.
2. Add `.github/workflows/publish-docs.yml` using `i2mint/epythet/actions/publish-github-pages@master` (the `epythet-setup` skill has the file). Inputs: `github-token` (required), `ignore`, `python-version`, `docs-branch` (default `gh-pages`), `docs-dir` (default `./docsrc/_build/html/`).
3. Push; after the workflow runs, `epythet check-pages owner/repo`. The action also calls the Pages API itself, so usually nothing more is needed.
4. The site is at `https://OWNER.github.io/REPO/`. Its agent outputs are at `/llms.txt` and `/<package>.md`.

## Batch operations across an organisation

Requires `pip install hubcap` for the org listing.

```python
from epythet.tools.published_docs import check_pages_setup, enable_pages, repo_stubs_for_org

for stub in repo_stubs_for_org("myorg"):
    result = check_pages_setup(stub, check_url=False)
    if result["gh_pages_branch_exists"] and not result["pages_enabled"]:
        enable_pages(stub)
        print(f"Enabled Pages for {stub}")
```

`published_doc_diagnosis_df(org)` (needs pandas) returns the same diagnosis for every repo as a DataFrame.

## Local checkouts

Every command accepts a local directory instead of `owner/repo`; the repo is read from `remote.origin.url` in `.git/config`:

```bash
epythet check-pages .
epythet configure-pages /path/to/project
```

`epythet.repo_stub_from_local_dir(path)` is the function behind it.

## Docstrings render wrongly on the published site

That is a source problem, not a Pages problem. `epythet validate PROJECT_DIR` names the artifacts and their fixes (`epythet-validate` skill); `epythet.repair_package(path, write_to_files=True)` inserts the missing blank lines before doctests (`epythet-repair-migrate` skill).

## Function reference

| Function | Purpose |
|---|---|
| `check_pages_setup(repo_stub, check_url=True)` | Full diagnosis dict |
| `pages_config(repo_stub)` | Raw GitHub Pages API response (`None` when not enabled) |
| `enable_pages(repo_stub, branch="gh-pages", path="/")` | Enable or update the Pages source |
| `configure_github_pages(repo_stub)` | Older variant that requires `GITHUB_TOKEN` |
| `repo_stub_from_local_dir(path)` | `owner/repo` from a local git checkout |
| `repo_stubs_for_org(org)` | Every repo of an organisation (needs `hubcap`) |
