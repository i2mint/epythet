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
from typing import Union, Iterable, Callable

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


# # TODO: Same as configure_github_pages
# def set_github_pages_source(
#     repo_stub: str,
#     *,
#     target_branch: str = DFLT_DOCS_BRANCH,
#     path: str,
#     headers: HeadersSpec = dflt_headers,
# ) -> dict:
#     """
#     Configures the GitHub Pages source branch and directory for the given repository.

#     Parameters:
#         repo_stub (str): Owner and name of the GitHub repository, e.g., 'owner/repo'.
#         target_branch (str): Branch for GitHub Pages to use.
#         path (str): Path within the branch to serve GitHub Pages from, either '/' or '/docs'.
#         headers (dict): Headers for authentication, e.g., {'Authorization': 'Bearer <token>'}.

#     Returns:
#         dict: Response from GitHub API as a dictionary.
#     """
#     url = f"https://api.github.com/repos/{repo_stub}/pages"
#     data = {"source": {"branch": target_branch, "path": path}}
#     headers = _get_obj(headers)

#     response = requests.put(url, headers=headers, json=data)
#     response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
#     return response.json()


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


def configure_github_pages_for_repo_stubs(repo_stubs: Union[RepoStubs, Org]):
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
