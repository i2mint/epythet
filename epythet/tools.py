"""Tools to manipulate documentation elements

The main purpose of the module:

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

"""

import re
import os
from typing import Iterable, Union, Mapping

Source = Union[str, Iterable[str]]

blank_line = re.compile(r'\s*$').match
beginning_of_doctest = re.compile(r'\s*>>>').match


def _ensure_lines(x):
    if isinstance(x, str):
        return x.split('\n')
    return x


# Pattern: BufferStats and append_output_to_input (in lined)
def tag_doctest_blocks_not_preceeded_by_new_lines_alt_2(lines: Iterable[str]):
    """Yields (line, True/False) pairs. True when line is a >>> without newlines before,

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it. To render well through Sphinx, code blocks must be separated from earlier
    text by a blank (only spaces) line.

    This function diagnoses that.
    """


def binary_transition(transitions, state, symbol):
    """Binary state machine transition computation. Computes next state.

    :param transitions: Transition "matrix", in the form of:
        {True: state_inverting_symbols, False: state_inverting_symbols}
    :param state: Current state. True or False
    :param symbol: Incoming symbol
    :return: New state

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
    """
    if symbol in transitions[state]:  # if symbol is in the set of triggering symbols...
        return not state  # reverse the state
    else:
        return state  # else just remain in the same state


# TODO: Pattern: lined
def _filepath_to_string(filepath: str):
    with open(filepath, 'rt') as fp:
        return fp.read()


def _guess_src_kind(src):
    if isinstance(src, str):
        if os.path.isfile(src):
            return 'filepath'
        elif os.path.isdir(src):
            raise TypeError(
                f'Directories are not handled here. '
                f'Maybe you want to use print_diagnosis? --> {src=}'
            )
        else:
            # don't consider it a string if it doesn't have a newline.
            # ... it might just be a misspelled file or folderp ath
            if '\n' in src or src == '':
                return 'string'
    elif isinstance(src, Iterable):
        return 'lines'
    raise TypeError(f'Unknown src type: {src=}')


_src_trans = {
    ('filepath', 'string'): _filepath_to_string,
    ('string', 'lines'): lambda x: x.split('\n'),
    ('filepath', 'lines'): lambda x: _filepath_to_string(x).split('\n'),
}
_src_kinds = {'filepath', 'string', 'lines'}


def _get_source(src, target_kind, src_kind=None):
    src_kind = src_kind or _guess_src_kind(src)
    if target_kind == src_kind:
        return src
    else:
        assert target_kind in _src_kinds
        assert src_kind in _src_kinds
        transformer = _src_trans[src_kind, target_kind]
        return transformer(src)


# Pattern: BufferStats and append_output_to_input (in lined)
def tag_doctest_blocks_not_preceeded_by_new_lines(lines):
    """Yields (line, True/False) pairs. True when line is a >>> without newlines before,

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it. To render well through Sphinx, code blocks must be separated from earlier
    text by a blank (only spaces) line.

    This function diagnoses that.

    It uses three finite (binary) state machines.
    """

    def line_kind(line):
        if beginning_of_doctest(line):
            return 'code_start'
        elif blank_line(line):
            return 'blank_line'
        else:
            return 'normal_line'

    code_transitions = {True: {'blank_line'}, False: {'code_start'}}

    previous_normal_transitions = {
        True: {'blank_line', 'code_start'},
        False: {'normal_line'},
    }

    code, prev_normal, prev_code = False, False, False

    for line in _ensure_lines(lines):
        kind = line_kind(line)
        code = binary_transition(code_transitions, code, kind)
        yield line, code & prev_normal & ~prev_code
        prev_normal = binary_transition(previous_normal_transitions, prev_normal, kind)
        prev_code = binary_transition(code_transitions, prev_code, kind)


