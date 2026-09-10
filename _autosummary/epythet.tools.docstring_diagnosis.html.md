# epythet.tools.docstring_diagnosis

Tools to manipulate documentation elements

The main purpose of the module:

```pycon
>>> repair_package(PY_FILES_DIRECTORY)
```

If you have tec (pip install tec) installed, you can even input a module object:

```pycon
>>> import epythet
>>> number_of_problems = repair_package(epythet)
---> This is just a diagnosis: No files are being written to
setup_docsrc.py                           : #problems: 0
config_parser.py                          : #problems: 0
...
docs_gen.py                               : #problems: 0
```

As the print out header indicated, this is just a diagnosis of problems found for
each module, and returns the total number of problems.
It’s advised to do this, then have a look at the problems using

```pycon
>>> print_diagnosis(MODULE_PATH_OR_PKG_FOLDER)
```

Once you’re familiar with the problems, you can choose to do:

```pycon
>>> repair_package(PY_FILES_DIRECTORY, write_to_files=True)
```

This will attempt to repair the problems for you.

```pycon
>>> docs = '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''
>>>
>>>
>>> new_docs = add_newlines_before_doctests_when_missing(docs)
>>> assert new_docs == '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''
```

### Functions

| [`add_newlines_before_doctests_when_missing`](#epythet.tools.docstring_diagnosis.add_newlines_before_doctests_when_missing)(src)             | Returns the code_string with newlines inserted before code blocks when missing./                                        |
|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`binary_transition`](#epythet.tools.docstring_diagnosis.binary_transition)(transitions, state, symbol)              | Binary state machine transition computation.                                                                            |
| [`diagnose_doctest_code_blocks`](#epythet.tools.docstring_diagnosis.diagnose_doctest_code_blocks)(src)                          | Yields lines the start code block and need attention,                                                                   |
| [`diagnosis_snippets`](#epythet.tools.docstring_diagnosis.diagnosis_snippets)(src)                                    | Generate snippets that exhibit the problems in the src                                                                  |
| [`lines_with_two_new_lines_before_doctests`](#epythet.tools.docstring_diagnosis.lines_with_two_new_lines_before_doctests)(lines)            | Yields the input lines, but interleaving an empty ('') line if a code block starts with out an empty line preceeding it |
| [`print_diagnosis`](#epythet.tools.docstring_diagnosis.print_diagnosis)(src)                                       | Print diagnosis of one or several files                                                                                 |
| [`repair_package`](#epythet.tools.docstring_diagnosis.repair_package)(pkg[, write_to_files])                      | Diagnose and/or repair a whole pkg (given by folder or pkg module obj, or a store (see dol).                            |
| [`tag_doctest_blocks_not_preceeded_by_new_lines`](#epythet.tools.docstring_diagnosis.tag_doctest_blocks_not_preceeded_by_new_lines)(lines)       | Yields (line, True/False) pairs.                                                                                        |
| [`tag_doctest_blocks_not_preceeded_by_new_lines_alt_2`](#epythet.tools.docstring_diagnosis.tag_doctest_blocks_not_preceeded_by_new_lines_alt_2)(lines) | Yields (line, True/False) pairs.                                                                                        |

### epythet.tools.docstring_diagnosis.add_newlines_before_doctests_when_missing(src)

Returns the code_string with newlines inserted before code blocks when missing./

A code block is defined by a line that starts with `>>>` (except for optional spaces
before it.

```pycon
>>> docs = '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''
>>>
>>>
>>> new_docs = add_newlines_before_doctests_when_missing(docs)
>>> assert new_docs == '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''
```

### epythet.tools.docstring_diagnosis.beginning_of_doctest(string, pos=0, endpos=9223372036854775807)

Matches zero or more characters at the beginning of the string.

### epythet.tools.docstring_diagnosis.binary_transition(transitions, state, symbol)

Binary state machine transition computation. Computes next state.

* **Parameters:**
  * **transitions** – Transition “matrix”, in the form of:
    {True: state_inverting_symbols, False: state_inverting_symbols}
  * **state** – Current state. True or False
  * **symbol** – Incoming symbol
* **Returns:**
  New state

```pycon
>>> transitions = {False: {1, 2}, True: {3}}
>>> binary_transition(transitions, False, 3)
False
>>> binary_transition(transitions, False, 1)
True
>>> binary_transition(transitions, True, 1)
True
>>> binary_transition(transitions, True, 2)
True
>>> binary_transition(transitions, True, 3)
False
```

### epythet.tools.docstring_diagnosis.blank_line(string, pos=0, endpos=9223372036854775807)

Matches zero or more characters at the beginning of the string.

### epythet.tools.docstring_diagnosis.diagnose_doctest_code_blocks(src)

Yields lines the start code block and need attention,

```pycon
>>> docs = '''
... The doctest won't render correctly if it's not preceeded by a blank line:
...     >>> like_this
...
... But with a blank line before a block of doctests, it's fine
...
... >>> okay
...
...     Is also detected in indentations
...     >>> this_doctest_is_too_close_to_text
...     SOME_OUTPUT
...     >>> but_this_is_fine
...     since it's within a doctest block
...
... '''
>>> it = diagnose_doctest_code_blocks(docs)
```

You would usually run `next(it)` to check on the first problem, repair, and rerun.
(Oh, and it’s important to rerun, because the line numbers won’t be valid anymore
once you edit the source code_string!).

But, to doctest this we’ll do this:

```pycon
>>> list(it)
[(3, '    >>> like_this'), (10, '    >>> this_doctest_is_too_close_to_text')]
```

### epythet.tools.docstring_diagnosis.diagnosis_snippets(src)

Generate snippets that exhibit the problems in the src

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.tools.docstring_diagnosis.lines_with_two_new_lines_before_doctests(lines)

Yields the input lines, but interleaving an empty (‘’) line if a code block
starts with out an empty line preceeding it

A code block is defined by a line that starts with `>>>` (except for optional spaces
before it.

### epythet.tools.docstring_diagnosis.print_diagnosis(src)

Print diagnosis of one or several files

### epythet.tools.docstring_diagnosis.repair_package(pkg, write_to_files=False)

Diagnose and/or repair a whole pkg (given by folder or pkg module obj,
or a store (see dol).

A folder or package object is handed to [`epythet.repair.repair()`](epythet.repair.html.md#epythet.repair.repair),
which applies every source-safe normalizer rule (blank lines before
doctests and lists, Markdown fences, one-line `Returns:` sections,
Markdown headings and links) and verifies each rewrite; a store (a
`dol` mapping) keeps the original doctest-only pass, which is the only
one that can write through an arbitrary mapping.

Prints one line per file with the number of docstrings that changed (or
would change) and returns the total, exactly as it always has; wads’
`wads-docstring-render` skill depends on that shape.

### epythet.tools.docstring_diagnosis.tag_doctest_blocks_not_preceeded_by_new_lines(lines)

Yields (line, True/False) pairs. True when line is a >>> without newlines before,

A code block is defined by a line that starts with `>>>` (except for optional spaces
before it. To render well through Sphinx, code blocks must be separated from earlier
text by a blank (only spaces) line.

This function diagnoses that.

It uses three finite (binary) state machines.

### epythet.tools.docstring_diagnosis.tag_doctest_blocks_not_preceeded_by_new_lines_alt_2(lines)

Yields (line, True/False) pairs. True when line is a >>> without newlines before,

A code block is defined by a line that starts with `>>>` (except for optional spaces
before it. To render well through Sphinx, code blocks must be separated from earlier
text by a blank (only spaces) line.

This function diagnoses that.
