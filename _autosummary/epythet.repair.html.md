# epythet.repair

`epythet repair`: apply the normalizer’s source-safe rewrites to docstrings in place.

The build-time normalizer ([`epythet.normalizer`](epythet.normalizer.html.md#module-epythet.normalizer)) fixes a docstring’s
markup on the fly, so the rendered site is right without editing anything.
This module writes the same fixes *back into the source*, for the packages
that want their docstrings right at rest (decision D9). It is deliberately
narrow:

- Only the docstring literal changes. The rest of the file is copied byte
  for byte (exact-span rewriting, no unparsing), and the module’s AST with
  docstrings blanked must be identical before and after or the file is not
  written.
- Only the normalizer’s *source-safe* rules run ([`SOURCE_SAFE_RULES`](#epythet.repair.SOURCE_SAFE_RULES)):
  a blank line before a doctest, list or field list; a Markdown fence to a
  `code-block` (or a `::` literal block, `fence_style="literal"`);
  `Returns: text` one-liners to real sections; `## Heading` to a rubric;
  `[text](url)` to an RST link; short underlines padded. Escaping a
  prose `*args` is *not* source-safe (it changes what the author wrote,
  and a later reader may not know why the backslash is there), so it stays a
  diagnostic (DR010), like unmatched backticks and every other artifact the
  normalizer cannot fix.
- Every doctest keeps its source lines byte for byte (checked with
  [`doctest`](https://docs.python.org/3/library/doctest.html#module-doctest)’s own parser); a rewrite that would change one is skipped.
- Every rewritten docstring is re-validated at level 0.5: a rewrite that
  introduces a finding the original did not have is dropped. With
  `write=True` the doctests of every touched file are run before and after
  (the module is *imported* for that, so its top level runs; pass
  `run_doctests=False` / `--no-doctests` for code that must not run), and
  a file whose failures went up is restored. A module that cannot be imported
  is written but reported as unverified.
- Line endings (CRLF), a UTF-8 BOM and tab indentation are preserved; a file
  is replaced atomically.

Dry run is the default and prints a unified diff; `write=True` applies.
The seam `applier=` swaps the rewriting substrate: [`apply_span_edits()`](#epythet.repair.apply_span_edits)
(default, no dependency) or [`apply_with_libcst()`](#epythet.repair.apply_with_libcst) (when LibCST is
installed; it re-parses the module as a concrete syntax tree and replaces
the string nodes).

```pycon
>>> from epythet.repair import rewrite_docstring_literal
>>> literal = '"""Do it.\n    - one\n    - two\n    """'
>>> new, reason = rewrite_docstring_literal(literal)
>>> new.split("\n"), reason
(['"""Do it.', '', '    - one', '    - two', '    """'], None)
>>> rewrite_docstring_literal('"""Has a \\n escape."""')[1]
'non-raw literal with backslashes: escapes would change'
```

### Module Attributes

| [`SOURCE_SAFE_RULES`](#epythet.repair.SOURCE_SAFE_RULES)   | The normalizer rules whose rewrite is safe to commit to source, in normalizer order.   |
|----------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`UNSAFE_RULES`](#epythet.repair.UNSAFE_RULES)        | Normalizer rules that stay build-time only, and why.                                   |

### Functions

| [`apply_span_edits`](#epythet.repair.apply_span_edits)(source, edits)                    | Splice each edit's `after` over its `[start, end)` span, last edit first.                |
|-----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`apply_with_libcst`](#epythet.repair.apply_with_libcst)(source, edits)                   | The LibCST applier: replace the matching `SimpleString` nodes of a concrete syntax tree. |
| [`fences_to_literal_blocks`](#epythet.repair.fences_to_literal_blocks)(lines)                    | The `fence_style="literal"` variant: a fence becomes a `::` literal block.               |
| [`iter_docstring_nodes`](#epythet.repair.iter_docstring_nodes)(tree)                         | `(qualname, node, constant)` for every docstring in a parsed module.                     |
| [`render_repair`](#epythet.repair.render_repair)(report, \*[, diff])                  | The human report: the diff (dry run) or what was written, then the refusals.             |
| [`repair`](#epythet.repair.repair)(path, \*[, write, fence_style, rules, ...]) | Repair the docstrings under `path` (a file, package directory or project root).          |
| [`repair_command`](#epythet.repair.repair_command)(path, \*[, write, ...])             | Rewrite docstrings so they render right: blank lines, fences, one-liner sections, links. |
| [`repair_source`](#epythet.repair.repair_source)(source, \*[, rules, ...])            | Repair every docstring of one module's source text; nothing is written.                  |
| [`rewrite_docstring_literal`](#epythet.repair.rewrite_docstring_literal)(segment, \*[, rules])    | Rewrite one docstring literal's source; returns `(new_segment, reason_if_unsafe)`.       |
| [`rules_for`](#epythet.repair.rules_for)([fence_style, rules])                    | The rule tuple for a fence style (`literal` swaps the fence rule).                       |
| [`split_literal`](#epythet.repair.split_literal)(segment)                             | `(prefix, quote, body, closing quote)` of a string literal's source, or `None`.          |

### Classes

| [`DocstringEdit`](#epythet.repair.DocstringEdit)(qualname, line, start, end, ...)   | One docstring the repair rewrote (or refused to).   |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| [`FileRepair`](#epythet.repair.FileRepair)(path, original, repaired[, ...])      | What the repair did to one file.                    |
| [`RepairReport`](#epythet.repair.RepairReport)(root[, files, write, notes])        | Everything one `repair` run did.                    |

### *class* epythet.repair.DocstringEdit(qualname, line, start, end, before, after, reason=None, fixed=<factory>, remaining=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One docstring the repair rewrote (or refused to).

### *class* epythet.repair.FileRepair(path, original, repaired, edits=<factory>, skipped=None, written=False, verification=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What the repair did to one file.

#### diff()

The unified diff of the file, empty when nothing changed.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

#### *property* refused *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[DocstringEdit](#epythet.repair.DocstringEdit)]*

a refused rewrite, or findings no rule fixes.

A docstring that was rewritten but still has findings counts too, so
the number is the same on the dry run, the write, and the run after.

* **Type:**
  Docstrings left for a hand

### *class* epythet.repair.RepairReport(root, files=<factory>, write=False, notes=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Everything one `repair` run did.

### epythet.repair.SOURCE_SAFE_RULES *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Callable](https://docs.python.org/3/library/typing.html#typing.Callable)[[[list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]], [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]], ...]* *= (<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>)*

The normalizer rules whose rewrite is safe to commit to source, in normalizer order.

### epythet.repair.UNSAFE_RULES *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]* *= {'escape_unmatched_stars': 'escaping \*args in prose changes what the author wrote; reported as DR010 instead'}*

Normalizer rules that stay build-time only, and why.

### epythet.repair.apply_span_edits(source, edits)

Splice each edit’s `after` over its `[start, end)` span, last edit first.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.repair.apply_with_libcst(source, edits)

The LibCST applier: replace the matching `SimpleString` nodes of a concrete syntax tree.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.repair.fences_to_literal_blocks(lines)

The `fence_style="literal"` variant: a fence becomes a `::` literal block.

A literal block needs no directive support and, unlike `code-block`,
is safe inside a docstring that a doctest runner reads (a `>>>` line
inside it is still literal, but is never mistaken for a directive body).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> N.normalize_text("Run:\n```bash\npip install x\n```\nDone.", rules=[fences_to_literal_blocks])
'Run::\n\n    pip install x\n\nDone.'
```

### epythet.repair.iter_docstring_nodes(tree)

`(qualname, node, constant)` for every docstring in a parsed module.

### epythet.repair.render_repair(report, , diff=True)

The human report: the diff (dry run) or what was written, then the refusals.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.repair.repair(path, \*, write=False, fence_style='code-block', rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>), ignore=(), ledger=None, napoleon=True, revalidate=True, run_doctests=True, applier=<function apply_span_edits>)

Repair the docstrings under `path` (a file, package directory or project root).

* **Parameters:**
  * **path** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike)) – What to repair.
  * **write** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Apply the rewrites; the default only computes them (dry run).
  * **fence_style** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – What a Markdown fence becomes: `code-block` or `literal`.
  * **rules** ([`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]]) – The normalizer rules to apply; [`SOURCE_SAFE_RULES`](#epythet.repair.SOURCE_SAFE_RULES) by default.
  * **ignore** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – Path substrings to skip, as `epythet validate --ignore`.
  * **ledger** – The rule catalog used to re-validate (`None` = bundled).
  * **napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Parse docstrings with napoleon’s Google/NumPy pre-processing.
  * **revalidate** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Drop a rewrite that introduces a level-0.5 finding.
  * **run_doctests** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – With `write`, run each touched file’s doctests before
    and after, and restore a file whose failures went up.
  * **applier** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`DocstringEdit`](#epythet.repair.DocstringEdit)]], [`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – The rewriting substrate; [`apply_span_edits()`](#epythet.repair.apply_span_edits) or
    [`apply_with_libcst()`](#epythet.repair.apply_with_libcst).
* **Return type:**
  [`RepairReport`](#epythet.repair.RepairReport)

### epythet.repair.repair_command(path, , write=False, fence_style='code-block', ignore=None, ledger=None, no_napoleon=False, no_doctests=False, applier='span', quiet=False)

Rewrite docstrings so they render right: blank lines, fences, one-liner sections, links.

Dry run by default: prints a unified diff of what –write would change.
Unsafe cases (prose \*args, unmatched backticks, backslashes in a non-raw
docstring) are reported, never rewritten. Exit 0 when nothing is left to
do or every write was verified; 3 when a written file had to be restored.

* **Parameters:**
  * **path** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – A .py file, a package directory, or a project root.
  * **write** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Apply the changes (after re-validating each docstring and re-running doctests).
  * **fence_style** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – What a Markdown fence becomes: code-block or literal.
  * **ignore** ([`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)) – Skip files whose path contains this string (repeat -i for several).
  * **ledger** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Directory of extra rule YAML files overlaid on the bundled ledger.
  * **no_napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Re-validate without napoleon’s Google/NumPy pre-processing.
  * **no_doctests** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Do not run each touched file’s doctests before and after writing.
  * **applier** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – The rewriting substrate: span (default) or libcst.
  * **quiet** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Print the summary only, not the diff.
* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.repair.repair_source(source, \*, rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>), ledger_rules=(), napoleon=True, applier=<function apply_span_edits>, path=None)

Repair every docstring of one module’s source text; nothing is written.

* **Return type:**
  [`FileRepair`](#epythet.repair.FileRepair)

### epythet.repair.rewrite_docstring_literal(segment, \*, rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>))

Rewrite one docstring literal’s source; returns `(new_segment, reason_if_unsafe)`.

The body is dedented the way [`inspect.cleandoc()`](https://docs.python.org/3/library/inspect.html#inspect.cleandoc) does (the first
line stays as written), the rules run, and the result is re-indented to
the original margin. Indentation-only lines (the closing-quote line) are
preserved.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)]

### epythet.repair.rules_for(fence_style='code-block', rules=(<function fences_to_code_blocks>, <function fix_short_underlines>, <function google_one_liners>, <function bare_headers_to_rubrics>, <function markdown_headings_to_rubrics>, <function literal_block_after_colon>, <function reflow_list_continuations>, <function blank_lines_between_blocks>, <function markdown_links_to_rst>))

The rule tuple for a fence style (`literal` swaps the fence rule).

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]], [`...`](https://docs.python.org/3/library/constants.html#Ellipsis)]

### epythet.repair.split_literal(segment)

`(prefix, quote, body, closing quote)` of a string literal’s source, or `None`.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> split_literal('r"""x"""')
('r', '"""', 'x', '"""')
>>> split_literal("'y'")
('', "'", 'y', "'")
```
