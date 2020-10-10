"""Utils to package and publish.



The typical sequence of the methodic and paranoid could be something like this:

```
python pack.py current-configs  # see what you got
python pack.py increment-configs-version  # update (increment the version and write that in setup.cfg
python pack.py current-configs-version  # see that it worked
python pack.py current-configs  # ... if you really want to see the whole configs again (you're really paranoid)
python pack.py run-setup  # see that it worked
python pack.py twine-upload-dist  # publish
# and then go check things work...
```


If you're crazy (or know what you're doing) just do

```
python pack.py go
```


"""
import subprocess
from setuptools import find_packages
import json
import re
import sys
from pprint import pprint
from typing import Union, Mapping, Iterable, Generator
from configparser import ConfigParser
import os

CONFIG_FILE_NAME = 'setup.cfg'
CONFIG_SECTION = 'metadata'

pjoin = lambda *p: os.path.join(*p)


def get_name_from_configs(pkg_dir, assert_exists=True):
    """Get name from local setup.cfg (metadata section)"""
    configs = read_configs(pkg_dir=pkg_dir)
    name = configs.get('name', None)
    if assert_exists:
        assert name is not None, "No name was found in configs"
    return name


def go(pkg_dir, version=None, verbose=True):
    """Update version, package and deploy:
    Runs in a sequence: increment_configs_version, update_setup_cfg, run_setup, twine_upload_dist

    :param version: The desired version (if not given, will increment the current version
    :param verbose: Whether to print stuff or not

    """

    increment_configs_version(pkg_dir, version)
    update_setup_cfg(pkg_dir, verbose=verbose)
    run_setup(pkg_dir)
    twine_upload_dist(pkg_dir)


def clog(condition, *args, **kwargs):
    if condition:
        pprint(*args, **kwargs)


Path = str


# def update_version(version):
#     """Updates version (writes to setup.cfg)"""
#     pass
def _get_pkg_dir(pkg_dir: Path, validate=True) -> Path:
    pkg_dir, pkg_dirname = validate_pkg_dir(pkg_dir)
    if validate:
        validate_pkg_dir(pkg_dir)
    return pkg_dir


def _get_pkg_dir_and_name(pkg_dir):
    pkg_dir = os.path.realpath(pkg_dir)
    if pkg_dir.endswith(os.sep):
        pkg_dir = pkg_dir[:-1]
    pkg_dirname = os.path.basename(pkg_dir)
    return pkg_dir, pkg_dirname


def validate_pkg_dir(pkg_dir):
    """Asserts that the pkg_dir is actually one (has a pkg_name/__init__.py file)"""
    pkg_dir, pkg_dirname = _get_pkg_dir_and_name(pkg_dir)
    assert os.path.isdir(pkg_dir), f"Directory {pkg_dir} wasn't found"
    assert pkg_dirname in os.listdir(pkg_dir), f"pkg_dir={pkg_dir} doesn't itself contain a dir named {pkg_dirname}"
    assert '__init__.py' in os.listdir(os.path.join(pkg_dir, pkg_dirname)), \
        f"pkg_dir={pkg_dir} contains a dir named {pkg_dirname}, " \
        f"but that dir isn't a package (does not have a __init__.py"

    return pkg_dir, pkg_dirname


def current_configs(pkg_dir):
    configs = read_configs(pkg_dir=_get_pkg_dir(pkg_dir))
    pprint(configs)


def current_configs_version(pkg_dir):
    pkg_dir = _get_pkg_dir(pkg_dir)
    return read_configs(pkg_dir=pkg_dir)['version']


# TODO: Both setup and twine are python. Change to use python objects directly.
def update_setup_cfg(pkg_dir, new_deploy=False, version=None, verbose=True):
    """Update setup.cfg (at this point, just updates the version).
    If version is not given, will ask pypi (via http request) what the current version is, and increment that.
    """
    pkg_dir = _get_pkg_dir(pkg_dir)
    configs = read_and_resolve_setup_configs(pkg_dir=_get_pkg_dir(pkg_dir), new_deploy=new_deploy, version=version)
    pprint("\n{configs}\n")
    clog(verbose, pprint(configs))
    write_configs(pkg_dir=pkg_dir, configs=configs)


def set_version(pkg_dir, version):
    """Update setup.cfg (at this point, just updates the version).
    If version is not given, will ask pypi (via http request) what the current version is, and increment that.
    """
    pkg_dir = _get_pkg_dir(pkg_dir)
    configs = read_configs(pkg_dir)
    assert isinstance(version, str), "version should be a string"
    configs['version'] = version
    write_configs(pkg_dir=pkg_dir, configs=configs)


def increment_configs_version(
        pkg_dir,
        version=None,
):
    """Update setup.cfg (at this point, just updates the version).
    If version is not given, will ask pypi (via http request) what the current version is, and increment that.
    """
    pkg_dir = _get_pkg_dir(pkg_dir)
    configs = read_configs(pkg_dir=pkg_dir)
    version = _get_version(pkg_dir, version=version, configs=configs, new_deploy=False)
    version = increment_version(version)
    configs['version'] = version
    write_configs(pkg_dir=pkg_dir, configs=configs)


