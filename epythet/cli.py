"""Command line access to epythet"""

from pathlib import Path

_STATIC_FILES = Path(__file__).absolute().parent / '_static'

from epythet.autogen import make_autodocs
from epythet.setup_docsrc import make_docsrc
from epythet.call_make import make

argh_kwargs = {
    'namespace': 'epythet',
    'functions': [make_docsrc, make_autodocs, make,],
    'namespace_kwargs': {
        'title': 'Documentation Generator',
        'description': 'Setup and generate Sphinx docs effortlessly',
    },
}


def main():
    import argh  # pip install argh

    argh.dispatch_commands(argh_kwargs.get('functions', None))


if __name__ == '__main__':
    main()
