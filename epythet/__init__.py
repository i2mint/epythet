"""Setup and generate Sphinx docs effortlessly

Console Scripts
---------------

To see available commands
::

    epythet --help

Quickstart
----------
As easy as 1, 2, 3

Prequisite
==========
Check your ``PROJECT_DIR/setup.cfg`` contains::

    [metadata]
    name = epythet
    version = 0.0.27
    author = Otosense
    copyright = 2020, Otosense
    display_name = Epythet


1. Setup Sphinx docsrc
======================
One time setup to create docsrc folder with Sphinx docs config and makefile.  Commit docsrc into your git repo.

Python::

    from epythet.setup_docsrc import make_docsrc
    make_docsrc(PROJECT_DIR)

Command Line::

    epythet make-docsrc PROJECT_DIR

2. Generate module docs
=======================
Generate rst docs for all .py modules in your package.  Use make_autodocs each time there is a new .py file added.
These rst files generated in the docsrc folder should also be commited into your git repo.

Python::

    from epythet.autogen import make_autodocs
    make_autodocs(PROJECT_DIR)

Command Line::

    epythet make-autodocs PROJECT_DIR

3. Compile docs
===============
Compile generated rst docs with Sphinx makefile.  Use this each time you make changes to your .py files or .rst files.

Python::

    from epythet.call_make import make
    make(PROJECT_DIR, 'html')

Command Line::

    epythet make PROJECT_DIR html

View by opening ``PROJECT_DIR/docsrc/_build/html/index.html``

Github Pages
------------

Go to your repo settings and set GitHub Pages site to build from the ``/docs`` folder in the ``master`` branch.
That is:
- Go to {github_repo}/settings
- Scroll down to "GitHub" Pages section.
- For epythet, the settings look like this:
.. |GithubPagesSetup| image:: https://user-images.githubusercontent.com/1906276/113177929-e71d9e80-9202-11eb-918e-1f7421dff06f.png

More detailed instructions `here <https://docs.github.com/en/github/working-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>`_

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
`This source file for example <https://github.com/i2mint/epythet/blob/master/epythet/__init__.py>`_.

"""

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
