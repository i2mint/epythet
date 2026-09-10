# epythet.confgen

Generate the Sphinx configuration from a [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig).

[`sphinx_settings()`](#epythet.confgen.sphinx_settings) returns the plain dict a `conf.py` would define. The
shim `docsrc/conf.py` that `epythet.scaffold.make_docsrc()` writes gets
it through `from epythet.sphinx_conf import *`; tests and tools call it
directly. Every value here is either verified in the v2 research (README
include, nested API tree, typed cross-references, agent twins) or a direct
consequence of the decision record.

```pycon
>>> from epythet.config import DocsConfig
>>> cfg = DocsConfig(project_dir="/tmp/x", name="x", package_dir="x", theme="furo", api_generator="autosummary")
>>> s = sphinx_settings(cfg)
>>> s["html_theme"], s["default_role"], "sphinx.ext.autosummary" in s["extensions"]
('furo', 'code', True)
```

### Module Attributes

| [`BASE_EXTENSIONS`](#epythet.confgen.BASE_EXTENSIONS)   | Extensions every epythet site uses, whatever the API generator.   |
|--------------------------------------------------------------------|-------------------------------------------------------------------|
| [`API_ROOT`](#epythet.confgen.API_ROOT)          | Where the API pages live under `docsrc` (and in the site URL).    |

### Functions

| [`api_toctree_entry`](#epythet.confgen.api_toctree_entry)(config)   | The document `index.md`'s toctree points at for the API pages.                 |
|------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`merge_settings`](#epythet.confgen.merge_settings)(base, extra) | Merge two settings dicts, concatenating list values instead of replacing them. |
| [`sphinx_settings`](#epythet.confgen.sphinx_settings)(config)     | The complete Sphinx `conf.py` namespace for `config`.                          |

### epythet.confgen.API_ROOT *= 'api'*

Where the API pages live under `docsrc` (and in the site URL).

### epythet.confgen.BASE_EXTENSIONS *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('sphinx.ext.napoleon', 'sphinx_autodoc_typehints', 'sphinx.ext.intersphinx', 'sphinx.ext.doctest', 'sphinx.ext.viewcode', 'sphinx.ext.githubpages', 'myst_parser', 'sphinxcontrib.mermaid', 'sphinx_copybutton', 'epythet.sphinx_ext')*

Extensions every epythet site uses, whatever the API generator.

### epythet.confgen.api_toctree_entry(config)

The document `index.md`’s toctree points at for the API pages.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> from epythet.config import DocsConfig
>>> api_toctree_entry(DocsConfig(project_dir="/tmp/x", name="x", api_generator="autosummary"))
'api'
>>> api_toctree_entry(DocsConfig(project_dir="/tmp/x", name="x", api_generator="autoapi"))
'api/index'
```

### epythet.confgen.merge_settings(base, extra)

Merge two settings dicts, concatenating list values instead of replacing them.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> merge_settings({"extensions": ["a"], "x": 1}, {"extensions": ["b"], "x": 2})
{'extensions': ['a', 'b'], 'x': 2}
```

### epythet.confgen.sphinx_settings(config)

The complete Sphinx `conf.py` namespace for `config`.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
