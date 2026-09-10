# epythet.scaffold

### epythet.scaffold(config, , verbose=True, pages=())

Write the docsrc files for an already-loaded configuration.

* **Parameters:**
  **pages** ([`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[`PageSpec`]) – extra generated pages, written next to `index.md` and added
  to its toctree after the API entry (the seam for e.g. a “For AI agents”
  page).
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
