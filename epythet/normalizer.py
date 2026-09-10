"""Build-time docstring normalizer: fix the markup artifacts people actually write.

Docstrings in the wild mix reStructuredText, Google sections and Markdown
habits. Sphinx renders the RST and napoleon handles the Google sections, but a
handful of recurring slips render wrongly, mostly *silently*: a doctest glued
to the prose above it becomes a paragraph starting with ``>>>``; a Markdown
fence is printed literally; ``Returns: text`` on one line is just a sentence;
``*args`` opens an emphasis that never closes.

This module rewrites those cases on the fly, in the ``autodoc-process-docstring``
event, so the rendered site is right without editing any source. Each rule is a
pure function ``list[str] -> list[str]`` and :data:`DEFAULT_RULES` is the
ordered tuple that runs by default. The rules only touch prose: lines inside
doctest blocks, literal blocks and directive bodies are left byte-for-byte
alone, because doctests are executed and code is code.

The rules, in order:

1. ``fences_to_code_blocks``: ```` ```lang ```` fences become ``.. code-block:: lang``.
2. ``fix_short_underlines``: a section underline shorter than its title is extended.
3. ``google_one_liners``: ``Returns: text`` becomes a real ``Returns:`` section.
4. ``bare_headers_to_rubrics``: ``Examples:`` with unindented content becomes a rubric.
5. ``markdown_headings_to_rubrics``: ``## Title`` becomes ``.. rubric:: Title``.
6. ``literal_block_after_colon``: prose ending in ``:`` followed by an indented
   block gets the ``::`` that makes it a literal block.
7. ``reflow_list_continuations``: a wrapped list or field line at the marker's
   own indentation is indented under it.
8. ``blank_lines_between_blocks``: a blank line is inserted before a doctest,
   list or field list that follows prose, and after an indented block ends.
9. ``markdown_links_to_rst``: ``[text](url)`` becomes ```text <url>`_``.
10. ``escape_unmatched_stars``: ``*args`` / ``**kwargs`` in prose are escaped.

>>> print(normalize_text('''Do the thing.
... Options are:
... - fast
... - slow
... Returns: the answer, which may
... span lines.
... '''))
Do the thing.
Options are:
<BLANKLINE>
- fast
- slow
<BLANKLINE>
Returns:
    the answer, which may
    span lines.
<BLANKLINE>
>>> normalize_docstring(["Text", "    >>> f(1)", "    3"])
['Text', '', '    >>> f(1)', '    3']
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Sequence

Rule = Callable[[list[str]], list[str]]

#: Section names napoleon recognises (Google style), lowercase.
GOOGLE_SECTIONS = frozenset(
    {
        "args", "arguments", "attention", "attributes", "caution", "danger", "error",
        "example", "examples", "hint", "important", "keyword args", "keyword arguments",
        "methods", "note", "notes", "other parameters", "parameters", "receive",
        "receives", "return", "returns", "raise", "raises", "references", "see also",
        "tip", "todo", "warning", "warnings", "warn", "warns", "yield", "yields",
    }
)  # fmt: skip

_DOCTEST_RE = re.compile(r"^\s*>>>( |$)")
_DOCTEST_CONT_RE = re.compile(r"^\s*\.\.\.( |$)")
_BULLET_RE = re.compile(r"^\s*([-*+•]|\d+[.)]|#\.)\s+\S")
_FIELD_RE = re.compile(r"^\s*:[A-Za-z_][^:]*:(\s|$)")
_DIRECTIVE_RE = re.compile(r"^\s*\.\.\s+[\w:-]+::")
_FENCE_RE = re.compile(r"^(\s*)```+\s*([\w+.-]*)\s*$")
_MD_HEADING_RE = re.compile(r"^(\s*)#{1,6}\s+(\S.*?)\s*#*\s*$")
_MD_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
_UNDERLINE_RE = re.compile(r"""^\s*([=\-~^"'*+#`:.])\1{2,}\s*$""")
_SECTION_HEADER_RE = re.compile(r"^(\s*)([A-Z][A-Za-z ]+):\s*$")
_SECTION_ONE_LINER_RE = re.compile(r"^(\s*)([A-Z][A-Za-z ]+):\s+(\S.*)$")
_LITERAL_SPAN_RE = re.compile(r"``.+?``|`[^`]+`")
_STAR_WORD_RE = re.compile(r"(?<![\w\\*])(\*\*?)(?=\w)")

BLANK, PROSE, DOCTEST, LITERAL, LIST, FIELD, FENCE = (
    "blank", "prose", "doctest", "literal", "list", "field", "fence",
)  # fmt: skip
_CODE_CONTEXTS = frozenset({DOCTEST, LITERAL, FENCE})
_PROSE_LIKE = frozenset({PROSE, LIST, FIELD})


def indent_of(line: str) -> int:
    """Number of leading spaces (tabs count as one).

    >>> indent_of("    x"), indent_of("x"), indent_of("")
    (4, 0, 0)
    """
    return len(line) - len(line.lstrip())


def line_contexts(lines: Sequence[str]) -> list[str]:
    """Classify every line as blank, prose, doctest, literal, list, field or fence.

    The classification is what keeps every rule away from code: a line inside a
    doctest block, a ``::`` literal block, a directive body or a Markdown fence
    is never rewritten.

    >>> line_contexts(["Text:", "", "    >>> 1", "    1", "", "- a", "  b", "", ":param x: y"])
    ['prose', 'blank', 'doctest', 'doctest', 'blank', 'list', 'list', 'blank', 'field']
    >>> line_contexts(["    >>> 1", "    1", "back to prose"])
    ['doctest', 'doctest', 'prose']
    """
    contexts: list[str] = []
    block: str | None = None  # doctest / list / field, reset on a blank line
    block_indent = 0  # indentation of the >>> that opened a doctest block
    literal_indent: int | None = None  # inside a :: or directive block
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if block is not None and stripped and indent_of(line) < block_indent:
            block = None  # a line shallower than the block's marker ends the block
        if in_fence:
            contexts.append(FENCE)
            if stripped.startswith("```"):
                in_fence = False
            continue
        if literal_indent is not None:
            if not stripped:
                contexts.append(BLANK)
                continue
            if indent_of(line) > literal_indent:
                contexts.append(LITERAL)
                continue
            literal_indent = None
        if not stripped:
            contexts.append(BLANK)
            block = None
            continue
        if stripped.startswith("```"):
            contexts.append(FENCE)
            in_fence = True
            block = None
            continue
        if block == DOCTEST:
            contexts.append(DOCTEST)
            continue
        if _DOCTEST_RE.match(line):
            contexts.append(DOCTEST)
            block = DOCTEST
            block_indent = indent_of(line)
            continue
        if _DIRECTIVE_RE.match(line):
            contexts.append(LITERAL)
            literal_indent = indent_of(line)
            block = None
            continue
        if _BULLET_RE.match(line):
            contexts.append(LIST)
            if block != LIST:
                block_indent = indent_of(line)
            block = LIST
            continue
        if _FIELD_RE.match(line):
            contexts.append(FIELD)
            if block != FIELD:
                block_indent = indent_of(line)
            block = FIELD
            continue
        if block in (LIST, FIELD):
            contexts.append(block)
        else:
            contexts.append(PROSE)
        if stripped.endswith("::") and not stripped.startswith(".."):
            literal_indent = indent_of(line)
    return contexts


def _is_section_header(line: str) -> bool:
    m = _SECTION_HEADER_RE.match(line)
    return bool(m) and m.group(2).lower() in GOOGLE_SECTIONS


def _next_nonblank(lines: Sequence[str], start: int) -> int | None:
    for j in range(start, len(lines)):
        if lines[j].strip():
            return j
    return None


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------


def fences_to_code_blocks(lines: list[str]) -> list[str]:
    """Turn Markdown code fences into ``.. code-block::`` directives.

    >>> normalize_text("Run:\\n```bash\\npip install x\\n```\\nDone.", rules=[fences_to_code_blocks])
    'Run:\\n\\n.. code-block:: bash\\n\\n    pip install x\\n\\nDone.'
    """
    contexts = line_contexts(lines)
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _FENCE_RE.match(lines[i])
        if not (m and contexts[i] == FENCE):
            out.append(lines[i])
            i += 1
            continue
        indent, lang = m.group(1), m.group(2) or "text"
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("```"):
            body.append(lines[j])
            j += 1
        body = _reindent(body, len(indent) + 4)
        _ensure_trailing_blank(out)
        out.append(f"{indent}.. code-block:: {lang}")
        out.append("")
        out.extend(body)
        out.append("")
        i = j + 1
    return out


def fix_short_underlines(lines: list[str]) -> list[str]:
    """Extend a title underline that is shorter than its title.

    >>> normalize_text("Examples\\n----\\ntext", rules=[fix_short_underlines])
    'Examples\\n--------\\ntext'
    """
    contexts = line_contexts(lines)
    out = list(lines)
    for i in range(1, len(lines)):
        m = _UNDERLINE_RE.match(lines[i])
        if not m or contexts[i] in _CODE_CONTEXTS:
            continue
        title = lines[i - 1]
        if not title.strip() or contexts[i - 1] != PROSE or _UNDERLINE_RE.match(title):
            continue
        if i >= 2 and lines[i - 2].strip() and not _UNDERLINE_RE.match(lines[i - 2]):
            continue  # a paragraph line, not a title
        if (
            title.rstrip().endswith((".", "!", "?", ",", ";", ":"))
            or len(lines[i].strip()) < 4
        ):
            continue  # a sentence over a Markdown rule, not a title
        width = len(title.rstrip())
        if len(lines[i].rstrip()) < width:
            out[i] = " " * indent_of(title) + m.group(1) * (width - indent_of(title))
    return out


def google_one_liners(lines: list[str]) -> list[str]:
    """Expand ``Returns: text`` (and other one-line sections) into real sections.

    Continuation lines at the same indentation are folded into the section body.

    >>> normalize_text("Returns: a thing that\\nspans two lines.\\n\\nNext.", rules=[google_one_liners])
    'Returns:\\n    a thing that\\n    spans two lines.\\n\\nNext.'
    """
    contexts = line_contexts(lines)
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _SECTION_ONE_LINER_RE.match(lines[i])
        if not (
            m and contexts[i] in _PROSE_LIKE and m.group(2).lower() in GOOGLE_SECTIONS
        ):
            out.append(lines[i])
            i += 1
            continue
        indent, header, rest = m.group(1), m.group(2), m.group(3)
        _ensure_trailing_blank(out)
        out.append(f"{indent}{header}:")
        out.append(f"{indent}    {rest}")
        j = i + 1
        while (
            j < len(lines)
            and contexts[j] in _PROSE_LIKE
            and indent_of(lines[j]) == len(indent)
            and not _SECTION_ONE_LINER_RE.match(lines[j])
            and not _is_section_header(lines[j])
        ):
            out.append(f"{indent}    {lines[j].strip()}")
            j += 1
        if j < len(lines) and lines[j].strip():
            out.append("")
        i = j
    return out


def bare_headers_to_rubrics(lines: list[str]) -> list[str]:
    """Turn a section header with no indented body into a rubric.

    napoleon only recognises ``Examples:`` when its content is indented; when
    the doctest below sits at the same indentation, the header rendered as a
    stray paragraph. A rubric is what napoleon itself emits for the section.

    >>> normalize_text("Examples:\\n\\n>>> f()\\n1", rules=[bare_headers_to_rubrics])
    '.. rubric:: Examples\\n\\n>>> f()\\n1'
    """
    contexts = line_contexts(lines)
    out = list(lines)
    for i, line in enumerate(lines):
        if contexts[i] != PROSE or not _is_section_header(line):
            continue
        j = _next_nonblank(lines, i + 1)
        if j is not None and indent_of(lines[j]) > indent_of(line):
            continue  # a proper section; napoleon handles it
        m = _SECTION_HEADER_RE.match(line)
        out[i] = f"{m.group(1)}.. rubric:: {m.group(2)}"
        if j is not None and j == i + 1:
            out[i] += "\n"  # split below into a blank line
    return _split_embedded_newlines(out)


def markdown_headings_to_rubrics(lines: list[str]) -> list[str]:
    """Render ``## Heading`` as a rubric instead of a literal ``##``.

    A ``#`` line right after code is left alone: it is most likely a comment
    that fell out of a doctest.

    >>> normalize_text("Intro.\\n## Usage\\nText.", rules=[markdown_headings_to_rubrics])
    'Intro.\\n\\n.. rubric:: Usage\\n\\nText.'
    """
    contexts = line_contexts(lines)
    out: list[str] = []
    for i, line in enumerate(lines):
        m = _MD_HEADING_RE.match(line)
        if not m or contexts[i] != PROSE or not m.group(2)[0].isalnum():
            out.append(line)
            continue
        if i > 0 and contexts[i - 1] in _CODE_CONTEXTS:
            out.append(line)
            continue
        _ensure_trailing_blank(out)
        out.append(f"{m.group(1)}.. rubric:: {m.group(2)}")
        if i + 1 < len(lines) and lines[i + 1].strip():
            out.append("")
    return out


def literal_block_after_colon(lines: list[str]) -> list[str]:
    """Make ``text:`` followed by an indented block a proper ``::`` literal block.

    >>> normalize_text("For example:\\n    x = f(1)\\nThen more.", rules=[literal_block_after_colon])
    'For example::\\n\\n    x = f(1)\\n\\nThen more.'
    """
    contexts = line_contexts(lines)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        stripped = line.rstrip()
        j = i + 1
        eligible = (
            contexts[i] == PROSE
            and stripped.endswith(":")
            and not stripped.endswith("::")
            and not _is_section_header(line)
            and not _FIELD_RE.match(line)
            and j < len(lines)
            and lines[j].strip()
            and indent_of(lines[j]) > indent_of(line)
            and contexts[j] not in (DOCTEST, LIST, FIELD)
            and not _BULLET_RE.match(lines[j])
        )
        if not eligible:
            i += 1
            continue
        out[-1] = stripped + ":"
        out.append("")
        block_indent = indent_of(line)
        while j < len(lines) and (
            not lines[j].strip() or indent_of(lines[j]) > block_indent
        ):
            out.append(lines[j])
            j += 1
        if j < len(lines) and out[-1].strip():
            out.append("")
        i = j
    return out


def blank_lines_between_blocks(lines: list[str]) -> list[str]:
    """Separate prose from the doctest, list, field list or indented block after it.

    The missing blank line before ``>>>`` is the single most common artifact in
    the fleet: without it Sphinx renders the doctest as a paragraph and
    ``sphinx.ext.doctest`` never runs it.

    >>> normalize_text("Prose\\n>>> f()\\n1", rules=[blank_lines_between_blocks])
    'Prose\\n\\n>>> f()\\n1'
    >>> normalize_text("Prose\\n:param x: y\\n    more\\n:param z: w", rules=[blank_lines_between_blocks])
    'Prose\\n\\n:param x: y\\n    more\\n:param z: w'
    >>> normalize_text("Text:\\n    indented\\nback", rules=[blank_lines_between_blocks])
    'Text:\\n    indented\\n\\nback'
    """
    contexts = line_contexts(lines)
    out: list[str] = []
    for i, line in enumerate(lines):
        if i > 0 and lines[i - 1].strip() and line.strip():
            prev_ctx, ctx = contexts[i - 1], contexts[i]
            starts_block = ctx in (DOCTEST, LIST, FIELD) and prev_ctx not in (
                ctx, DOCTEST, FENCE, LITERAL,
            )  # fmt: skip
            next_is_deeper = i + 1 < len(lines) and indent_of(lines[i + 1]) > indent_of(
                line
            )
            dedents = (
                indent_of(line) < indent_of(lines[i - 1])
                and ctx not in _CODE_CONTEXTS
                and not (ctx == prev_ctx and ctx in (LIST, FIELD))
                and not next_is_deeper  # a new definition-list term, not a return to prose
            )
            if starts_block or dedents:
                out.append("")
        out.append(line)
    return out


def markdown_links_to_rst(lines: list[str]) -> list[str]:
    """Rewrite ``[text](url)`` links as RST hyperlinks, outside code and literals.

    >>> normalize_text("See [the docs](https://x.org/a) now.", rules=[markdown_links_to_rst])
    'See `the docs <https://x.org/a>`_ now.'
    """
    contexts = line_contexts(lines)
    return [
        _outside_literal_spans(line, lambda s: _MD_LINK_RE.sub(r"`\1 <\2>`_", s))
        if ctx not in _CODE_CONTEXTS
        else line
        for line, ctx in zip(lines, contexts)
    ]


def escape_unmatched_stars(lines: list[str]) -> list[str]:
    """Escape ``*args`` and ``**kwargs`` in prose so they are not read as emphasis.

    Only a star run that is never closed on the same line is escaped, so real
    ``*emphasis*`` and ``**strong**`` are untouched.

    >>> normalize_text("Takes *args and **kwargs, *really*.", rules=[escape_unmatched_stars])
    'Takes \\\\*args and \\\\*\\\\*kwargs, *really*.'
    """
    contexts = line_contexts(lines)
    return [
        _outside_literal_spans(line, _escape_stars_in_segment)
        if ctx not in _CODE_CONTEXTS
        else line
        for line, ctx in zip(lines, contexts)
    ]


def _escape_stars_in_segment(segment: str) -> str:
    for delim in ("**", "*"):
        segment = _escape_unclosed(segment, delim)
    return segment


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _escape_unclosed(s: str, delim: str) -> str:
    """Escape each ``delim`` that opens an emphasis nobody closes on this line.

    A second opener before any closer (``*args and *really*``) means the first
    one was never meant as markup, even though docutils would pair them.
    """
    n = len(delim)

    def opens_at(i: int) -> bool:
        return (
            s.startswith(delim, i)
            and (i == 0 or (s[i - 1] not in "\\*" and not _is_word_char(s[i - 1])))
            and i + n < len(s)
            and _is_word_char(s[i + n])
        )

    def closes_at(j: int) -> bool:
        return (
            s[j - 1] != "\\"
            and not s[j - 1].isspace()
            and (j + n >= len(s) or not _is_word_char(s[j + n]))
        )

    out: list[str] = []
    i = 0
    while i < len(s):
        if not opens_at(i):
            out.append(s[i])
            i += 1
            continue
        j = s.find(delim, i + n)
        while j != -1 and not closes_at(j):
            if opens_at(j):
                j = -1
                break
            j = s.find(delim, j + n)
        if j != -1:
            out.append(s[i : j + n])
            i = j + n
        else:
            out.append("\\" + "\\".join(delim))
            i += n
    return "".join(out)


_MARKER_RE = re.compile(r"^(\s*)([-*+•]\s+|\d+[.)]\s+|#\.\s+|:[A-Za-z_][^:]*:\s*)")
_SENTENCE_END = (".", "!", "?", ":")


def reflow_list_continuations(lines: list[str]) -> list[str]:
    """Indent a wrapped list or field line that sits at the marker's own indentation.

    ``- a long item that wraps\\nonto the next line`` is not a continuation in
    RST (the list "ends without a blank line"). Indenting the wrapped line under
    the marker makes it one. A line that reads like a new sentence after a
    finished item is separated with a blank line instead.

    >>> normalize_text("- item that\\nwraps\\n- two", rules=[reflow_list_continuations])
    '- item that\\n  wraps\\n- two'
    >>> normalize_text("- item.\\nNext paragraph", rules=[reflow_list_continuations])
    '- item.\\n\\nNext paragraph'
    """
    contexts = line_contexts(lines)
    out: list[str] = []
    marker_indent = marker_width = None
    for i, line in enumerate(lines):
        ctx = contexts[i]
        m = _MARKER_RE.match(line) if ctx in (LIST, FIELD) else None
        if m:
            marker_indent, marker_width = len(m.group(1)), len(m.group(2))
            if ctx == FIELD:
                marker_width = 4
            out.append(line)
            continue
        if ctx not in (LIST, FIELD) or marker_indent is None or not line.strip():
            if not line.strip():
                marker_indent = None
            out.append(line)
            continue
        if indent_of(line) != marker_indent:
            out.append(line)
            continue
        stripped = line.strip()
        previous = out[-1].rstrip() if out else ""
        if stripped[0].isupper() and previous.endswith(_SENTENCE_END):
            out.append("")
            out.append(line)
            marker_indent = None
        else:
            out.append(" " * (marker_indent + marker_width) + stripped)
    return out


#: The rules that run by default, in order.
DEFAULT_RULES: tuple[Rule, ...] = (
    fences_to_code_blocks,
    fix_short_underlines,
    google_one_liners,
    bare_headers_to_rubrics,
    markdown_headings_to_rubrics,
    literal_block_after_colon,
    reflow_list_continuations,
    blank_lines_between_blocks,
    markdown_links_to_rst,
    escape_unmatched_stars,
)


def normalize_docstring(
    lines: Iterable[str], *, rules: Sequence[Rule] = DEFAULT_RULES
) -> list[str]:
    """Apply ``rules`` in order to a docstring given as lines (no trailing newlines).

    >>> normalize_docstring(["Text", ">>> 1", "1"])
    ['Text', '', '>>> 1', '1']
    """
    lines = list(lines)
    for rule in rules:
        lines = rule(lines)
    return lines


def normalize_text(text: str, *, rules: Sequence[Rule] = DEFAULT_RULES) -> str:
    """Apply ``rules`` to a docstring given as one string.

    >>> normalize_text("Text\\n>>> 1\\n1")
    'Text\\n\\n>>> 1\\n1'
    """
    return "\n".join(normalize_docstring(text.split("\n"), rules=rules))


def sphinx_process_docstring(app, what, name, obj, options, lines):
    """The ``autodoc-process-docstring`` handler: normalizes ``lines`` in place.

    ``options`` is deliberately never touched (its mapping interface is
    deprecated in Sphinx 9). Register with ``priority=400`` so this runs before
    napoleon (priority 500) sees the docstring.
    """
    configured = getattr(app.config, "epythet_normalizer_rules", None)
    rules = DEFAULT_RULES if configured is None else resolve_rules(configured)
    lines[:] = normalize_docstring(lines, rules=rules)


def resolve_rules(rules: Iterable) -> tuple[Rule, ...]:
    """Accept rule functions or dotted import paths (``"pkg.mod:func"`` or ``"pkg.mod.func"``).

    Dotted paths are what a ``conf.py`` can hold: Sphinx cannot pickle functions
    in its configuration, and a ledger of autofixable rules ships names.

    >>> [r.__name__ for r in resolve_rules(["epythet.normalizer.fences_to_code_blocks"])]
    ['fences_to_code_blocks']
    """
    import importlib

    resolved = []
    for rule in rules:
        if isinstance(rule, str):
            module_name, _, attr = rule.replace(":", ".").rpartition(".")
            rule = getattr(importlib.import_module(module_name), attr)
        resolved.append(rule)
    return tuple(resolved)


def setup(app):
    """Sphinx extension entry point: ``extensions = ["epythet.normalizer"]``.

    ``epythet.sphinx_ext`` registers the same hook; listing both is harmless.
    """
    from epythet.sphinx_ext import setup as _full_setup

    return _full_setup(app)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _reindent(body: list[str], indent: int) -> list[str]:
    nonblank = [l for l in body if l.strip()]
    common = min((indent_of(l) for l in nonblank), default=0)
    return [(" " * indent + l[common:]) if l.strip() else "" for l in body]


def _ensure_trailing_blank(out: list[str]) -> None:
    if out and out[-1].strip():
        out.append("")


def _split_embedded_newlines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        out.extend(line.split("\n"))
    return out


def _outside_literal_spans(line: str, transform: Callable[[str], str]) -> str:
    """Apply ``transform`` to the parts of ``line`` that are not inside backticks."""
    out: list[str] = []
    pos = 0
    for m in _LITERAL_SPAN_RE.finditer(line):
        out.append(transform(line[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(transform(line[pos:]))
    return "".join(out)
