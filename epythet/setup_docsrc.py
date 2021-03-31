"""Docstring makers"""

from pathlib import Path
import shutil
import sys

from epythet import _STATIC_FILES
from epythet.config_parser import parse_config
from epythet.templates import (
    master_file_t,
    master_file_title_t,
    RstTitle,
)


def make_master_file(docsrc_dir, title: str):
    """Make index.rst in docsrc_dir using template master_file_t

    :param docsrc_dir:
    :param title:
    """
    master_file = Path(docsrc_dir).absolute() / 'index.rst'
    master_contents = master_file_t.format(
        rst_title=RstTitle.make_title(title, RstTitle.section)
    )
    master_file.write_text(master_contents)


def make_docsrc(project_dir, verbose: bool = True):
    """Make source folder for documentation based on setup.cfg metadata

    :param project_dir: Path to root project directory containing setup.cfg
    """
    # copy _static/docsrc files to project_dir/docsrc
    if verbose:
        print('Making and populating a docsrc directory (for documentation)')
    docsrc_src = _STATIC_FILES / 'docsrc'
    if not docsrc_src.is_dir():
        raise RuntimeError(f'Epythet module missing files in: {docsrc_src}')
    docsrc_dst = Path(project_dir).absolute() / 'docsrc'
    if sys.version_info.minor >= 8:
        shutil.copytree(str(docsrc_src), str(docsrc_dst), dirs_exist_ok=True)
    else:
        shutil.copytree(str(docsrc_src), str(docsrc_dst))

    docsrc_static_dir = docsrc_dst / '_static'
    docsrc_static_dir.mkdir(parents=True, exist_ok=True)
    # make master file
    project, copyright, author, release, display_name = parse_config(
        Path(project_dir) / 'setup.cfg'
    )
    title = master_file_title_t.format(display_name=display_name)
    make_master_file(docsrc_dir=docsrc_dst, title=title)


if __name__ == '__main__':
    import argh

    argh.dispatch_command(make_docsrc)
