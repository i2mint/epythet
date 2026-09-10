# epythet.migrate

`epythet migrate-style`: rewrite RST field lists as Google (or NumPy) sections, opt-in.

The fleet keeps both conventions and napoleon renders both, so nothing here
runs by default anywhere (maintainer decision 6: normalizer only, no mass
style conversion). This is the tool for the one package, module or file
whose maintainer wants `:param x:` lines to become an `Args:` section.

It is built on [`epythet.repair`](epythet.repair.html.md#module-epythet.repair)’s machinery and inherits every one of
its guarantees: exact-span rewriting, an unchanged AST outside docstrings,
byte-identical doctest sources, and a level-0.5 re-validation of each
rewritten docstring. On top of that it only converts what round-trips:

- the *field region* is the first contiguous block of `:param`,
  `:type`, `:returns`, `:rtype` and `:raises` lines (with their
  indented continuations); prose before it and everything after it, doctests
  included, is copied verbatim;
- a region holding any other field (`:keyword`, `:var`, `:meta`, …)
  is left alone, because `docstring_parser.compose` drops or mangles those;
- the composed section is parsed back and must describe the same
  parameters, return and exceptions as the original, or the docstring is
  left alone.

The conversion itself is `docstring_parser.parse(..., style=REST)` then
`compose(..., style=GOOGLE)` (research §9); the substrate that writes it
back is the `applier=` seam of [`epythet.repair.repair()`](epythet.repair.html.md#epythet.repair.repair).

```pycon
>>> from epythet.migrate import convert_fields
>>> print(convert_fields(":param x: the x value\n:type x: int\n:returns: x doubled\n:rtype: int", to="google"))
:param x: the x value
:type x: int
```

<BLANKLINE>
:returns: x doubled
:rtype: int

### Module Attributes

| [`CONVERTIBLE_FIELDS`](#epythet.migrate.CONVERTIBLE_FIELDS)   | Field names whose conversion round-trips through `docstring_parser`.   |
|-----------------------------------------------------------------------|------------------------------------------------------------------------|

### Functions

| [`convert_fields`](#epythet.migrate.convert_fields)(region, \*[, to])                  | Convert one RST field block to a Google or NumPy section block, or `None` if unsafe.            |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| [`field_region`](#epythet.migrate.field_region)(lines)                               | `(start, end)` of the first RST field block, or `None`; `end` is exclusive.                     |
| [`field_regions`](#epythet.migrate.field_regions)(lines)                              | Every field block of a docstring, in order.                                                     |
| [`migrate_style`](#epythet.migrate.migrate_style)(path, \*[, to, write, ignore, ...]) | Convert the RST field lists under `path` (a file, package or project) to `to` sections.         |
| [`migrate_style_command`](#epythet.migrate.migrate_style_command)(path, \*[, to, write, ...]) | Rewrite RST field lists (:param x:) as Google or NumPy sections, one file or package at a time. |
| [`rst_fields_to_sections`](#epythet.migrate.rst_fields_to_sections)([to])                      | A normalizer-shaped rule (`lines -> lines`) converting the docstring's field block.             |

### epythet.migrate.CONVERTIBLE_FIELDS *= frozenset({'arg', 'argument', 'except', 'exception', 'param', 'parameter', 'raise', 'raises', 'return', 'returns', 'rtype', 'type'})*

Field names whose conversion round-trips through `docstring_parser`.

### epythet.migrate.convert_fields(region, , to='google')

Convert one RST field block to a Google or NumPy section block, or `None` if unsafe.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.migrate.field_region(lines)

`(start, end)` of the first RST field block, or `None`; `end` is exclusive.

A block starts at a field line and takes every following field line at
the same indentation and every continuation (a deeper-indented line, or a
blank line followed by one of those).

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/library/functions.html#int), [`int`](https://docs.python.org/3/library/functions.html#int)] | [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> field_region(["Summary.", "", ":param x: the x", "    more", ":returns: y", "", "Then prose."])
(2, 5)
>>> field_region(["No fields."]) is None
True
```

### epythet.migrate.field_regions(lines)

Every field block of a docstring, in order.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/library/functions.html#int), [`int`](https://docs.python.org/3/library/functions.html#int)]]

```pycon
>>> field_regions([":param x: x", "", "prose", "", ":returns: y"])
[(0, 1), (4, 5)]
```

### epythet.migrate.migrate_style(path, \*, to='google', write=False, ignore=(), ledger=None, napoleon=True, run_doctests=True, applier=<function apply_span_edits>)

Convert the RST field lists under `path` (a file, package or project) to `to` sections.

Dry run by default; see [`epythet.repair.repair()`](epythet.repair.html.md#epythet.repair.repair) for the arguments,
which are the same.

* **Return type:**
  [`RepairReport`](epythet.repair.html.md#epythet.repair.RepairReport)

### epythet.migrate.migrate_style_command(path, , to='google', write=False, ignore=None, ledger=None, no_napoleon=False, no_doctests=False, applier='span', quiet=False)

Rewrite RST field lists (:param x:) as Google or NumPy sections, one file or package at a time.

Opt-in and never part of a fleet sweep. Dry run by default: prints the
diff –write would apply. Docstrings whose fields would not round-trip
(:keyword, :var, :meta, …) are left alone and listed.

* **Parameters:**
  * **path** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – A .py file, a package directory, or a project root.
  * **to** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Target convention: google or numpy.
  * **write** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Apply the changes (after re-validating each docstring and re-running doctests).
  * **ignore** ([`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)) – Skip files whose path contains this string (repeat -i for several).
  * **ledger** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Directory of extra rule YAML files overlaid on the bundled ledger.
  * **no_napoleon** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Re-validate without napoleon’s Google/NumPy pre-processing.
  * **no_doctests** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Do not run each touched file’s doctests before and after writing.
  * **applier** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – The rewriting substrate: span (default) or libcst.
  * **quiet** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Print the summary only, not the diff.
* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.migrate.rst_fields_to_sections(to='google')

A normalizer-shaped rule (`lines -> lines`) converting the docstring’s field block.

A docstring with more than one field block is left alone: converting one
would leave a mixed-style docstring behind.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]
