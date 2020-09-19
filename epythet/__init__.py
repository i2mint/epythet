import os

root_dir = os.path.dirname(__file__)
pkg_dir = os.path.dirname(root_dir)
pkg_join = lambda *paths: os.path.join(pkg_dir, *paths)

deploy_py_path = pkg_join('deploy.py')
pip_packaging_py_path = pkg_join('pip_packaging.py')
