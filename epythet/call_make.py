"""Just to call make"""

import subprocess
from pathlib import Path


def make(project_dir, *make_args):
    """Invokes the Sphinx docs makefile in project_dir/docsrc.  Commonly used make_args: "html", "doctest", "github"

    :param project_dir: Path to root project directory containing docsrc folder
    :param make_args: Sphinx docs makefile args
    """
    subprocess.run(('make',) + make_args, cwd=Path(project_dir).absolute() / 'docsrc')
