import shutil
from pathlib import Path

from epythet.docs_gen import _STATIC_FILES
from epythet.docs_gen.templates import master_file_t, master_file_title_t, RstTitle
from epythet.setup_config import read_config


def make_master_file(docsrc_dir, title: str):
    """Make index.rst in docsrc_dir using template master_file_t

    :param docsrc_dir:
    :param title:
    """
    master_file = Path(docsrc_dir).absolute() / 'index.rst'
    master_contents = master_file_t.format(rst_title=RstTitle.make_title(title, RstTitle.section))
    master_file.write_text(master_contents)


def make_docsrc(project_dir):
    """Make source folder for documentation based on setup.cfg metadata

    :param project_dir: Path to root project directory containing setup.cfg
    """
    # copy _static/docsrc files to project_dir/docsrc
    docsrc_src = _STATIC_FILES / 'docsrc'
    if not docsrc_src.is_dir():
        raise RuntimeError(f"Epythet module missing files in: {docsrc_src}")
    docsrc_dst = Path(project_dir).absolute() / 'docsrc'
    docsrc_static_dir = docsrc_dst / '_static'
    docsrc_static_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(docsrc_src), str(docsrc_dst))

    # make master file
    config = read_config(project_dir)

    title = master_file_title_t.format(display_name=config['metadata']['display_name'])
    make_master_file(docsrc_dir=docsrc_dst, title=title)


if __name__ == "__main__":
    import argh

    argh.dispatch_command(make_docsrc)