def run_setup(pkg_dir):
    """Run ``python setup.py sdist bdist_wheel``"""
    print('--------------------------- setup_output ---------------------------')
    pkg_dir = _get_pkg_dir(pkg_dir)
    original_dir = os.getcwd()
    os.chdir(pkg_dir)
    setup_output = subprocess.run(f'{sys.executable} setup.py sdist bdist_wheel'.split(' '))
    os.chdir(original_dir)
    # print(f"{setup_output}\n")


def twine_upload_dist(pkg_dir):
    """Publish to pypi. Runs ``python -m twine upload dist/*``"""
    print('--------------------------- upload_output ---------------------------')
    pkg_dir = _get_pkg_dir(pkg_dir)
    original_dir = os.getcwd()
    os.chdir(pkg_dir)
    # TODO: dist/*? How to publish just last on
    subprocess.run(f'{sys.executable} -m twine upload dist/*'.split(' '))
    os.chdir(original_dir)
    # print(f"{upload_output.decode()}\n")


# TODO: A lot of work done here to read setup.cfg. setup function apparently does it for you. How to use that?

# TODO: postprocess_ini_section_items and preprocess_ini_section_items: Add comma separated possibility?
# TODO: Find out if configparse has an option to do this processing alreadys
def postprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    r"""Transform newline-separated string values into actual list of strings (assuming that intent)

    >>> section_from_ini = {
    ...     'name': 'epythet',
    ...     'keywords': '\n\tdocumentation\n\tpackaging\n\tpublishing'
    ... }
    >>> section_for_python = dict(postprocess_ini_section_items(section_from_ini))
    >>> section_for_python
    {'name': 'epythet', 'keywords': ['documentation', 'packaging', 'publishing']}

    """
    splitter_re = re.compile('[\n\r\t]+')
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if v.startswith('\n'):
            v = splitter_re.split(v[1:])
            v = [vv.strip() for vv in v if vv.strip()]
            v = [vv for vv in v if not vv.startswith('#')]  # remove commented lines
        yield k, v


# TODO: Find out if configparse has an option to do this processing already
def preprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    """Transform list values into newline-separated strings, in view of writing the value to a ini formatted section
    >>> section = {
    ...     'name': 'epythet',
    ...     'keywords': ['documentation', 'packaging', 'publishing']
    ... }
    >>> for_ini = dict(preprocess_ini_section_items(section))
    >>> print('keywords =' + for_ini['keywords'])  # doctest: +NORMALIZE_WHITESPACE
    keywords =
        documentation
        packaging
        publishing

    """
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if isinstance(v, list):
            v = '\n\t' + '\n\t'.join(v)
        yield k, v


def read_configs(
        pkg_dir: Path,
        postproc=postprocess_ini_section_items
):
    pkg_dir = _get_pkg_dir(pkg_dir)
    config_filepath = pjoin(pkg_dir, CONFIG_FILE_NAME)
    c = ConfigParser()
    c.read_file(open(config_filepath, 'r'))
    # if CONFIG_SECTION is None:
    #     d = dict(c)
    #     if postproc:
    #         d = {k: dict(postproc(v)) for k, v in c}
    # else:
    d = dict(c[CONFIG_SECTION])
    if postproc:
        d = dict(postproc(d))
    return d


def write_configs(
        pkg_dir: Path,
        configs,
        preproc=preprocess_ini_section_items
):
    pkg_dir = _get_pkg_dir(pkg_dir)
    config_filepath = pjoin(pkg_dir, CONFIG_FILE_NAME)
    c = ConfigParser()
    if os.path.isfile(config_filepath):
        c.read_file(open(config_filepath, 'r'))
    c[CONFIG_SECTION] = dict(preproc(configs))
    with open(config_filepath, 'w') as fp:
        c.write(fp)


# dflt_formatter = Formatter()

def increment_version(version_str):
    version_nums = list(map(int, version_str.split('.')))
    version_nums[-1] += 1
    return '.'.join(map(str, version_nums))


try:
    import requests

    requests_is_installed = True
except ModuleNotFoundError:
    requests_is_installed = False


def http_get_json(url, use_requests=requests_is_installed) -> Union[dict, None]:
    """Make ah http request to url and get json, and return as python dict
    """

    if use_requests:
        import requests
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        else:
            raise ValueError(f"response code was {r.status_code}")
    else:
        import urllib.request
        from urllib.error import HTTPError
        req = urllib.request.Request(url)
        try:
            r = urllib.request.urlopen(req)
            if r.code == 200:
                return json.loads(r.read())
            else:
                raise ValueError(f"response code was {r.code}")
        except HTTPError:
            return None  # to indicate (hopefully) that name doesn't exist
        except Exception:
            raise


DLFT_PYPI_PACKAGE_JSON_URL_TEMPLATE = 'https://pypi.python.org/pypi/{package}/json'


