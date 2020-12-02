# epythet

Documentation and packaging tools.
Less humdrum, more automation, earlier at the pub. 

[Full documentation here](https://i2mint.github.io/epythet/index.html)

# Install

Just
```
pip install epythet
```

Oh, and also you'll need [sphinx-doc](https://www.sphinx-doc.org/en/master/usage/installation.html), which you can get on linux by:

```
$ apt-get install python3-sphinx
```

and on macOS with

```
brew install sphinx-doc
```

and on windows by googling it.


# Quickstart

## Setup Sphinx docsrc

```python
from epythet.docs_gen.setup_docsrc import make_docsrc
make_docsrc(PROJECT_DIR)
```

## Generate module docs

```python
from epythet.docs_gen.autogen import make_autodocs
make_autodocs(PROJECT_DIR)
```

Compile docs

```
cd PROJECT_DIR/docsrc
make html
```

View by opening `PROJECT_DIR/docsrc/_build/html/index.html`.

# Github Pages
Go to your repo settings and set GitHub Pages site to build from the /docs folder in the master branch. Github will tell you where it will be published. In this case, the site is published at https://i2mint.github.io/epythet/

Compile docs for github

```
cd PROJECT_DIR/docsrc
make github
```

Push generated `PROJECT_DIR/docs` to master branch

# Editing and Customizing Docs

You can add RST documentation directly in the source files. [This source file for example](https://github.com/i2mint/epythet/blob/master/epythet/docs_gen/__init__.py).
