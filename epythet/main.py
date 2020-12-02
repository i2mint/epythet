from epythet.docs_gen.setup_docsrc import make_docsrc
from epythet.docs_gen.autogen import make_autodocs


def make_html():
    pass


def go(project_dir, output_dirname='module_docs', skip_existing=True, docsrc_dir=None):
    """Create sphinx autodocs and table of contents for module defined by setup.cfg

    :param project_dir: Path to root project directory containing setup.cfg
    :param output_dirname: directory name to be created under docsrc
    :param skip_existing: existing docs will not be overwritten if True
    :param docsrc_dir: path to sphinx docs source file
    """
    make_docsrc(project_dir)
    make_autodocs(project_dir, output_dirname, skip_existing, docsrc_dir)
    make_html(project_dir)


if __name__ == "__main__":
    import argh

    argh.dispatch_commands([make_docsrc, make_autodocs])
