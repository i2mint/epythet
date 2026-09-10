# epythet.sphinx_ext

epythet’s Sphinx extension: the normalizer, agent link relations and theme CSS.

Listed automatically in the generated configuration
(`extensions = [..., "epythet.sphinx_ext"]`); usable on its own in any
`conf.py` too. It registers:

- the docstring normalizer on `autodoc-process-docstring` (priority 400, so
  it runs before napoleon), see [`epythet.normalizer`](epythet.normalizer.html.md#module-epythet.normalizer);
- the `<link rel="alternate" type="text/markdown">` / `rel="describedby"`
  relations on every HTML page when `epythet_agent_outputs` is on, see
  [`epythet.agent_outputs`](epythet.agent_outputs.html.md#module-epythet.agent_outputs);
- the theme accent stylesheet `_static/epythet.css` when the chosen theme
  takes its colours from CSS variables (`epythet_theme_css`).

### Functions

| [`setup`](#epythet.sphinx_ext.setup)(app)           | Register epythet's hooks and configuration values (idempotent).   |
|-----------------------------------------------------------------------|-------------------------------------------------------------------|
| [`write_theme_css`](#epythet.sphinx_ext.write_theme_css)(app) | `builder-inited` hook: materialise the theme CSS into `_static`.  |

### epythet.sphinx_ext.setup(app)

Register epythet’s hooks and configuration values (idempotent).

### epythet.sphinx_ext.write_theme_css(app)

`builder-inited` hook: materialise the theme CSS into `_static`.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)
