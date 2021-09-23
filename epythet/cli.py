"""Command line access to epythet"""

from pathlib import Path

_STATIC_FILES = Path(__file__).absolute().parent / '_static'

from .autogen import make_autodocs
from .setup_docsrc import make_docsrc
from .call_make import make

from epythet.tools import (
    repair_package,
    print_diagnosis,
    diagnose_doctest_code_blocks,
    add_newlines_before_doctests_when_missing,
)

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
