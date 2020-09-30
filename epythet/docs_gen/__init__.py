"""Setup and generate Sphinx docs effortlessly

Quickstart
----------

Setup Sphinx docsrc
::

    from epythet.docs_gen.setup_docsrc import make_docsrc
    make_docsrc(PROJECT_DIR)

Generate module docs
::

    from epythet.docs_gen.autogen import make_autodocs
    make_autodocs(PROJECT_DIR)

Compile docs
::

    cd PROJECT_DIR/docsrc
    make html

"""

from pathlib import Path


_STATIC_FILES = Path(__file__).absolute().parent / '_static'
