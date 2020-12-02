"""
Console Scripts
---------------

To see available commands
::

    epythet --help


"""

import os
import json
import sys

py_version = sys.version_info.minor

root_dir = os.path.dirname(__file__)
root_dir_name = os.path.basename(root_dir)

rjoin = lambda *paths: os.path.join(root_dir, *paths)

data_dir = rjoin('data')
licenses_json_path = rjoin(data_dir, 'github_licenses.json')

pkg_dir = os.path.dirname(root_dir)
pkg_join = lambda *paths: os.path.join(pkg_dir, *paths)

pkg_path_names = ('.gitignore', 'setup.py')
pkg_paths = {pkg_join(name) for name in pkg_path_names}

import sys

py_version = sys.version_info.minor
from epythet.populate import populate_pkg_dir


def main():
    import argh  # pip install argh

    from epythet.pack import argh_kwargs as pack_kw
    from epythet.docs_gen import argh_kwargs as docs_gen_kw

    parser = argh.ArghParser()
    parser.add_commands(**pack_kw)
    parser.add_commands(**docs_gen_kw)
    parser.dispatch()


if __name__ == "__main__":
    main()
