"""Configuration parsing"""
from configparser import ConfigParser
from pathlib import Path


def parse_config(config_file):
    """Parse the following data from the project setup.cfg for Sphinx conf.py

    ::

        [metadata]
        name = epythet
        version = 0.0.27
        author = Otosense
        copyright = 2020, Otosense
        display_name = Epythet

    :param config_file: PROJECT_DIR/setup.cfg
    :return: name, copyright, author, version, display_name
    """

    config = ConfigParser()
    with open(config_file, 'r') as f:
        config.read_file(f)

    project = config['metadata']['name']
    copyright = config['metadata'].get('copyright', 'NO COPYRIGHT')
    author = config['metadata'].get('author', 'NO AUTHOR')

    # The full version, including alpha/beta/rc tags
    release = config['metadata'].get('version', 'NO VERSION')
    display_name = config['metadata'].get('display_name', config['metadata']['name'])

    return project, copyright, author, release, display_name
