"""Legacy configuration accessor kept for the frozen ``docsrc/conf.py`` copies.

Over a hundred projects committed a ``docsrc/conf.py`` that does::

    project, copyright, author, release, display_name = parse_config(
        Path(__file__).absolute().parent.parent / "setup.cfg"
    )

That 5-tuple is a published contract, so it stays. New code should use
:func:`epythet.config.load_config`, which returns the full
:class:`~epythet.config.DocsConfig`.
"""

from pathlib import Path

from epythet.config import ConfigError, load_config


def parse_config(config_file):
    """Project metadata for Sphinx's ``conf.py``, as a 5-tuple.

    ``config_file`` may be a ``setup.cfg`` path, a ``pyproject.toml`` path or the
    project directory itself. Whatever is passed, the project directory is what
    gets resolved: ``pyproject.toml`` (with a ``[project]`` table) wins over
    ``setup.cfg`` when both exist. See :mod:`epythet.config` for the keys.

    ``copyright`` is an empty string when unset, and the generated docs render no
    copyright line in that case.

    :param config_file: ``PROJECT_DIR/setup.cfg``, ``PROJECT_DIR/pyproject.toml``
        or ``PROJECT_DIR``
    :return: ``(name, copyright, author, version, display_name)``
    :raises FileNotFoundError: when neither configuration file exists
    """
    try:
        return load_config(Path(config_file)).legacy_tuple
    except ConfigError as e:
        raise FileNotFoundError(str(e)) from e
