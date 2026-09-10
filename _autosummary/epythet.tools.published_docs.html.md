# epythet.tools.published_docs

Elements for a tool to setup docs and check if docs are published, and if not, why.

```pycon
>>> from epythet.tools.published_docs import published_doc_diagnosis_df
>>> published_doc_diagnosis_df('https://github.com/i2mint/epythet')
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
>>> published_doc_diagnosis_df([
...     'https://github.com/i2mint/epythet', 'https://github.com/myorg/myrepo',
... ])
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
1    https://github.com/myorg/myrepo    https://myorg.github.io/myrepo            False                 False
```

### Functions

| [`branch_exists`](#epythet.tools.published_docs.branch_exists)(repo_stub, branch, \*[, ...])       | Check if a branch exists in a repo.                                                                                                                                                                                                      |
|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`check_pages_setup`](#epythet.tools.published_docs.check_pages_setup)(repo_stub, \*[, ...])           | Diagnose the GitHub Pages setup for a single repo.                                                                                                                                                                                       |
| [`check_token_scopes`](#epythet.tools.published_docs.check_token_scopes)([token, verbose])              | Check the scopes of a GitHub token.                                                                                                                                                                                                      |
| `clog`(condition, \*args, \*\*kwargs)                                                              |                                                                                                                                                                                                                                          |
| [`commit_data`](#epythet.tools.published_docs.commit_data)(repo_stub, branch, \*[, headers])     | Retrieves data about the latest commit on a branch of a GitHub repository.                                                                                                                                                               |
| [`configure_github_pages`](#epythet.tools.published_docs.configure_github_pages)(repo_stub, \*[, ...])      | Configure or update GitHub Pages for a repo.                                                                                                                                                                                             |
| [`configure_github_pages_for_repo_stubs`](#epythet.tools.published_docs.configure_github_pages_for_repo_stubs)(repo_stubs) | Configure Pages for an iterable of repo stubs, or all repos in an organization.                                                                                                                                                          |
| [`default_branch_and_commit_sha`](#epythet.tools.published_docs.default_branch_and_commit_sha)(repo_stub, \*)      | Retrieves the default branch and current commit SHA for a given GitHub repository.                                                                                                                                                       |
| `dflt_headers`([token])                                                                            |                                                                                                                                                                                                                                          |
| [`enable_pages`](#epythet.tools.published_docs.enable_pages)(repo_stub, \*[, branch, path])       | Enable or update GitHub Pages for a repo.                                                                                                                                                                                                |
| [`ensure_branch`](#epythet.tools.published_docs.ensure_branch)(repo_stub, \*, branch[, ...])       | Ensures a branch exists.                                                                                                                                                                                                                 |
| [`github_org_and_repo`](#epythet.tools.published_docs.github_org_and_repo)(github_url)                   |                                                                                                                                                                                                                                          |
| `github_token`([env_var])                                                                          |                                                                                                                                                                                                                                          |
| `is_a_github_repo_root_url`(url)                                                                   |                                                                                                                                                                                                                                          |
| `is_valid_response`(response)                                                                      |                                                                                                                                                                                                                                          |
| [`pages_config`](#epythet.tools.published_docs.pages_config)(repo_stub)                           | Return the GitHub Pages configuration for a repo, or None if not configured.                                                                                                                                                             |
| [`published_doc_diagnosis_df`](#epythet.tools.published_docs.published_doc_diagnosis_df)([urls, url_column])    | The `published_doc_diagnosis_df` gets you a pandas dataframe (requires pandas to be installed!) that will tell you if given github `org/repo` url(s) have published documentation and if a `docs` folder even exists (in master branch). |
| [`repo_data`](#epythet.tools.published_docs.repo_data)(repo_stub, \*[, headers])               | Retrieves data about a GitHub repository.                                                                                                                                                                                                |
| [`repo_stub_from_local_dir`](#epythet.tools.published_docs.repo_stub_from_local_dir)([path])                  | Extract the `owner/repo` slug from a local git checkout's remote URL.                                                                                                                                                                    |
| `repo_stubs_for_org`(org)                                                                          |                                                                                                                                                                                                                                          |
| [`repo_url_to_docs_url`](#epythet.tools.published_docs.repo_url_to_docs_url)(repo_url)                    |                                                                                                                                                                                                                                          |
| [`repo_url_to_repo_docs_url`](#epythet.tools.published_docs.repo_url_to_repo_docs_url)(repo_url)               |                                                                                                                                                                                                                                          |
| `table_url_to_df`(url)                                                                             |                                                                                                                                                                                                                                          |
| `token_user_info`([token, verbose])                                                                |                                                                                                                                                                                                                                          |
| `url_exists`(url)                                                                                  |                                                                                                                                                                                                                                          |
| `url_of_urls_csv_to_urls`(url[, url_column])                                                       |                                                                                                                                                                                                                                          |
| `verify_repo_access`(repo_stub, \*[, verbose])                                                     |                                                                                                                                                                                                                                          |

### epythet.tools.published_docs.branch_exists(repo_stub, branch, \*, headers=<function dflt_headers>, verbose=True)

Check if a branch exists in a repo.

* **Parameters:**
  * **repo_stub** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – A string of the form `org/repo`.
  * **branch** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – The branch name to check for.
  * **headers** (`Union`[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict), [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[], [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)]]) – A function that returns a dictionary of headers

### epythet.tools.published_docs.check_pages_setup(repo_stub, , expected_branch='gh-pages', expected_path='/', check_url=True)

Diagnose the GitHub Pages setup for a single repo.

Returns a dict describing the state of things:

```default
{
    'repo': 'owner/repo',
    'gh_pages_branch_exists': True/False,
    'pages_enabled': True/False,
    'source_branch': 'gh-pages' or None,
    'source_path': '/' or None,
    'correctly_configured': True/False,
    'docs_url': 'https://owner.github.io/repo',
    'docs_url_responding': True/False or None,  # None if not checked
    'diagnosis': 'A human-readable summary of what is wrong (or right).',
}
```

Works with either a `GITHUB_TOKEN` env var or an authenticated `gh` CLI.

```pycon
>>> check_pages_setup('i2mint/epythet')
```

### epythet.tools.published_docs.check_token_scopes(token=None, , verbose=True)

Check the scopes of a GitHub token.

### epythet.tools.published_docs.commit_data(repo_stub, branch, \*, headers=<function dflt_headers>)

Retrieves data about the latest commit on a branch of a GitHub repository.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

### epythet.tools.published_docs.configure_github_pages(repo_stub, \*, target_branch='gh-pages', folder='/', ensure_branch_exists=True, headers=<function dflt_headers>, verbose=True)

Configure or update GitHub Pages for a repo.

### Example

```pycon
>>> configure_github_pages('i2mint/epythet')
```

### epythet.tools.published_docs.configure_github_pages_for_repo_stubs(repo_stubs)

Configure Pages for an iterable of repo stubs, or all repos in an organization.

```pycon
>>> repo_pages_status = dict(
...     configure_github_pages_for_stubs('i2mint')
... )
```

### epythet.tools.published_docs.default_branch_and_commit_sha(repo_stub, \*, headers=<function dflt_headers>)

Retrieves the default branch and current commit SHA for a given GitHub repository.

* **Parameters:**
  * **repo_stub** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The GitHub repository in “owner/repo” format.
  * **headers** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Headers for authentication, e.g., {‘Authorization’: ‘Bearer <token>’}.
* **Returns:**
  A dictionary containing ‘default_branch’ and ‘commit_sha’.
* **Return type:**
  [*dict*](https://docs.python.org/3/library/stdtypes.html#dict)

### epythet.tools.published_docs.enable_pages(repo_stub, , branch='gh-pages', path='/')

Enable or update GitHub Pages for a repo. Uses `gh` CLI or GITHUB_TOKEN.

This is the recommended way to programmatically set up Pages.  Unlike
`configure_github_pages` (which requires `requests` and a token), this
function works out of the box if you have `gh` installed and authenticated.

Returns the API response dict on success, or None on failure.

```pycon
>>> enable_pages('thorwhalen/denote')
```

### epythet.tools.published_docs.ensure_branch(repo_stub, \*, branch, commit_sha=None, headers=<function dflt_headers>, verbose=True)

Ensures a branch exists. Does nothing if it already does, and creates it if not.

* **Parameters:**
  * **repo_stub** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Owner and name of the GitHub repository, e.g., ‘owner/repo’.
  * **branch** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Name of the branch to be created if it doesn’t exist
  * **commit_sha** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Commit SHA to base the new branch on. By default,
    it’s the SHA of the most recent commit of the default branch.
  * **headers** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Headers for authentication, e.g., {‘Authorization’: ‘Bearer <token>’}.
* **Returns:**
  Response from GitHub API as a dictionary.
* **Return type:**
  [*dict*](https://docs.python.org/3/library/stdtypes.html#dict)

### epythet.tools.published_docs.github_org_and_repo(github_url)

```pycon
>>> github_org_and_repo('https://github.com/i2mint/i2')
{'org': 'i2mint', 'repo': 'i2'}
```

### epythet.tools.published_docs.pages_config(repo_stub)

Return the GitHub Pages configuration for a repo, or None if not configured.

Returns a dict with keys like `source` (containing `branch` and `path`),
`html_url`, `build_type`, etc.  Returns `None` when Pages is not enabled.

Works with either a `GITHUB_TOKEN` env var or an authenticated `gh` CLI.

```pycon
>>> pages_config('i2mint/epythet')
{'source': {'branch': 'gh-pages', 'path': '/'}, 'html_url': '...', ...}
```

### epythet.tools.published_docs.published_doc_diagnosis_df(urls=None, url_column='url')

The `published_doc_diagnosis_df` gets you a pandas dataframe (requires pandas to be
installed!) that will tell you if given github `org/repo` url(s) have published
documentation and if a `docs` folder even exists (in master branch).

* **Parameters:**
  * **urls** (`Union`[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)]]) – A list of urls, a table containing urls, or a single url pointing to
    a csv where this table can be downloaded from.
  * **url_column** – When `urls` is a table, what column name contains the urls.
* **Returns:**
  A dataframe with the diagnosis

### epythet.tools.published_docs.repo_data(repo_stub, \*, headers=<function dflt_headers>)

Retrieves data about a GitHub repository.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

### epythet.tools.published_docs.repo_stub_from_local_dir(path='.')

Extract the `owner/repo` slug from a local git checkout’s remote URL.

```pycon
>>> repo_stub_from_local_dir('/path/to/some/git/repo')
'owner/repo'
```

### epythet.tools.published_docs.repo_url_to_docs_url(repo_url)

```pycon
>>> repo_url_to_docs_url('https://github.com/i2mint/i2')
'https://i2mint.github.io/i2'
```

### epythet.tools.published_docs.repo_url_to_repo_docs_url(repo_url)

```pycon
>>> repo_url_to_repo_docs_url('https://github.com/i2mint/i2')
'https://github.com/i2mint/i2/tree/master/docs'
```
