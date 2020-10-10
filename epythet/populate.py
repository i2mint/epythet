import os
import shutil
import json
# from functools import partial
from typing import List, Optional
from epythet import pkg_path_names, root_dir, epythet_configs, epythet_configs_file
from epythet import pkg_join as epythet_join
from epythet.util import mk_conditional_logger

# from epythet.pack_util import write_configs

path_sep = os.path.sep

populate_dflts = epythet_configs.get(
    'populate_dflts',
    {'description': "There's a bit of an air of mystery around this project...",
     'root_url': None,
     'author': None,
     'license': 'mit',
     'description_file': 'README.md',
     'keywords': None,
     'install_requires': None,
     'verbose': True}
)


def gen_readme_text(name, text="There's a bit of an air of mystery around this project..."):
    return f"""
# {name}
{text}
"""


# TODO: Add a `defaults_from` in **configs that allows one to have several named defaults in epythet_configs_file
def populate_pkg_dir(pkg_dir,
                     description: str = populate_dflts['description'],
                     root_url: Optional[str] = populate_dflts['root_url'],
                     author: Optional[str] = populate_dflts['author'],
                     license: str = populate_dflts['license'],
                     description_file: str = populate_dflts['description_file'],
                     keywords: Optional[List] = populate_dflts['keywords'],
                     install_requires: Optional[List] = populate_dflts['install_requires'],
                     verbose: bool = populate_dflts['verbose'],
                     overwrite: List = (),
                     defaults_from: Optional[str] = None,
                     **configs):
    """Populate project directory root with useful packaging files, if they're missing.

    >>> from epythet.populate import populate_pkg_dir
    >>> import os  # doctest: +SKIP
    >>> name = 'epythet'  # doctest: +SKIP
    >>> pkg_dir = f'/D/Dropbox/dev/p3/proj/i/{name}'  # doctest: +SKIP
    >>> populate_pkg_dir(pkg_dir,  # doctest: +SKIP
    ...                  description='Tools for packaging',
    ...                  root_url=f'https://github.com/i2mint',
    ...                  author='OtoSense')

    :param pkg_dir:
    :param description:
    :param root_url:
    :param author:
    :param license:
    :param description_file:
    :param keywords:
    :param install_requires:
    :param verbose:
    :param default_from: Name of field to look up in epythet_configs to get defaults from,
        or 'user_input' to get it from user input.
    :param configs:
    :return:

    """
    # TODO: Test this defaults_from thing!
    if defaults_from is not None:
        if defaults_from == 'user_input':
            args_defaults = dict()  # ... and then fill with user input
            raise NotImplementedError("Not immplemented yet")  # TODO: Implement
        else:
            try:
                epythet_configs = json.load(open(epythet_configs_file))
                args_defaults = epythet_configs[defaults_from]
            except KeyError:
                raise KeyError(f"{epythet_configs_file} json didn't have a {defaults_from} field")
        _locals = locals()
        for k, v in args_defaults.items():
            _locals[k] = v

    if isinstance(overwrite, str):
        overwrite = {overwrite}
    else:
        overwrite = set(overwrite)

    _clog = mk_conditional_logger(condition=verbose, func=print)
    pkg_dir = os.path.abspath(os.path.expanduser(pkg_dir))
    assert os.path.isdir(pkg_dir), f"{pkg_dir} is not a directory"
    if pkg_dir.endswith(path_sep):
        pkg_dir = pkg_dir[:-1]  # remove the slash suffix (or basename will be empty)
    name = os.path.basename(pkg_dir)
    pjoin = lambda *p: os.path.join(pkg_dir, *p)

    if name not in os.listdir(pkg_dir):
        f = pjoin(name)
        _clog(f"... making directory {pkg_dir}")
        os.mkdir(f)
    if '__init__.py' not in os.listdir(pjoin(name)):
        f = pjoin(name, '__init__.py')
        _clog(f"... making an empty {f}")
        with open(f, 'w') as fp:
            fp.write("")

    # Note: Overkill since we just made those things...
    if name not in os.listdir(pkg_dir) or '__init__.py' not in os.listdir(pjoin(name)):
        raise RuntimeError("You should have a {name}/{name}/__init__.py structure. You don't.")

    if os.path.isfile(pjoin('setup.cfg')):
        with open(pjoin('setup.cfg'), 'r'):
            pass

    kwargs = dict(description=description,
                  root_url=root_url,
                  author=author,
                  license=license,
                  description_file=description_file,
                  keywords=keywords,
                  install_requires=install_requires)
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    kwargs['description-file'] = kwargs.get('description_file', '')
    configs = dict(name=name, **configs, **kwargs)

    assert configs.get('name', name) == name, \
        f"There's a name conflict. pkg_dir tells me the name is {name}, but configs tell me its {configs.get('name')}"

    def copy_from_resource(resource_name):
        _clog(f'... copying {resource_name} from {root_dir} to {pkg_dir}')
        shutil.copy(epythet_join(resource_name), pjoin(resource_name))

    def should_update(resource_name):
        return (resource_name in overwrite) or (not os.path.isfile(pjoin(resource_name)))

    for resource_name in pkg_path_names:
        if should_update(resource_name):
            copy_from_resource(resource_name)

    def save_txt_to_pkg(resource_name, content):
        target_path = pjoin(resource_name)
        assert not os.path.isfile(target_path), f"{target_path} exists already"
        _clog(f"... making a {resource_name}")
        with open(pjoin(resource_name), 'wt') as fp:
            fp.write(content)

    if should_update('setup.cfg'):
        from epythet.pack_util import write_configs
        _clog("... making a 'setup.cfg'")
        write_configs(configs, pjoin('setup.cfg'))

    if should_update('LICENSE'):
        from epythet.licensing import license_body
        _license_body = license_body(configs['license'])
        save_txt_to_pkg('LICENSE', _license_body)

    if should_update('README.md'):
        readme_text = gen_readme_text(name, configs.get('description'))
        save_txt_to_pkg('README.md', readme_text)

    return name


def update_pack_and_setup_py(target_pkg_dir):
    """Just copy over setup.py and pack.py (moving the original to be prefixed by '_'"""
    if target_pkg_dir.endswith(path_sep):
        target_pkg_dir = target_pkg_dir[:-1]  # remove the slash suffix (or basename will be empty)
    name = os.path.basename(target_pkg_dir)
    contents = os.listdir(target_pkg_dir)
    assert {'pack.py', 'setup.py', name}.issubset(contents), \
        f"{target_pkg_dir} needs to have all three: {', '.join({'pack.py', 'setup.py', name})}"

    pjoin = lambda *p: os.path.join(target_pkg_dir, *p)

    resources = {'pack.py', 'setup.py'}
    for resource_name in resources:
        print(f'... copying {resource_name} from {epythet_join("")} to {target_pkg_dir}')
        shutil.move(src=pjoin(resource_name), dst=pjoin('_' + resource_name))
        shutil.copy(src=epythet_join(resource_name), dst=pjoin(resource_name))


if __name__ == '__main__':
    import argh  # TODO: replace by argparse, or require argh in epythet?

    argh.dispatch_command(populate_pkg_dir)
