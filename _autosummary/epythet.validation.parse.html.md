# epythet.validation.parse

Level 0.5: parse each docstring’s docutils doctree and run the ledger’s detectors.

This is the load-bearing level of `epythet validate`: the research measured
that a strict `sphinx-build -W -n` is silent on 12 of 21 artifact classes,
while the doctree of the docstring, parsed in isolation, exposes 20 of them at
about a thousand docstrings per second and without a build.

Two things make a naive implementation fail and are handled here:

- plain docutils knows nothing of `:func:`, `.. versionadded::` and the
  rest of Sphinx’s vocabulary, so stub roles and directives are registered
  first (otherwise nearly every correct Sphinx docstring is flagged);
- with `sphinx.ext.napoleon` enabled fleet-wide, Google sections are
  rewritten before docutils sees them, so the same transform is applied here
  (`napoleon=True`) and rules can opt out via `applies_to.napoleon`.

`file_insertion_enabled` and `raw_enabled` are off so that a docstring can
never make the validator read a file or inject raw HTML.

### Module Attributes

| [`ONE_ARGUMENT_DIRECTIVES`](#epythet.validation.parse.ONE_ARGUMENT_DIRECTIVES)   | Directives whose real implementation takes at most one argument.   |
|----------------------------------------------------------------------------|--------------------------------------------------------------------|

### Functions

| [`evaluate_rule`](#epythet.validation.parse.evaluate_rule)(rule, parsed)                    | Run one parse-level rule over one parsed docstring; returns the evidence list.      |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`findings_for`](#epythet.validation.parse.findings_for)(parsed, rules, \*[, level])       | One finding per (docstring, rule) that fired, carrying the first hit and the count. |
| [`install_stubs`](#epythet.validation.parse.install_stubs)()                                | Register stub Sphinx roles and directives with docutils (idempotent).               |
| [`napoleon_transform`](#epythet.validation.parse.napoleon_transform)(text)                       | Rewrite Google/NumPy sections into RST fields the way `sphinx.ext.napoleon` does.   |
| [`parse_docstring`](#epythet.validation.parse.parse_docstring)(docstring, \*[, napoleon])     | Parse one docstring (after the optional napoleon transform).                        |
| [`parse_rst`](#epythet.validation.parse.parse_rst)(text)                                | Parse RST text into a doctree, returning it with the docutils messages.             |
| [`run_parse_level`](#epythet.validation.parse.run_parse_level)(docstrings, ledger, \*[, ...]) | Level 0.5 over a stream of docstrings.                                              |
| [`sphinx_available`](#epythet.validation.parse.sphinx_available)()                             | Whether `sphinx.ext.napoleon` can be imported.                                      |

### Classes

| [`ParsedDocstring`](#epythet.validation.parse.ParsedDocstring)(docstring, text, tree, messages)   | One docstring, its (possibly napoleon-transformed) text, doctree and messages.   |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|

### epythet.validation.parse.ONE_ARGUMENT_DIRECTIVES *= frozenset({'code', 'code-block', 'literalinclude', 'math', 'sourcecode'})*

Directives whose real implementation takes at most one argument.

### *class* epythet.validation.parse.ParsedDocstring(docstring, text, tree, messages, \_paragraphs=None, \_literals=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One docstring, its (possibly napoleon-transformed) text, doctree and messages.

#### *property* literals *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

Text of every inline literal.

#### *property* paragraphs *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

Prose of every paragraph not inside a system message.

Text inside inline `literal` nodes is left out, so a field marker
quoted as code (double backticks around `:param x:`) never trips a
prose regex.

#### texts_for(node)

The text corpus a `regex` detector scans: `paragraph`, `literal` or `any`.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.parse.evaluate_rule(rule, parsed)

Run one parse-level rule over one parsed docstring; returns the evidence list.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.parse.findings_for(parsed, rules, , level=0.5)

One finding per (docstring, rule) that fired, carrying the first hit and the count.

A rule whose detector declares `only_if_no_other_hits: true` (the
catch-all DR032) is evaluated last and reported only when nothing more
specific fired on the same docstring, so a docutils message never appears
twice under two rule ids.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)]

### epythet.validation.parse.install_stubs()

Register stub Sphinx roles and directives with docutils (idempotent).

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.validation.parse.napoleon_transform(text)

Rewrite Google/NumPy sections into RST fields the way `sphinx.ext.napoleon` does.

Returns `text` unchanged when Sphinx is not importable; the caller records
a note in that case.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.validation.parse.parse_docstring(docstring, , napoleon=True)

Parse one docstring (after the optional napoleon transform).

* **Return type:**
  [`ParsedDocstring`](#epythet.validation.parse.ParsedDocstring)

### epythet.validation.parse.parse_rst(text)

Parse RST text into a doctree, returning it with the docutils messages.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[`document`, [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]

### epythet.validation.parse.run_parse_level(docstrings, ledger, , napoleon=True)

Level 0.5 over a stream of docstrings.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)]

### epythet.validation.parse.sphinx_available()

Whether `sphinx.ext.napoleon` can be imported.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)
