"""Command line access to epythet

More info in the main epythet documentation page
"""

from pathlib import Path

_STATIC_FILES = Path(__file__).absolute().parent / '_static'

from epythet.autogen import make_autodocs
from epythet.setup_docsrc import make_docsrc
from epythet.call_make import make


def quickstart(project_dir):
    """Quickstart will run through the three steps

    1. epythet make_docsrc project_dir
    2. epythet make_autodocs project_dir
    3. epythet make project_dir html

    :param project_dir: Path to root project directory containing docsrc folder
    """
    make_docsrc(project_dir, verbose=True)
    make_autodocs(project_dir, skip_existing=False)
    make(project_dir, 'html')


argh_kwargs = {
    'namespace': 'epythet',
    'functions': [make_docsrc, make_autodocs, make, quickstart],
    'namespace_kwargs': {
        'title': 'Documentation Generator',
        'description': 'Setup and generate Sphinx docs effortlessly',
    },
}


def epythet_cli():
    import argh  # pip install argh

    argh.dispatch_commands(argh_kwargs.get('functions', None))


if __name__ == '__main__':
    epythet_cli()
