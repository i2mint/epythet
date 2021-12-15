"""Elements for a tool to check if docs are published, and if not, why.

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
from typing import Union, Iterable

Url = str
Urls = Iterable[Url]
Table = Union[Url, Urls, Iterable[Iterable]]

github_url_p = re.compile(r'https?://github.com/(?P<org>[^/]+)/(?P<repo>[^/]+).*?')
github_root_url_p = re.compile(r'^https?://github.com/[^/]+/[^/]+/?$')

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
