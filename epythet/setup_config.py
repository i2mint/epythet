from configparser import ConfigParser
from pathlib import Path


def config_path(project_dir):
    config_file = Path(project_dir).absolute() / 'setup.cfg'
    return config_file


def make_config(project_dir, name, root_url, description, author, license, description_file, copyright, version,
                display_name):
    """Create the setup.cfg file to be read by setup.py and docs_gen

    :param project_dir: path to root project directory containing module folder, setup.py, and where setup.cfg will be
    :param name: module name
    :param root_url: git or documentation url
    :param description: short description
    :param author: module owner
    :param license: software license type
    :param description_file: .md or .rst file in project_dir
    :param copyright: year and author displayed in documentation
    :param version: version number MAJOR.MINOR.PATCH
    :param display_name: Name displayed in documentation with capitalization and punctuation as needed
    :return:
    """
    param_kwargs = locals()
    config_file = config_path(project_dir)
    config = ConfigParser()
    config['metadata'] = param_kwargs
    with config_file.open('w') as f:
        config.write(f)


def read_config(project_dir):
    """

    :param project_dir: path to root project directory containing module folder, setup.py, and where setup.cfg will be
    :return:
    """
    config_file = config_path(project_dir)
    config = ConfigParser()
    with config_file.open('r') as f:
        config.read_file(f)
    return config
