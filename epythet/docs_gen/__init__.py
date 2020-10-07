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

View by opening ``PROJECT_DIR/docsrc/_build/html/index.html``

Github Pages
------------

Go to your repo settings and set GitHub Pages site to build from the ``/docs`` folder in the ``master`` branch.
Github will tell you where it will be published.
In this case, the site is published at https://i2mint.github.io/epythet/

Compile docs for github
::

    cd PROJECT_DIR/docsrc
    make github

Push generated ``PROJECT_DIR/docs`` to ``master`` branch

Editing and Customizing Docs
----------------------------

You can add RST documentation directly in the source files.
`This source file for example <https://github.com/i2mint/epythet/blob/master/epythet/docs_gen/__init__.py>`_.
"""

from pathlib import Path
_STATIC_FILES = Path(__file__).absolute().parent / '_static'

from epythet.docs_gen.autogen import make_autodocs
from epythet.docs_gen.setup_docsrc import make_docsrc


argh_kwargs = {
    'namespace': 'docs_gen',
    'functions': [
        make_docsrc,
        make_autodocs,
    ],
    'namespace_kwargs': {
        'title': 'Documentation Generator',
        'description': 'Setup and generate Sphinx docs effortlessly'
    }
}

if __name__ == '__main__':
    import argh  # pip install argh
    argh.dispatch_commands(argh_kwargs.get('functions', None))