def diagnose_doctest_code_blocks(src: Source):
    """
    Yields lines the start code block and need attention,

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

    You would usually run `next(it)` to check on the first problem, repair, and rerun.
    (Oh, and it's important to rerun, because the line numbers won't be valid anymore
    once you edit the source code_string!).

    But, to doctest this we'll do this:

    >>> list(it)
    [(3, '    >>> like_this'), (10, '    >>> this_doctest_is_too_close_to_text')]

    """
    lines = _get_source(src, 'lines')
    for line_num, (line, needs_attention) in enumerate(
        tag_doctest_blocks_not_preceeded_by_new_lines(lines), 1
    ):
        if needs_attention:
            yield line_num, line


def diagnosis_snippets(src: Source) -> Iterable[str]:
    """Generate snippets that exhibit the problems in the src"""
    lines = _get_source(src, 'lines')
    for line_num, _ in diagnose_doctest_code_blocks(lines):
        line_idx = line_num - 1  # because line_nums start with 1, and idx with 0
        yield '\n'.join(lines[max(0, line_idx - 1) : (line_idx + 2)])


def _decode_or_default(
    b: bytes,
    dflt='# --- did not manage to decode .py file bytes --- #',
    use_cchardet=True,
):
    try:
        return b.decode()
    except UnicodeDecodeError:
        return dflt


def print_diagnosis(src: Source):
    """Print diagnosis of one or several files"""

    if isinstance(src, str) and os.path.isdir(src):
        from dol import filt_iter, wrap_kvs, KvReader
        from dol.filesys import FileBytesReader

        @wrap_kvs(obj_of_data=_decode_or_default)
        @filt_iter(filt=lambda k: k.endswith('.py') and '__pycache__' not in k)
        class PyFilesReader(FileBytesReader, KvReader):
            ...

        src = PyFilesReader(src)

    if isinstance(src, Mapping):
        for k, string_contents in src.items():
            snippets = list(diagnosis_snippets(string_contents))
            if snippets:
                print(
                    f'----------- {k} -----------', '\n', '\n'.join(snippets), '\n\n',
                )
    else:
        print('\n'.join(diagnosis_snippets(src)))


def lines_with_two_new_lines_before_doctests(lines: Iterable[str]):
    r"""Yields the input lines, but interleaving an empty ('') line if a code block
    starts with out an empty line preceeding it

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it.
    """
    for line, needs_attention in tag_doctest_blocks_not_preceeded_by_new_lines(lines):
        if needs_attention:
            yield ''
            yield line
        else:
            yield line


def add_newlines_before_doctests_when_missing(src: str):
    r"""Returns the code_string with newlines inserted before code blocks when missing./

    A code block is defined by a line that starts with `>>>` (except for optional spaces
    before it.

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


    """
    lines = _get_source(src, 'lines')
    return '\n'.join(lines_with_two_new_lines_before_doctests(lines))


def repair_package(pkg, write_to_files=False):
    """Diagnose and/or repair a whole pkg (given by folder or pkg module obj,
    or a store (see dol).

    For now, it diagnosis and repairs:
    - When there's a space missing between doc text and doctest (code block)
    """

    if not isinstance(pkg, Mapping):
        # If pkg is not already a store
        from dol.filesys import RelPathFileStringPersister

        if isinstance(pkg, str) and os.path.isdir(pkg):
            reader = RelPathFileStringPersister(pkg)
        else:
            # try a more flexible store
            from tec import PyFilesReader

            reader = PyFilesReader(pkg)

        writer = RelPathFileStringPersister(reader.rootdir)
    else:
        reader = pkg
        writer = pkg

    if not write_to_files:
        print('---> This is just a diagnosis: No files are being written to')

    num_of_problems = 0

    for k, v in reader.items():
        problems = list(diagnose_doctest_code_blocks(v))
        num_of_problems += len(problems)
        print(f'{k:<42s}: #problems: {len(problems)}')
        if problems and write_to_files:
            writer[k] = add_newlines_before_doctests_when_missing(reader[k])

    return num_of_problems