# TODO: Perhaps there's a safer way to analyze errors (and determine if the package exists or other HTTPError)
def current_pypi_version(
        pkg_dir: Path,
        name: Union[None, str] = None,
        url_template=DLFT_PYPI_PACKAGE_JSON_URL_TEMPLATE,
        use_requests=requests_is_installed
) -> Union[str, None]:
    """
    Return version of package on pypi.python.org using json.

    ```
    > current_pypi_version('py2store')
    '0.0.7'
    ```

    :param package: Name of the package
    :return: A version (string) or None if there was an exception (usually means there
    """
    pkg_dir, pkg_dirname = validate_pkg_dir(pkg_dir)
    name = name or get_name_from_configs(pkg_dir)
    assert pkg_dirname == name, f"pkg_dirname ({pkg_dirname}) and name ({name}) were not the same"
    url = url_template.format(package=name)
    t = http_get_json(url, use_requests=use_requests)
    releases = t.get('releases', [])
    if releases:
        return sorted(releases, key=lambda r: tuple(map(int, r.split('.'))))[-1]


def next_version_for_package(
        pkg_dir: Path,
        name: Union[None, str] = None,
        url_template=DLFT_PYPI_PACKAGE_JSON_URL_TEMPLATE,
        version_if_current_version_none='0.0.1',
        use_requests=requests_is_installed
) -> str:
    name = name or get_name_from_configs(pkg_dir=pkg_dir)
    current_version = current_pypi_version(name, url_template, use_requests=use_requests)
    if current_version is not None:
        return increment_version(current_version)
    else:
        return version_if_current_version_none


def _get_version(pkg_dir: Path,
                 version,
                 configs,
                 name: Union[None, str] = None,
                 new_deploy=False):
    version = version or configs.get('version', None)
    if version is None:
        try:
            if new_deploy:
                version = next_version_for_package(pkg_dir, name)  # when you want to make a new package
            else:
                version = current_pypi_version(pkg_dir, name)  # when you want to make a new package
        except Exception as e:
            print(
                f"Got an error trying to get the new version of {name} so will try to get the version from setup.cfg...")
            print(f"{e}")
            version = configs.get('version', None)
            if version is None:
                raise ValueError(f"Couldn't fetch the next version from PyPi (no API token?), "
                                 f"nor did I find a version in setup.cfg (metadata section).")
    return version


def read_and_resolve_setup_configs(
        pkg_dir: Path,
        new_deploy=False,
        version=None,
        assert_names=True):
    """make setup params and call setup

    :param pkg_dir: Directory where the pkg is (which is also where the setup.cfg is)
    :param new_deploy: whether this setup for a new deployment (publishing to pypi) or not
    :param version: The version number to set this up as.
                    If not given will look at setup.cfg[metadata] for one,
                    and if not found there will use the current version (requesting pypi.org)
                    and bump it if the new_deploy flag is on
    """
    # read the config file (get a dict with it's contents)
    pkg_dir, pkg_dirname = _get_pkg_dir_and_name(pkg_dir)
    if assert_names:
        validate_pkg_dir(pkg_dir)

    configs = read_configs(pkg_dir)

    # parse out name and root_url
    assert 'root_url' in configs or 'url' in configs, "configs didn't have a root_url or url"

    name = configs['name'] or pkg_dirname
    if assert_names:
        assert name == pkg_dirname, f"config name ({name}) and pkg_dirname ({pkg_dirname}) are not equal!"

    if 'root_url' in configs:
        root_url = configs['root_url']
        if root_url.endswith('/'):  # yes, it's a url so it's always forward slash, not the systems' slash os.sep
            root_url = root_url[:-1]
        url = f"{root_url}/{name}"
    elif 'url' in configs:
        url = configs['url']
    else:
        raise ValueError(f"configs didn't have a root_url or url. It should have at least one of these!")

    # Note: if version is not in config, version will be None,
    #  resulting in bumping the version or making it be 0.0.1 if the package is not found (i.e. first deploy)

    meta_data_dict = {k: v for k, v in configs.items()}

    # make the setup_kwargs
    setup_kwargs = dict(
        meta_data_dict,
        # You can add more key=val pairs here if they're missing in config file
    )

    version = _get_version(pkg_dir, version, configs, name, new_deploy)

    def text_of_readme_md_file():
        try:
            with open('README.md') as f:
                return f.read()
        except:
            return ""

    dflt_kwargs = dict(
        name=f"{name}",
        version=f'{version}',
        url=url,
        packages=find_packages(),
        include_package_data=True,
        platforms='any',
        # long_description=text_of_readme_md_file(),
        # long_description_content_type="text/markdown",
        description_file='README.md'
    )

    configs = dict(dflt_kwargs, **setup_kwargs)

    return configs


argh_kwargs = {
    'namespace': 'pack',
    'functions': [
        current_configs,
        increment_configs_version,
        current_configs_version,
        twine_upload_dist,
        read_and_resolve_setup_configs,
        update_setup_cfg,
        go,
        get_name_from_configs,
        run_setup,
        current_pypi_version,
        validate_pkg_dir
    ],
    'namespace_kwargs': {
        'title': 'Package Configurations',
        'description': 'Utils to package and publish.'
    }
}

if __name__ == '__main__':
    import argh  # pip install argh

    argh.dispatch_commands(argh_kwargs.get('functions', None))
