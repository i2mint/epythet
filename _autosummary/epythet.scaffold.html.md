# epythet.scaffold

### epythet.scaffold(config, , verbose=True, pages=None)

Write the docsrc files for an already-loaded configuration.

* **Parameters:**
  **pages** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[`PageSpec`]]) – extra generated pages, written next to `index.md` and added
  to its toctree after the API entry. `None` (the default) means the
  conventional pages, i.e. the “For AI agents” page that
  `epythet.ai_artifacts.default_pages` produces when the project has
  agent artifacts and `ai_artifacts` is on; pass `()` for none.
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
