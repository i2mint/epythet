import os
import shutil
from functools import partial

from epythet import pkg_path_names, root_dir
from epythet import pkg_join as epythet_join
from epythet.util import mk_conditional_logger
from epythet.pack import write_configs

path_sep = os.path.sep


def gen_readme_text(name, text="There's a bit of an air of mystery around this project..."):
    return f"""
# {name}
{text}
"""


def populate_pkg_dir(pkg_dir,
                     description="There's a bit of an air of mystery around this project...",
                     root_url=None,
                     author=None,
                     license='mit',
                     description_file='README.md',
                     keywords=None,
                     install_requires=None,
                     verbose=True,
                     **configs):
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

    for resource_name in pkg_path_names:
        if not os.path.isfile(pjoin(resource_name)):
            copy_from_resource(resource_name)

    def save_txt_to_pkg(resource_name, content):
        target_path = pjoin(resource_name)
        assert not os.path.isfile(target_path), f"{target_path} exists already"
        _clog(f"... making a {resource_name}")
        with open(pjoin(resource_name), 'wt') as fp:
            fp.write(content)

    if not os.path.isfile(pjoin('setup.cfg')):
        from epythet.pack import write_configs
        _clog("... making a 'setup.cfg'")
        write_configs(configs, pjoin('setup.cfg'))

    if not os.path.isfile(pjoin('LICENSE')):
        from epythet.licensing import license_body
        _license_body = license_body(configs['license'])
        save_txt_to_pkg('LICENSE', _license_body)

    if not os.path.isfile(pjoin('README.md')):
        readme_text = gen_readme_text(name, configs.get('description'))
        save_txt_to_pkg('README.md', readme_text)

    return name


if __name__ == '__main__':
    import argh  # TODO: replace by argparse, or require argh in epythet?

    argh.dispatch_command(populate_pkg_dir)
