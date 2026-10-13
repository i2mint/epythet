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
doctest blocks, literal blocks, directive bodies and ASCII-art drawings are
left byte-for-byte alone, because doctests are executed and code is code.

**The principle: rewrite only what is unambiguous; otherwise report.** A rule
fires when the line can mean one thing (a `>>>` glued to prose is a doctest;
a 

```
``
```

\`\` `` ``` fence is a fence) and stays out when the author’s intent has two
readings. So a `#` line becomes a rubric only when it is shaped like a
Markdown heading and stands alone between blank lines, never when it could be
a code comment; `text:` followed by an indented block becomes a literal
block only when the block reads as code, never when it reads as a paragraph or
a definition; a section one-liner folds in the prose that wraps it, never a
field list that follows it; and nothing at all is rewritten inside the body of
a Google section (an argument called `x:` is not a literal block marker, an
argument called `error:` is not a section) or inside a drawing. What the
rules leave alone, `epythet validate` reports (DR014 for the accidental
definition list, DR002 for the bare section header, DR031 for the commented
doctest), so nothing is silently dropped: the same fixture that pins a rule’s
silence pins the finding that replaces it.

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
   list or field list that follows prose, and after an indented block ends;
   not when the block sits directly under its own section header.
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

| [`GOOGLE_SECTIONS`](#epythet.normalizer.GOOGLE_SECTIONS)   | Section names napoleon recognises (Google style), lowercase.               |
|--------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`PROSE_WORDS`](#epythet.normalizer.PROSE_WORDS)       | How many plain words make a line read as prose rather than code.           |
| [`ART_MIN_LINES`](#epythet.normalizer.ART_MIN_LINES)     | How many lines of a run must be drawing lines for the run to be a drawing. |
| [`DEFAULT_RULES`](#epythet.normalizer.DEFAULT_RULES)     | The rules that run by default, in order.                                   |

### Functions

| [`bare_headers_to_rubrics`](#epythet.normalizer.bare_headers_to_rubrics)(lines)                 | Turn a section header with no indented body into a rubric.                           |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`blank_lines_between_blocks`](#epythet.normalizer.blank_lines_between_blocks)(lines)              | Separate prose from the doctest, list, field list or indented block after it.        |
| [`escape_unmatched_stars`](#epythet.normalizer.escape_unmatched_stars)(lines)                  | Escape `*args` and `**kwargs` in prose so they are not read as emphasis.             |
| [`fences_to_code_blocks`](#epythet.normalizer.fences_to_code_blocks)(lines)                   | Turn Markdown code fences into <br/><br/>```<br/>``<br/>```<br/><br/>.               |
| [`fix_short_underlines`](#epythet.normalizer.fix_short_underlines)(lines)                    | Extend a title underline that is shorter than its title.                             |
| [`google_one_liners`](#epythet.normalizer.google_one_liners)(lines)                       | Expand `Returns: text` (and other one-line sections) into real sections.             |
| [`google_section_bodies`](#epythet.normalizer.google_section_bodies)(lines)                   | For every line, the indentation of the Google section body it is in, else `None`.    |
| [`indent_of`](#epythet.normalizer.indent_of)(line)                                | Number of leading spaces (tabs count as one).                                        |
| [`is_art_line`](#epythet.normalizer.is_art_line)(line)                              | Whether `line` is a piece of a drawing: box characters, arrows, or mostly strokes.   |
| [`line_contexts`](#epythet.normalizer.line_contexts)(lines)                           | Classify every line as blank, prose, doctest, literal, list, field, fence or art.    |
| [`literal_block_after_colon`](#epythet.normalizer.literal_block_after_colon)(lines)               | Make `text:` followed by an indented block a proper `::` literal block.              |
| [`markdown_headings_to_rubrics`](#epythet.normalizer.markdown_headings_to_rubrics)(lines)            | Render `## Heading` as a rubric instead of a literal `##`.                           |
| [`markdown_links_to_rst`](#epythet.normalizer.markdown_links_to_rst)(lines)                   | Rewrite `[text](url)` links as RST hyperlinks, outside code and literals.            |
| [`normalize_docstring`](#epythet.normalizer.normalize_docstring)(lines, \*[, rules])        | Apply `rules` in order to a docstring given as lines (no trailing newlines).         |
| [`normalize_text`](#epythet.normalizer.normalize_text)(text, \*[, rules])              | Apply `rules` to a docstring given as one string.                                    |
| [`reflow_list_continuations`](#epythet.normalizer.reflow_list_continuations)(lines)               | Indent a wrapped list or field line that sits at the marker's own indentation.       |
| [`resolve_rules`](#epythet.normalizer.resolve_rules)(rules)                           | Accept rule functions or dotted import paths (`"pkg.mod:func"` or `"pkg.mod.func"`). |
| [`setup`](#epythet.normalizer.setup)(app)                                     | Sphinx extension entry point: `extensions = ["epythet.normalizer"]`.                 |
| [`sphinx_process_docstring`](#epythet.normalizer.sphinx_process_docstring)(app, what, name, ...) | The `autodoc-process-docstring` handler: normalizes `lines` in place.                |

### epythet.normalizer.ART_MIN_LINES *= 2*

How many lines of a run must be drawing lines for the run to be a drawing.

### epythet.normalizer.DEFAULT_RULES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Callable](https://docs.python.org/3/library/typing.html#typing.Callable)[[[list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]], [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]], ...]* *= (<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>, <function escape_unmatched_stars>)*

The rules that run by default, in order.

### epythet.normalizer.GOOGLE_SECTIONS *= frozenset({'args', 'arguments', 'attention', 'attributes', 'caution', 'danger', 'error', 'example', 'examples', 'hint', 'important', 'keyword args', 'keyword arguments', 'methods', 'note', 'notes', 'other parameters', 'parameters', 'raise', 'raises', 'receive', 'receives', 'references', 'return', 'returns', 'see also', 'tip', 'todo', 'warn', 'warning', 'warnings', 'warns', 'yield', 'yields'})*

Section names napoleon recognises (Google style), lowercase.

### epythet.normalizer.PROSE_WORDS *= 4*

How many plain words make a line read as prose rather than code.

### epythet.normalizer.bare_headers_to_rubrics(lines)

Turn a section header with no indented body into a rubric.

napoleon only recognises `Examples:` when its content is indented; when
the doctest below sits at the same indentation, the header rendered as a
stray paragraph. A rubric is what napoleon itself emits for the section.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

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
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("Prose\n>>> f()\n1", rules=[blank_lines_between_blocks])
'Prose\n\n>>> f()\n1'
>>> normalize_text("Prose\n:param x: y\n    more\n:param z: w", rules=[blank_lines_between_blocks])
'Prose\n\n:param x: y\n    more\n:param z: w'
>>> normalize_text("Text:\n    indented\nback", rules=[blank_lines_between_blocks])
'Text:\n    indented\n\nback'
```

Inside a Google section body the entries are a definition list, where
consecutive terms need no blank line between them, so a dedent from a
wrapped `Args:` entry to the next entry is left as written:

```pycon
>>> normalize_text("Args:\n    a: one that\n        wraps.\n    b: two.", rules=[blank_lines_between_blocks])
'Args:\n    a: one that\n        wraps.\n    b: two.'
```

A block immediately under its own section header is left alone: napoleon
renders `Examples:` followed directly by a doctest or list identically
with or without the blank line, so inserting one only trips `D412`
(pydocstyle’s “no blank lines between a section header and its content”).

```pycon
>>> normalize_text("Examples:\n    >>> f()\n    1", rules=[blank_lines_between_blocks])
'Examples:\n    >>> f()\n    1'
```

### epythet.normalizer.escape_unmatched_stars(lines)

Escape `*args` and `**kwargs` in prose so they are not read as emphasis.

Only a star run that is never closed on the same line is escaped, so real
`*emphasis*` and `**strong**` are untouched.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("Takes *args and **kwargs, *really*.", rules=[escape_unmatched_stars])
'Takes \\*args and \\*\\*kwargs, *really*.'
```

### epythet.normalizer.fences_to_code_blocks(lines)

Turn Markdown code fences into `.. code-block::` directives.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("Run:\n```bash\npip install x\n```\nDone.", rules=[fences_to_code_blocks])
'Run:\n\n.. code-block:: bash\n\n    pip install x\n\nDone.'
```

### epythet.normalizer.fix_short_underlines(lines)

Extend a title underline that is shorter than its title.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("Examples\n----\ntext", rules=[fix_short_underlines])
'Examples\n--------\ntext'
```

### epythet.normalizer.google_one_liners(lines)

Expand `Returns: text` (and other one-line sections) into real sections.

Prose lines that wrap the sentence at the same indentation are folded into
the section body; a field list, a bullet list, a Markdown heading or another
section ends it. Inside the body of another section the line is an entry
(an argument called `error`), not a header, and is left alone.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("Returns: a thing that\nspans two lines.\n\nNext.", rules=[google_one_liners])
'Returns:\n    a thing that\n    spans two lines.\n\nNext.'
>>> normalize_text("Returns: a thing.\n## Notes\nText.", rules=[google_one_liners])
'Returns:\n    a thing.\n\n## Notes\nText.'
>>> normalize_text("Note: be careful.\n:return: the thing", rules=[google_one_liners])
'Note:\n    be careful.\n\n:return: the thing'
```

### epythet.normalizer.google_section_bodies(lines)

For every line, the indentation of the Google section body it is in, else `None`.

A section is a known header (`Args:`, `Returns:`, …) on its own line
with an indented body below; the body ends at the first non-blank line
that is not deeper than the header. Rules use this to stay out of section
bodies, where `x:` is an argument and not a literal-block lead-in.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)]

```pycon
>>> google_section_bodies(["Args:", "    x: the x", "        more", "", "Text."])
[None, 4, 4, 4, None]
```

### epythet.normalizer.indent_of(line)

Number of leading spaces (tabs count as one).

* **Return type:**
  [`int`](https://docs.python.org/3/builtins/functions.html#int)

```pycon
>>> indent_of("    x"), indent_of("x"), indent_of("")
(4, 0, 0)
```

### epythet.normalizer.is_art_line(line)

Whether `line` is a piece of a drawing: box characters, arrows, or mostly strokes.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

```pycon
>>> is_art_line("│ 0 │ ──▶ │ 2 │"), is_art_line("  +----+"), is_art_line("- a bullet")
(True, True, False)
>>> is_art_line("func1 --> merge"), is_art_line("x = 1  # comment")
(True, False)
```

### epythet.normalizer.line_contexts(lines)

Classify every line as blank, prose, doctest, literal, list, field, fence or art.

The classification is what keeps every rule away from code: a line inside a
doctest block, a `::` literal block, a directive body, a Markdown fence or
an ASCII-art drawing is never rewritten.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> line_contexts(["Text:", "", "    >>> 1", "    1", "", "- a", "  b", "", ":param x: y"])
['prose', 'blank', 'doctest', 'doctest', 'blank', 'list', 'list', 'blank', 'field']
>>> line_contexts(["    >>> 1", "    1", "back to prose"])
['doctest', 'doctest', 'prose']
>>> line_contexts(["a --> b", "  |", "  v", "- c"])
['art', 'art', 'art', 'list']
```

### epythet.normalizer.literal_block_after_colon(lines)

Make `text:` followed by an indented block a proper `::` literal block.

Only when the block is unmistakably code (`_looks_like_code()`: no
line reads as prose and some line carries a code signal such as `=`,
`(` or `#`), and never inside a Google section body, where `x:` is an
argument. A lead-in over an indented paragraph is a definition list the
author may have meant; it is left alone and DR014 reports it. A lone
`Usage:` or `Output:` over a command or a value is code all the same.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("For example:\n    x = f(1)\nThen more.", rules=[literal_block_after_colon])
'For example::\n\n    x = f(1)\n\nThen more.'
>>> normalize_text("Usage:\n    python run.py  # top 12", rules=[literal_block_after_colon])
'Usage::\n\n    python run.py  # top 12'
>>> normalize_text("specifying:\n    the name of the thing to do.", rules=[literal_block_after_colon])
'specifying:\n    the name of the thing to do.'
>>> normalize_text("Args:\n    x:\n        The x.", rules=[literal_block_after_colon])
'Args:\n    x:\n        The x.'
```

### epythet.normalizer.markdown_headings_to_rubrics(lines)

Render `## Heading` as a rubric instead of a literal `##`.

A `#` line is also how a code comment, a commented-out doctest and its
output (`# True`) or a commented-out paragraph look, so the rule wants a
heading shape: `#` marks, a space, then a title that starts with a
capital letter, a digit or a backtick, holds no code (`=`, `(`,
`>>>`) and no trailing `:` or `.`, and is not a `TODO:` tag. A
single `#` must also follow a blank line (or open the docstring);
`##` and deeper may sit against prose. No heading of any level sits
against another `#` line (that is a commented-out paragraph or doctest)
or right after code.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("Intro.\n## Usage\nText.", rules=[markdown_headings_to_rubrics])
'Intro.\n\n.. rubric:: Usage\n\nText.'
>>> normalize_text("# >>> f()\n# True", rules=[markdown_headings_to_rubrics])
'# >>> f()\n# True'
>>> normalize_text("# Making a signature\nText.", rules=[markdown_headings_to_rubrics])
'.. rubric:: Making a signature\n\nText.'
>>> normalize_text("Intro.\n# Not a heading\n\nText.", rules=[markdown_headings_to_rubrics])
'Intro.\n# Not a heading\n\nText.'
```

### epythet.normalizer.markdown_links_to_rst(lines)

Rewrite `[text](url)` links as RST hyperlinks, outside code and literals.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_text("See [the docs](https://x.org/a) now.", rules=[markdown_links_to_rst])
'See `the docs <https://x.org/a>`_ now.'
```

### epythet.normalizer.normalize_docstring(lines, \*, rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>, <function escape_unmatched_stars>))

Apply `rules` in order to a docstring given as lines (no trailing newlines).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> normalize_docstring(["Text", ">>> 1", "1"])
['Text', '', '>>> 1', '1']
```

### epythet.normalizer.normalize_text(text, \*, rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>, <function escape_unmatched_stars>))

Apply `rules` to a docstring given as one string.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

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
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

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
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]], [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]], [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]

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
