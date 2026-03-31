"""

Elements for a tool to setup docs and check if docs are published, and if not, why.

>>> from epythet.tools.published_docs import published_doc_diagnosis_df
>>> published_doc_diagnosis_df('https://github.com/i2mint/epythet')  # doctest: +SKIP
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
>>> published_doc_diagnosis_df([  # doctest: +SKIP
...     'https://github.com/i2mint/epythet', 'https://github.com/otosense/omisc',
... ])
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
1  https://github.com/otosense/omisc  https://otosense.github.io/omisc            False                 False

"""

from functools import partial
import requests
from io import BytesIO
import re
from typing import Union
from collections.abc import Iterable, Callable

Url = str
Urls = Iterable[Url]
Table = Union[Url, Urls, Iterable[Iterable]]
Headers = dict
HeadersFunc = Callable[[], Headers]
HeadersSpec = Union[Headers, HeadersFunc]

github_url_p = re.compile(r"https?://github.com/(?P<org>[^/]+)/(?P<repo>[^/]+).*?")
github_root_url_p = re.compile(r"^https?://github.com/[^/]+/[^/]+/?$")

# -----------------------------------------------------------------------------------
# gh-pages
# TODO: A lot of tools herein are more general than epythet, and should be moved to
# hubcap, and refactored to not have so many repetitions (e.g. should centralize
# the url templates, factor out headers, etc.)

import requests
import os
import shutil
import subprocess
import json
from warnings import warn

DFLT_DOCS_BRANCH = "gh-pages"
DFLT_DOCS_FOLDER = "/"
DFLT_VERBOSE = True

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def clog(condition, *args, **kwargs):
    if condition:
        print(*args, **kwargs)


# ---------------------------------------------------------------------------
# gh CLI integration
# ---------------------------------------------------------------------------

GH_NOT_FOUND_MSG = (
    "The 'gh' CLI tool was not found on your system. "
    "Install it from https://cli.github.com/ and authenticate with 'gh auth login'. "
    "Alternatively, set the GITHUB_TOKEN environment variable for direct API access."
)


def _gh_is_available():
    """Return True if the ``gh`` CLI is installed and on PATH."""
    return shutil.which("gh") is not None


def _ensure_gh():
    """Raise a helpful error if ``gh`` is not installed."""
    if not _gh_is_available():
        raise EnvironmentError(GH_NOT_FOUND_MSG)


