# epythet.build

### epythet.build(config, target='html', , overrides=None)

Run one build target for a loaded configuration; returns the output directory.

* **Parameters:**
  * **config** ([`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig)) – the project’s configuration
  * **target** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – a Sphinx builder name or one of `github`, `gitlab`, `clean`
  * **overrides** ([`dict`](https://docs.python.org/3/library/stdtypes.html#dict) | [`None`](https://docs.python.org/3/library/constants.html#None)) – configuration overrides forwarded to the generated `conf.py`
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/library/constants.html#None)
