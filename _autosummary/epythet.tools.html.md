# epythet.tools

Tools to diagnose (and sometimes, repair) documentation

### Examples

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

The `published_doc_diagnosis_df` gets you a pandas dataframe (requires pandas to be
installed!) that will tell you if given github `org/repo` url(s) have published
documentation and if a `docs` folder even exists (in master branch):

```pycon
>>> from epythet.tools import published_doc_diagnosis_df
>>> published_doc_diagnosis_df('https://github.com/i2mint/epythet')
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
>>> published_doc_diagnosis_df([
...     'https://github.com/i2mint/epythet', 'https://github.com/myorg/myrepo',
... ])
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
1    https://github.com/myorg/myrepo    https://myorg.github.io/myrepo            False                 False
```

### Functions

| `print_diagnosis`(src)   |    |
|--------------------------|----|

### epythet.tools.beginning_of_doctest(string, pos=0, endpos=9223372036854775807)

Matches zero or more characters at the beginning of the string.

### epythet.tools.blank_line(string, pos=0, endpos=9223372036854775807)

Matches zero or more characters at the beginning of the string.

### Modules

| [`docstring_diagnosis`](epythet.tools.docstring_diagnosis.html.md#module-epythet.tools.docstring_diagnosis)   | Tools to manipulate documentation elements                                          |
|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`published_docs`](epythet.tools.published_docs.html.md#module-epythet.tools.published_docs)             | Elements for a tool to setup docs and check if docs are published, and if not, why. |
