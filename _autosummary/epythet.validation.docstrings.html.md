# epythet.validation.docstrings

Docstring extraction from Python source, without importing anything.

Every level below the build reads docstrings straight from the `ast`, so the
package under validation never has to be importable (and never runs). What
autodoc would see is approximated with [`inspect.cleandoc()`](https://docs.python.org/3/library/inspect.html#inspect.cleandoc), which is
what Sphinx’s `prepare_docstring` does modulo tab expansion.

Each [`Docstring`](#epythet.validation.docstrings.Docstring) carries both the *processed* text (what Python hands
to Sphinx) and the literal’s *source segment* (what the author typed), because
one seed rule (DR020, backslashes eaten by a non-raw string) is only visible
in the latter.

### Functions

| [`count_public_objects`](#epythet.validation.docstrings.count_public_objects)(package_dir, \*[, ignore])   | Count public modules, classes and functions, and those without a docstring.                 |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| [`iter_docstrings`](#epythet.validation.docstrings.iter_docstrings)(package_dir, \*[, ignore, ...])   | Yield every docstring in a package directory tree.                                          |
| [`iter_file_docstrings`](#epythet.validation.docstrings.iter_file_docstrings)(path, \*[, root, on_skip])   | Yield the module, class and function docstrings of one file, in source order.               |
| [`iter_python_files`](#epythet.validation.docstrings.iter_python_files)(package_dir, \*[, ignore])      | Every `.py` in the package tree, skipping caches, non-package dirs and `ignore` substrings. |

### Classes

| [`Coverage`](#epythet.validation.docstrings.Coverage)([checked, undocumented])              | How many public objects were seen and how many lack a docstring.   |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`Docstring`](#epythet.validation.docstrings.Docstring)(file, line, def_line, qualname, ...) | One docstring and where it came from.                              |

### *class* epythet.validation.docstrings.Coverage(checked=0, undocumented=0)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

How many public objects were seen and how many lack a docstring.

### *class* epythet.validation.docstrings.Docstring(file, line, def_line, qualname, kind, text, source, is_raw)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One docstring and where it came from.

#### *property* lines *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

The processed text, split into lines.

### epythet.validation.docstrings.count_public_objects(package_dir, , ignore=())

Count public modules, classes and functions, and those without a docstring.

“Public” means no leading underscore anywhere in the dotted name below the
package. Nested functions are counted like any other def.

* **Return type:**
  [`Coverage`](#epythet.validation.docstrings.Coverage)

### epythet.validation.docstrings.iter_docstrings(package_dir, , ignore=(), on_skip=None)

Yield every docstring in a package directory tree.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Docstring`](#epythet.validation.docstrings.Docstring)]

### epythet.validation.docstrings.iter_file_docstrings(path, , root=None, on_skip=None)

Yield the module, class and function docstrings of one file, in source order.

A file that does not parse or decode is skipped; `on_skip(path, reason)`
is called so the caller can report it (a syntax error is the linter’s
business, but silence would hide a docstring from the ledger).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Docstring`](#epythet.validation.docstrings.Docstring)]

### epythet.validation.docstrings.iter_python_files(package_dir, , ignore=())

Every `.py` in the package tree, skipping caches, non-package dirs and `ignore` substrings.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]
