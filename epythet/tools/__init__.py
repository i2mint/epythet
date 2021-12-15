"""Tools to diagnose (and sometimes, repair) documentation

Examples
--------

>>> repair_package(PY_FILES_DIRECTORY)  # doctest: +SKIP

If you have tec (pip install tec) installed, you can even input a module object:

>>> import epythet
>>> number_of_problems = repair_package(epythet)  # doctest: +SKIP
---> This is just a diagnosis: No files are being written to
setup_docsrc.py                           : #problems: 0
config_parser.py                          : #problems: 0
...
docs_gen.py                               : #problems: 0

As the print out header indicated, this is just a diagnosis of problems found for
each module, and returns the total number of problems.
It's advised to do this, then have a look at the problems using

>>> print_diagnosis(MODULE_PATH_OR_PKG_FOLDER)  # doctest: +SKIP

Once you're familiar with the problems, you can choose to do:

>>> repair_package(PY_FILES_DIRECTORY, write_to_files=True)  # doctest: +SKIP

This will attempt to repair the problems for you.

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

The `published_doc_diagnosis_df` gets you a pandas dataframe (requires pandas to be
installed!) that will tell you if given github ``org/repo`` url(s) have published
documentation and if a `docs` folder even exists (in master branch):

>>> from epythet.tools import published_doc_diagnosis_df  # doctest: +SKIP
>>> published_doc_diagnosis_df('https://github.com/i2mint/epythet')  # doctest: +SKIP
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
>>> published_doc_diagnosis_df([  # doctest: +SKIP
...     'https://github.com/i2mint/epythet', 'https://github.com/otosense/omisc',
... ])
                                 url                      doc_page_url  doc_page_exists  repo_has_docs_folder
0  https://github.com/i2mint/epythet  https://i2mint.github.io/epythet             True                  True
1  https://github.com/otosense/omisc  https://otosense.github.io/omisc            False                 False


"""

from contextlib import suppress

published_doc_diagnosis = None

with suppress(ImportError, ModuleNotFoundError):
    import pandas  # to raise an error if not installed, and break from with before...
    from epythet.tools.published_docs import published_doc_diagnosis_df

from epythet.tools.docstring_diagnosis import (
    Source,
    blank_line,
    beginning_of_doctest,
    tag_doctest_blocks_not_preceeded_by_new_lines_alt_2,
    binary_transition,
    tag_doctest_blocks_not_preceeded_by_new_lines,
    diagnose_doctest_code_blocks,
    diagnosis_snippets,
    print_diagnosis as docstring_print_diagnosis,
    lines_with_two_new_lines_before_doctests,
    add_newlines_before_doctests_when_missing,
    repair_package,
)


def print_diagnosis(src):
    docstring_print_diagnosis(src)
