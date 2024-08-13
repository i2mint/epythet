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

github_url_p = re.compile(r'https?://github.com/(?P<org>[^/]+)/(?P<repo>[^/]+).*?')
github_root_url_p = re.compile(r'^https?://github.com/[^/]+/[^/]+/?$')

# -----------------------------------------------------------------------------------

import requests
import os
from warnings import warn

DFLT_DOCS_BRANCH = 'gh-pages'
DFLT_DOCS_FOLDER = '/'

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}


def github_token(env_var='GITHUB_TOKEN'):
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
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
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


def token_user_info(token=None):
    response = requests.get('https://api.github.com/user', headers=dflt_headers(token))

    if response.status_code == 200:
        print("Token is valid.")
    else:
        print(f"Failed to authenticate: {response.status_code}")

    return response.json()


def verify_repo_access(repo_stub):
    url = f"https://api.github.com/repos/{repo_stub}"
    response = requests.get(url, headers=dflt_headers())

    if response.status_code == 200:
        print(f"Access to {repo_stub} verified.")
    else:
        print(f"Failed to access {repo_stub}: {response.status_code}")

    return response.json()


def branch_exists(repo_stub: str, branch: str, *, headers: HeadersSpec = dflt_headers):
    """
    Check if a branch exists in a repo.

    :param repo_stub: A string of the form ``org/repo``.
    :param branch: The branch name to check for.
    :param headers: A function that returns a dictionary of headers
    """
    url = f"https://api.github.com/repos/{repo_stub}/branches/{branch}"
    response = requests.get(url, headers=_get_obj(headers))
    if response.status_code == 200:
        return True
    else:
        print(
            f"repo_stub {branch} branch doesn't exist: {response.status_code}, {response.content=}"
        )
        return False


def configure_github_pages(
    repo_stub: str,
    *,
    target_branch=DFLT_DOCS_BRANCH,
    folder=DFLT_DOCS_FOLDER,
    headers: HeadersSpec = dflt_headers,
):
    """
    Configure or update GitHub Pages for a repo.

    Example:

    >>> configure_github_pages('i2mint/epythet')  # doctest: +SKIP

    """
    headers = _get_obj(headers)

    if not branch_exists(repo_stub, target_branch, headers=headers):
        print(
            f"---> {repo_stub} Branch {target_branch} does not exist. Please create the branch first."
        )
        return "https://github.com/{repo_stub}/branches/all"

    url = f"https://api.github.com/repos/{repo_stub}/pages"
    data = {"source": {"branch": target_branch, "path": folder}}

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 204:
        print(f"{repo_stub} GitHub Pages has been successfully updated.")
    elif response.status_code == 201:
        print(f"{repo_stub} GitHub Pages has been successfully configured.")
    else:
        print(f"{repo_stub} Failed to configure GitHub Pages: {response.status_code}")
        print(response.json())
        return response


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
    'https://raw.githubusercontent.com/otosense/content/main/tables/projects.csv'
)
docs_url_template = 'https://{org}.github.io/{repo}'
repo_docs_url_template = 'https://github.com/{org}/{repo}/tree/master/docs'


def published_doc_diagnosis_df(urls: Table = DFLT_URL_TABLE_SOURCE, url_column='url'):
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
    df['doc_page_url'] = df[url_column].apply(repo_url_to_docs_url)
    df['doc_page_exists'] = df['doc_page_url'].apply(url_exists)
    df['repo_has_docs_folder'] = df[url_column].apply(
        lambda url: url_exists(repo_url_to_repo_docs_url(url))
    )
    return df


def _get_table(df):
    import pandas as pd

    if isinstance(df, str):
        url = df
        if is_a_github_repo_root_url(url):
            return pd.DataFrame({'url': [url]})
        else:  # consider it to be a csv source of the table listing the urls
            df = table_url_to_df(url)
    elif not isinstance(df, pd.DataFrame) and isinstance(df, Iterable):
        urls = df
        df = pd.DataFrame({'url': urls})
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
