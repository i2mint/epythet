# epythet.normalizer

Build-time docstring normalizer: fix the markup artifacts people actually write.

Docstrings in the wild mix reStructuredText, Google sections and Markdown
habits. Sphinx renders the RST and napoleon handles the Google sections, but a
handful of recurring slips render wrongly, mostly *silently*: a doctest glued
to the prose above it becomes a paragraph starting with `>>>`; a Markdown
fence is printed literally; `Returns: text` on one line is just a sentence;
`*args` opens an emphasis that never closes.

This module rewrites those cases on the fly, in the `autodoc-process-docstring`
event, so the rendered site is right without editing any source. Each rule is a
pure function `list[str] -> list[str]` and [`DEFAULT_RULES`](#epythet.normalizer.DEFAULT_RULES) is the
ordered tuple that runs by default. The rules only touch prose: lines inside
doctest blocks, literal blocks and directive bodies are left byte-for-byte
alone, because doctests are executed and code is code.

The rules, in order:

1. `fences_to_code_blocks`: 

   ```
   ``
   ```

   \`\` ``lang ``` fences become `.. code-block:: lang`.
2. `fix_short_underlines`: a section underline shorter than its title is extended.
3. `google_one_liners`: `Returns: text` becomes a real `Returns:` section.
4. `bare_headers_to_rubrics`: `Examples:` with unindented content becomes a rubric.
5. `markdown_headings_to_rubrics`: `## Title` becomes `.. rubric:: Title`.
6. `literal_block_after_colon`: prose ending in `:` followed by an indented
   block gets the `::` that makes it a literal block.
7. `reflow_list_continuations`: a wrapped list or field line at the marker’s
   own indentation is indented under it.
8. `blank_lines_between_blocks`: a blank line is inserted before a doctest,
   list or field list that follows prose, and after an indented block ends.
9. `markdown_links_to_rst`: `[text](url)` becomes ``text <url>`_`.
10. `escape_unmatched_stars`: `*args` / `**kwargs` in prose are escaped.

```pycon
>>> print(normalize_text('''Do the thing.
... Options are:
... - fast
... - slow
... Returns: the answer, which may
... span lines.
... '''))
Do the thing.
Options are:

- fast
- slow

:returns: the answer, which may
          span lines.
```

<BLANKLINE>
>>> normalize_docstring([“Text”, “    >>> f(1)”, “    3”])
[‘Text’, ‘’, ‘    >>> f(1)’, ‘    3’]

### Module Attributes

| [`GOOGLE_SECTIONS`](#epythet.normalizer.GOOGLE_SECTIONS)   | Section names napoleon recognises (Google style), lowercase.   |
|--------------------------------------------------------------------|----------------------------------------------------------------|
| [`DEFAULT_RULES`](#epythet.normalizer.DEFAULT_RULES)     | The rules that run by default, in order.                       |

### Functions

| [`bare_headers_to_rubrics`](#epythet.normalizer.bare_headers_to_rubrics)(lines)                 | Turn a section header with no indented body into a rubric.                           |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`blank_lines_between_blocks`](#epythet.normalizer.blank_lines_between_blocks)(lines)              | Separate prose from the doctest, list, field list or indented block after it.        |
| [`escape_unmatched_stars`](#epythet.normalizer.escape_unmatched_stars)(lines)                  | Escape `*args` and `**kwargs` in prose so they are not read as emphasis.             |
| [`fences_to_code_blocks`](#epythet.normalizer.fences_to_code_blocks)(lines)                   | Turn Markdown code fences into <br/><br/>```<br/>``<br/>```<br/><br/>.               |
| [`fix_short_underlines`](#epythet.normalizer.fix_short_underlines)(lines)                    | Extend a title underline that is shorter than its title.                             |
| [`google_one_liners`](#epythet.normalizer.google_one_liners)(lines)                       | Expand `Returns: text` (and other one-line sections) into real sections.             |
| [`indent_of`](#epythet.normalizer.indent_of)(line)                                | Number of leading spaces (tabs count as one).                                        |
| [`line_contexts`](#epythet.normalizer.line_contexts)(lines)                           | Classify every line as blank, prose, doctest, literal, list, field or fence.         |
| [`literal_block_after_colon`](#epythet.normalizer.literal_block_after_colon)(lines)               | Make `text:` followed by an indented block a proper `::` literal block.              |
| [`markdown_headings_to_rubrics`](#epythet.normalizer.markdown_headings_to_rubrics)(lines)            | Render `## Heading` as a rubric instead of a literal `##`.                           |
| [`markdown_links_to_rst`](#epythet.normalizer.markdown_links_to_rst)(lines)                   | Rewrite `[text](url)` links as RST hyperlinks, outside code and literals.            |
| [`normalize_docstring`](#epythet.normalizer.normalize_docstring)(lines, \*[, rules])        | Apply `rules` in order to a docstring given as lines (no trailing newlines).         |
| [`normalize_text`](#epythet.normalizer.normalize_text)(text, \*[, rules])              | Apply `rules` to a docstring given as one string.                                    |
| [`reflow_list_continuations`](#epythet.normalizer.reflow_list_continuations)(lines)               | Indent a wrapped list or field line that sits at the marker's own indentation.       |
| [`resolve_rules`](#epythet.normalizer.resolve_rules)(rules)                           | Accept rule functions or dotted import paths (`"pkg.mod:func"` or `"pkg.mod.func"`). |
| [`setup`](#epythet.normalizer.setup)(app)                                     | Sphinx extension entry point: `extensions = ["epythet.normalizer"]`.                 |
| [`sphinx_process_docstring`](#epythet.normalizer.sphinx_process_docstring)(app, what, name, ...) | The `autodoc-process-docstring` handler: normalizes `lines` in place.                |

### epythet.normalizer.DEFAULT_RULES *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Callable](https://docs.python.org/3/library/typing.html#typing.Callable)[[[list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]], [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]], ...]* *= (<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>, <function escape_unmatched_stars>)*

The rules that run by default, in order.

### epythet.normalizer.GOOGLE_SECTIONS *= frozenset({'args', 'arguments', 'attention', 'attributes', 'caution', 'danger', 'error', 'example', 'examples', 'hint', 'important', 'keyword args', 'keyword arguments', 'methods', 'note', 'notes', 'other parameters', 'parameters', 'raise', 'raises', 'receive', 'receives', 'references', 'return', 'returns', 'see also', 'tip', 'todo', 'warn', 'warning', 'warnings', 'warns', 'yield', 'yields'})*

Section names napoleon recognises (Google style), lowercase.

### epythet.normalizer.bare_headers_to_rubrics(lines)

Turn a section header with no indented body into a rubric.

napoleon only recognises `Examples:` when its content is indented; when
the doctest below sits at the same indentation, the header rendered as a
stray paragraph. A rubric is what napoleon itself emits for the section.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Examples:\n\n>>> f()\n1", rules=[bare_headers_to_rubrics])
'.. rubric:: Examples\n\n>>> f()\n1'
```

### epythet.normalizer.blank_lines_between_blocks(lines)

Separate prose from the doctest, list, field list or indented block after it.

The missing blank line before `>>>` is the single most common artifact in
the fleet: without it Sphinx renders the doctest as a paragraph and
`sphinx.ext.doctest` never runs it.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Prose\n>>> f()\n1", rules=[blank_lines_between_blocks])
'Prose\n\n>>> f()\n1'
>>> normalize_text("Prose\n:param x: y\n    more\n:param z: w", rules=[blank_lines_between_blocks])
'Prose\n\n:param x: y\n    more\n:param z: w'
>>> normalize_text("Text:\n    indented\nback", rules=[blank_lines_between_blocks])
'Text:\n    indented\n\nback'
```

### epythet.normalizer.escape_unmatched_stars(lines)

Escape `*args` and `**kwargs` in prose so they are not read as emphasis.

Only a star run that is never closed on the same line is escaped, so real
`*emphasis*` and `**strong**` are untouched.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Takes *args and **kwargs, *really*.", rules=[escape_unmatched_stars])
'Takes \\*args and \\*\\*kwargs, *really*.'
```

### epythet.normalizer.fences_to_code_blocks(lines)

Turn Markdown code fences into `.. code-block::` directives.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Run:\n```bash\npip install x\n```\nDone.", rules=[fences_to_code_blocks])
'Run:\n\n.. code-block:: bash\n\n    pip install x\n\nDone.'
```

### epythet.normalizer.fix_short_underlines(lines)

Extend a title underline that is shorter than its title.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Examples\n----\ntext", rules=[fix_short_underlines])
'Examples\n--------\ntext'
```

### epythet.normalizer.google_one_liners(lines)

Expand `Returns: text` (and other one-line sections) into real sections.

Continuation lines at the same indentation are folded into the section body.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Returns: a thing that\nspans two lines.\n\nNext.", rules=[google_one_liners])
'Returns:\n    a thing that\n    spans two lines.\n\nNext.'
```

### epythet.normalizer.indent_of(line)

Number of leading spaces (tabs count as one).

* **Return type:**
  [`int`](https://docs.python.org/3/library/functions.html#int)

```pycon
>>> indent_of("    x"), indent_of("x"), indent_of("")
(4, 0, 0)
```

### epythet.normalizer.line_contexts(lines)

Classify every line as blank, prose, doctest, literal, list, field or fence.

The classification is what keeps every rule away from code: a line inside a
doctest block, a `::` literal block, a directive body or a Markdown fence
is never rewritten.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> line_contexts(["Text:", "", "    >>> 1", "    1", "", "- a", "  b", "", ":param x: y"])
['prose', 'blank', 'doctest', 'doctest', 'blank', 'list', 'list', 'blank', 'field']
>>> line_contexts(["    >>> 1", "    1", "back to prose"])
['doctest', 'doctest', 'prose']
```

### epythet.normalizer.literal_block_after_colon(lines)

Make `text:` followed by an indented block a proper `::` literal block.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("For example:\n    x = f(1)\nThen more.", rules=[literal_block_after_colon])
'For example::\n\n    x = f(1)\n\nThen more.'
```

### epythet.normalizer.markdown_headings_to_rubrics(lines)

Render `## Heading` as a rubric instead of a literal `##`.

A `#` line right after code is left alone: it is most likely a comment
that fell out of a doctest.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("Intro.\n## Usage\nText.", rules=[markdown_headings_to_rubrics])
'Intro.\n\n.. rubric:: Usage\n\nText.'
```

### epythet.normalizer.markdown_links_to_rst(lines)

Rewrite `[text](url)` links as RST hyperlinks, outside code and literals.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("See [the docs](https://x.org/a) now.", rules=[markdown_links_to_rst])
'See `the docs <https://x.org/a>`_ now.'
```

### epythet.normalizer.normalize_docstring(lines, \*, rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>, <function escape_unmatched_stars>))

Apply `rules` in order to a docstring given as lines (no trailing newlines).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_docstring(["Text", ">>> 1", "1"])
['Text', '', '>>> 1', '1']
```

### epythet.normalizer.normalize_text(text, \*, rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>, <function escape_unmatched_stars>))

Apply `rules` to a docstring given as one string.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> normalize_text("Text\n>>> 1\n1")
'Text\n\n>>> 1\n1'
```

### epythet.normalizer.reflow_list_continuations(lines)

Indent a wrapped list or field line that sits at the marker’s own indentation.

`- a long item that wraps\nonto the next line` is not a continuation in
RST (the list “ends without a blank line”). Indenting the wrapped line under
the marker makes it one. A line that reads like a new sentence after a
finished item is separated with a blank line instead.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> normalize_text("- item that\nwraps\n- two", rules=[reflow_list_continuations])
'- item that\n  wraps\n- two'
>>> normalize_text("- item.\nNext paragraph", rules=[reflow_list_continuations])
'- item.\n\nNext paragraph'
```

### epythet.normalizer.resolve_rules(rules)

Accept rule functions or dotted import paths (`"pkg.mod:func"` or `"pkg.mod.func"`).

Dotted paths are what a `conf.py` can hold: Sphinx cannot pickle functions
in its configuration, and a ledger of autofixable rules ships names.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]], [`...`](https://docs.python.org/3/library/constants.html#Ellipsis)]

```pycon
>>> [r.__name__ for r in resolve_rules(["epythet.normalizer.fences_to_code_blocks"])]
['fences_to_code_blocks']
```

### epythet.normalizer.setup(app)

Sphinx extension entry point: `extensions = ["epythet.normalizer"]`.

`epythet.sphinx_ext` registers the same hook; listing both is harmless.

### epythet.normalizer.sphinx_process_docstring(app, what, name, obj, options, lines)

The `autodoc-process-docstring` handler: normalizes `lines` in place.

`options` is deliberately never touched (its mapping interface is
deprecated in Sphinx 9). Register with `priority=400` so this runs before
napoleon (priority 500) sees the docstring.