def _gh_api(endpoint, *, method="GET", data=None):
    """Call ``gh api`` and return parsed JSON, or None on 404.

    Raises ``EnvironmentError`` if ``gh`` is not installed and
    ``subprocess.CalledProcessError`` for non-404 failures.
    """
    _ensure_gh()
    cmd = ["gh", "api", endpoint, "-X", method]
    if data is not None:
        for key, value in _flatten_json(data):
            cmd.extend(["-f", f"{key}={value}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if "404" in result.stderr or '"status":"404"' in (result.stdout or ""):
            return None
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def _flatten_json(d, prefix=""):
    """Flatten nested dict into gh-api -f key=value pairs.

    >>> list(_flatten_json({"source": {"branch": "gh-pages", "path": "/"}}))
    [('source[branch]', 'gh-pages'), ('source[path]', '/')]
    """
    for k, v in d.items():
        full_key = f"{prefix}[{k}]" if prefix else k
        if isinstance(v, dict):
            yield from _flatten_json(v, full_key)
        else:
            yield full_key, str(v)


# ---------------------------------------------------------------------------
# GitHub API helpers -- use gh CLI when GITHUB_TOKEN is not set
# ---------------------------------------------------------------------------


def _github_api_get(endpoint, *, headers=None):
    """GET a GitHub API endpoint, preferring GITHUB_TOKEN, falling back to gh CLI."""
    if headers is not None or os.getenv("GITHUB_TOKEN"):
        headers = headers or dflt_headers()
        resp = requests.get(f"https://api.github.com/{endpoint}", headers=headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    return _gh_api(endpoint)


def _github_api_request(endpoint, *, method="POST", data=None, headers=None):
    """Make a GitHub API request, preferring GITHUB_TOKEN, falling back to gh CLI."""
    if headers is not None or os.getenv("GITHUB_TOKEN"):
        headers = headers or dflt_headers()
        url = f"https://api.github.com/{endpoint}"
        resp = requests.request(method, url, headers=headers, json=data)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()
    return _gh_api(endpoint, method=method, data=data)


# ---------------------------------------------------------------------------
# Pages diagnosis and configuration (gh-friendly)
# ---------------------------------------------------------------------------


def pages_config(repo_stub):
    """Return the GitHub Pages configuration for a repo, or None if not configured.

    Returns a dict with keys like ``source`` (containing ``branch`` and ``path``),
    ``html_url``, ``build_type``, etc.  Returns ``None`` when Pages is not enabled.

    Works with either a ``GITHUB_TOKEN`` env var or an authenticated ``gh`` CLI.

    >>> pages_config('i2mint/epythet')  # doctest: +SKIP
    {'source': {'branch': 'gh-pages', 'path': '/'}, 'html_url': '...', ...}
    """
    return _github_api_get(f"repos/{repo_stub}/pages")


def check_pages_setup(
    repo_stub,
    *,
    expected_branch=DFLT_DOCS_BRANCH,
    expected_path=DFLT_DOCS_FOLDER,
    check_url=True,
):
    """Diagnose the GitHub Pages setup for a single repo.

    Returns a dict describing the state of things::

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

    Works with either a ``GITHUB_TOKEN`` env var or an authenticated ``gh`` CLI.

    >>> check_pages_setup('i2mint/epythet')  # doctest: +SKIP
    """
    org, repo = repo_stub.split("/")
    docs_url = f"https://{org}.github.io/{repo}"

    result = {
        "repo": repo_stub,
        "gh_pages_branch_exists": False,
        "pages_enabled": False,
        "source_branch": None,
        "source_path": None,
        "correctly_configured": False,
        "docs_url": docs_url,
        "docs_url_responding": None,
    }

    # Check if the expected branch exists
    branch_info = _github_api_get(
        f"repos/{repo_stub}/branches/{expected_branch}"
    )
    result["gh_pages_branch_exists"] = branch_info is not None

    # Check pages config
    config = pages_config(repo_stub)
    if config is not None:
        result["pages_enabled"] = True
        source = config.get("source", {})
        result["source_branch"] = source.get("branch")
        result["source_path"] = source.get("path")
        result["correctly_configured"] = (
            result["source_branch"] == expected_branch
            and result["source_path"] == expected_path
        )

    # Optionally check if docs URL actually responds
    if check_url:
        try:
            resp = requests.get(docs_url, timeout=10)
            result["docs_url_responding"] = resp.status_code == 200
        except requests.RequestException:
            result["docs_url_responding"] = False

    # Build human-readable diagnosis
    result["diagnosis"] = _build_diagnosis(result, expected_branch, expected_path)

    return result


def _build_diagnosis(result, expected_branch, expected_path):
    """Build a human-readable diagnosis string from check_pages_setup results."""
    repo = result["repo"]

    url_responding = result["docs_url_responding"]

    if result["correctly_configured"] and url_responding:
        return f"{repo}: All good -- Pages configured and docs are live."

    if result["correctly_configured"] and url_responding is None:
        return f"{repo}: Pages correctly configured (URL check skipped)."

    issues = []

    if not result["gh_pages_branch_exists"]:
        issues.append(
            f"The '{expected_branch}' branch does not exist. "
            "The CI docs job may not have run yet, or it failed."
        )

    if not result["pages_enabled"]:
        if result["gh_pages_branch_exists"]:
            issues.append(
                f"GitHub Pages is NOT enabled, but the '{expected_branch}' branch "
                "exists. This is the most common issue -- just enable Pages."
            )
        else:
            issues.append("GitHub Pages is NOT enabled.")
    elif not result["correctly_configured"]:
        issues.append(
            f"Pages is enabled but configured with "
            f"branch='{result['source_branch']}', path='{result['source_path']}' "
            f"instead of branch='{expected_branch}', path='{expected_path}'."
        )

    if result["correctly_configured"] and url_responding is False:
        issues.append(
            "Pages is correctly configured but the docs URL is not responding. "
            "It may need a few minutes after initial setup, or the CI docs job "
            "may have failed."
        )

    return f"{repo}: " + " | ".join(issues) if issues else f"{repo}: Unknown state."


def github_token(env_var="GITHUB_TOKEN"):
    token = os.getenv(env_var)
    if token is None:
        raise ValueError(
            "GITHUB_TOKEN is not set. You can set it as an environment variable."
        )
    return token


def dflt_headers(token=None):
    if token is None:
        token = github_token()
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _get_obj(obj_spec):
    """
    Get the object from the object spec.

    If the object spec is a callable, call it (with no args) to get the object.
    Otherwise, return the object spec as is.

    >>> _get_obj(3)
    3
    >>> _get_obj(lambda: 3)
    3

    """
    if callable(obj_spec):
        return obj_spec()
    return obj_spec


def token_user_info(token=None, *, verbose=DFLT_VERBOSE):
    _clog = partial(clog, verbose)
    response = requests.get("https://api.github.com/user", headers=dflt_headers(token))

    if response.status_code == 200:
        _clog("Token is valid.")
    else:
        _clog(f"Failed to authenticate: {response.status_code}")

    return response.json()


def check_token_scopes(token=None, *, verbose=DFLT_VERBOSE):
    """
    Check the scopes of a GitHub token.
    """
    _clog = partial(clog, verbose)

    url = "https://api.github.com/user"
    headers = dflt_headers(token)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        scopes = response.headers.get("X-OAuth-Scopes", "No scopes found")
        _clog("Token scopes:", scopes)
        return scopes.split(", ")
    else:
        _clog("Failed to retrieve token scopes. Status code:", response.status_code)
        _clog(response.json())
        return None


def verify_repo_access(repo_stub, *, verbose=DFLT_VERBOSE):
    _clog = partial(clog, verbose)
    url = f"https://api.github.com/repos/{repo_stub}"
    response = requests.get(url, headers=dflt_headers())

    if response.status_code == 200:
        _clog(f"Access to {repo_stub} verified.")
    else:
        _clog(f"Failed to access {repo_stub}: {response.status_code}")

    return response.json()


def branch_exists(
    repo_stub: str,
    branch: str,
    *,
    headers: HeadersSpec = dflt_headers,
    verbose=DFLT_VERBOSE,
):
    """
    Check if a branch exists in a repo.

    :param repo_stub: A string of the form ``org/repo``.
    :param branch: The branch name to check for.
    :param headers: A function that returns a dictionary of headers
    """
    _clog = partial(clog, verbose)

    url = f"https://api.github.com/repos/{repo_stub}/branches/{branch}"
    response = requests.get(url, headers=_get_obj(headers))
    if response.status_code == 200:
        return True
    else:
        _clog(
            f"{repo_stub} {branch} branch doesn't exist: {response.status_code}, {response.content=}"
        )
        return False


def configure_github_pages(
    repo_stub: str,
    *,
    target_branch=DFLT_DOCS_BRANCH,
    folder=DFLT_DOCS_FOLDER,
    ensure_branch_exists=True,
    headers: HeadersSpec = dflt_headers,
    verbose=DFLT_VERBOSE,
):
    """
    Configure or update GitHub Pages for a repo.

    Example:

    >>> configure_github_pages('i2mint/epythet')  # doctest: +SKIP

    """
    _clog = partial(clog, verbose)

    headers = _get_obj(headers)

    if not branch_exists(repo_stub, target_branch, headers=headers):
        if ensure_branch_exists:
            ensure_branch(repo_stub=repo_stub, branch=target_branch, headers=headers)
        else:
            _clog(
                f"---> {repo_stub} Branch {target_branch} does not exist. "
                "Please create the branch first. You can do so manually, or using the "
                "ensure_branch_exists=True option in configure_github_pages, or the "
                "ensure_branch function."
            )
            return f"https://github.com/{repo_stub}/branches/all"

    url = f"https://api.github.com/repos/{repo_stub}/pages"
    data = {"source": {"branch": target_branch, "path": folder}}

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 204:
        _clog(f"{repo_stub} GitHub Pages has been successfully updated.")
    elif response.status_code == 201:
        _clog(f"{repo_stub} GitHub Pages has been successfully configured.")
    else:
        _clog(f"{repo_stub} Failed to configure GitHub Pages: {response.status_code}")
        _clog(response.json())
        return response


def enable_pages(
    repo_stub,
    *,
    branch=DFLT_DOCS_BRANCH,
    path=DFLT_DOCS_FOLDER,
):
    """Enable or update GitHub Pages for a repo. Uses ``gh`` CLI or GITHUB_TOKEN.

    This is the recommended way to programmatically set up Pages.  Unlike
    ``configure_github_pages`` (which requires ``requests`` and a token), this
    function works out of the box if you have ``gh`` installed and authenticated.

    Returns the API response dict on success, or None on failure.

    >>> enable_pages('thorwhalen/denote')  # doctest: +SKIP
    """
    data = {"source": {"branch": branch, "path": path}}

    # Try POST first (create), fall back to PUT (update)
    result = _github_api_request(
        f"repos/{repo_stub}/pages", method="POST", data=data
    )
    if result is None:
        # Pages might already exist but misconfigured -- try PUT to update
        result = _github_api_request(
            f"repos/{repo_stub}/pages", method="PUT", data=data
        )
    return result


def ensure_branch(
    repo_stub: str,
    *,
    branch: str,
    commit_sha: str = None,
    headers: HeadersSpec = dflt_headers,
    verbose=DFLT_VERBOSE,
) -> dict:
    """
    Ensures a branch exists. Does nothing if it already does, and creates it if not.

    Parameters:
        repo_stub (str): Owner and name of the GitHub repository, e.g., 'owner/repo'.
        branch (str): Name of the branch to be created if it doesn't exist
        commit_sha (str): Commit SHA to base the new branch on. By default,
            it's the SHA of the most recent commit of the default branch.
        headers (dict): Headers for authentication, e.g., {'Authorization': 'Bearer <token>'}.

    Returns:
        dict: Response from GitHub API as a dictionary.
    """
    _clog = partial(clog, verbose)

    if branch_exists(repo_stub, branch):
        _clog(f"{repo_stub} Branch {branch} already exists.")
        return

    url = f"https://api.github.com/repos/{repo_stub}/git/refs"

    if commit_sha is None:
        commit_sha = default_branch_and_commit_sha(repo_stub, headers=headers)[
            "commit_sha"
        ]

    data = {"ref": f"refs/heads/{branch}", "sha": commit_sha}

    headers = _get_obj(headers)

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
    _clog(f"{repo_stub} Branch {branch} has been successfully created.")
    return response.json()


def repo_data(repo_stub: str, *, headers: HeadersSpec = dflt_headers) -> dict:
    """
    Retrieves data about a GitHub repository.
    """
    url = f"https://api.github.com/repos/{repo_stub}"

    headers = _get_obj(headers)
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise error if the request was unsuccessful

    return response.json()


def commit_data(
    repo_stub: str, branch: str, *, headers: HeadersSpec = dflt_headers
) -> dict:
    """
    Retrieves data about the latest commit on a branch of a GitHub repository.
    """
    # Get the SHA for the latest commit on the default branch
    headers = _get_obj(headers)

    commit_url = f"https://api.github.com/repos/{repo_stub}/git/refs/heads/{branch}"
    commit_response = requests.get(commit_url, headers=headers)
    commit_response.raise_for_status()
    return commit_response.json()


def default_branch_and_commit_sha(
    repo_stub: str, *, headers: HeadersSpec = dflt_headers
) -> dict:
    """
    Retrieves the default branch and current commit SHA for a given GitHub repository.

    Parameters:
        repo_stub (str): The GitHub repository in "owner/repo" format.
        headers (dict): Headers for authentication, e.g., {'Authorization': 'Bearer <token>'}.

    Returns:
        dict: A dictionary containing 'default_branch' and 'commit_sha'.
    """
    _repo_data = repo_data(repo_stub, headers=headers)
    default_branch = _repo_data["default_branch"]

    _commit_data = commit_data(repo_stub, branch=default_branch, headers=headers)
    commit_sha = _commit_data["object"]["sha"]

    return {"default_branch": default_branch, "commit_sha": commit_sha}


RepoStubs = Iterable[str]
Org = str


def repo_stubs_for_org(org: Org) -> RepoStubs:
    import hubcap

    org_reader = hubcap.GitHubReader(org)
    return [f"{org}/{repo}" for repo in list(org_reader)]


def configure_github_pages_for_repo_stubs(repo_stubs: RepoStubs | Org):
    """
    Configure Pages for an iterable of repo stubs, or all repos in an organization.

    >>> repo_pages_status = dict(
    ...     configure_github_pages_for_stubs('i2mint')  # doctest: +SKIP
    ... )

    """
    if isinstance(repo_stubs, str):
        repo_stubs = repo_stubs_for_org(repo_stubs)

    for repo_stub in repo_stubs:
        yield repo_stub, configure_github_pages(repo_stub)


def repo_stub_from_local_dir(path="."):
    """Extract the ``owner/repo`` slug from a local git checkout's remote URL.

    >>> repo_stub_from_local_dir('/path/to/some/git/repo')  # doctest: +SKIP
    'owner/repo'
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # Handle both HTTPS and SSH URLs
        url = re.sub(r"\.git$", "", url)
        m = re.search(r"github\.com[:/](.+/.+)$", url)
        return m.group(1) if m else None
    except Exception:
        return None


# -----------------------------------------------------------------------------------
# Note: Some of code below may need to be updated, given it assumes the old
# (prior to Oct 2023) way of setting up docs on github: Namely, where docs where
# in a docs folder in the master branch.


# TODO: Make the following particulars controllable from outside module
DFLT_URL_TABLE_SOURCE = (
    "https://raw.githubusercontent.com/otosense/content/main/tables/projects.csv"
)
docs_url_template = "https://{org}.github.io/{repo}"
repo_docs_url_template = "https://github.com/{org}/{repo}/tree/master/docs"


def published_doc_diagnosis_df(urls: Table = DFLT_URL_TABLE_SOURCE, url_column="url"):
    """
    The `published_doc_diagnosis_df` gets you a pandas dataframe (requires pandas to be
    installed!) that will tell you if given github ``org/repo`` url(s) have published
    documentation and if a `docs` folder even exists (in master branch).

    :param urls: A list of urls, a table containing urls, or a single url pointing to
        a csv where this table can be downloaded from.
    :param url_column: When ``urls`` is a table, what column name contains the urls.
    :return: A dataframe with the diagnosis

    """
    df = _get_table(urls)
    df["doc_page_url"] = df[url_column].apply(repo_url_to_docs_url)
    df["doc_page_exists"] = df["doc_page_url"].apply(url_exists)
    df["repo_has_docs_folder"] = df[url_column].apply(
        lambda url: url_exists(repo_url_to_repo_docs_url(url))
    )
    return df


def _get_table(df):
    import pandas as pd

    if isinstance(df, str):
        url = df
        if is_a_github_repo_root_url(url):
            return pd.DataFrame({"url": [url]})
        else:  # consider it to be a csv source of the table listing the urls
            df = table_url_to_df(url)
    elif not isinstance(df, pd.DataFrame) and isinstance(df, Iterable):
        urls = df
        df = pd.DataFrame({"url": urls})
    return df


def is_a_github_repo_root_url(url):
    return bool(github_root_url_p.match(url))


def github_org_and_repo(github_url):
    """
    >>> github_org_and_repo('https://github.com/i2mint/i2')
    {'org': 'i2mint', 'repo': 'i2'}
    """
    return github_url_p.match(github_url.strip()).groupdict()


def repo_url_to_docs_url(repo_url):
    """
    >>> repo_url_to_docs_url('https://github.com/i2mint/i2')
    'https://i2mint.github.io/i2'
    """
    return docs_url_template.format(**github_org_and_repo(repo_url))


def repo_url_to_repo_docs_url(repo_url):
    """
    >>> repo_url_to_repo_docs_url('https://github.com/i2mint/i2')
    'https://github.com/i2mint/i2/tree/master/docs'
    """
    return repo_docs_url_template.format(**github_org_and_repo(repo_url))


def table_url_to_df(url: Url):
    import pandas as pd

    html = requests.get(url).content
    df = pd.read_csv(BytesIO(html))
    df.columns = [column_name.strip() for column_name in df.columns]
    return df


def is_valid_response(response):
    return response.status_code == 200


def url_exists(url):
    return is_valid_response(requests.get(url))


# Below is stuff I wrote on my way to getting rid of pandas, but then decided to stop


def url_of_urls_csv_to_urls(url: Url, url_column=None):
    df = table_url_to_df(url)
    url_column = url_column or df.columns[0]
    return df[url_column].tolist()


def _get_urls(urls):
    if isinstance(urls, str):
        url = urls
        if is_a_github_repo_root_url(url):
            return [url]
        else:  # consider it to be a csv source of the table listing the urls
            return url_of_urls_csv_to_urls(url)
    return urls
