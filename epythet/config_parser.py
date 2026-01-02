"""Configuration parsing"""

from configparser import ConfigParser
from pathlib import Path
import os


def parse_config(config_file):
    """Parse the following data from the project setup. cfg or pyproject.toml for Sphinx conf.py

    For setup.cfg::

        [metadata]
        name = epythet
        version = 0.0.27
        author = Otosense
        copyright = 2020, Otosense
        display_name = Epythet

    For pyproject.toml::

        [project]
        name = "epythet"
        version = "0.0.27"
        authors = [{name = "Otosense"}]

        [tool.epythet]
        copyright = "2020, Otosense"
        display_name = "Epythet"

    :param config_file: PROJECT_DIR/setup.cfg or PROJECT_DIR/pyproject.toml
    :return: name, copyright, author, version, display_name
    """

    config_path = Path(config_file)

    # If setup.cfg doesn't exist, try pyproject.toml
    if not config_path.exists():
        project_dir = config_path.parent
        pyproject_path = project_dir / "pyproject.toml"

        if pyproject_path.exists():
            return _parse_pyproject_toml(pyproject_path)
        else:
            raise FileNotFoundError(
                f"Neither {config_file} nor {pyproject_path} found. "
                "Please provide either setup.cfg or pyproject.toml."
            )

    # Parse setup.cfg
    config = ConfigParser()
    with open(config_file, "r") as f:
        config.read_file(f)

    project = config["metadata"]["name"]
    copyright = config["metadata"].get("copyright", "NO COPYRIGHT")
    author = config["metadata"].get("author", "NO AUTHOR")

    # The full version, including alpha/beta/rc tags
    release = config["metadata"].get("version", "NO VERSION")
    display_name = config["metadata"].get("display_name", config["metadata"]["name"])

    return project, copyright, author, release, display_name


def _parse_pyproject_toml(pyproject_path):
    """Parse project metadata from pyproject.toml

    :param pyproject_path: Path to pyproject.toml
    :return: name, copyright, author, version, display_name
    """
    try:
        import tomllib
    except ImportError:
        # Python < 3.11
        try:
            import tomli as tomllib
        except ImportError:
            raise ImportError(
                "tomli is required to parse pyproject.toml on Python < 3.11. "
                "Install it with: pip install tomli"
            )

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project_data = data.get("project", {})
    tool_epythet = data.get("tool", {}).get("epythet", {})

    project = project_data.get("name", "NO PROJECT NAME")
    version = project_data.get("version", "NO VERSION")

    # Extract author from authors list if available
    authors = project_data.get("authors", [])
    if authors and isinstance(authors, list) and len(authors) > 0:
        author = authors[0].get("name", "NO AUTHOR")
    else:
        author = "NO AUTHOR"

    # Check tool.epythet section first, then fallback to defaults
    copyright = tool_epythet.get("copyright", "NO COPYRIGHT")
    display_name = tool_epythet.get("display_name", project)

    return project, copyright, author, version, display_name
