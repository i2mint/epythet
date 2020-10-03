import os

root_dir = os.path.dirname(__file__)
root_dir_name = os.path.basename(root_dir)
rjoin = lambda *paths: os.path.join(root_dir, *paths)
data_dir = rjoin('data')
licenses_json_path = rjoin(data_dir, 'github_licenses.json')

pkg_dir = os.path.dirname(root_dir)
pkg_join = lambda *paths: os.path.join(pkg_dir, *paths)

pkg_path_names = ('.gitignore', 'pack.py', 'setup.py')
pkg_paths = {pkg_join(name) for name in pkg_path_names}

from epythet.populate import populate_pkg_dir
