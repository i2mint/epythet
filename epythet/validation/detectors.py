"""Named doctree detectors, referenced from ledger rules by ``detector.function``.

Each detector takes a :class:`~epythet.validation.parse.ParsedDocstring` and
returns a list of evidence strings, one per hit (an empty list means the rule
does not fire). They read the docutils doctree rather than rendered HTML so
that the rules keep working under any Sphinx theme, and under a MkDocs
backend, exactly as decided in D8.

The detectors are the measured prototype from the validation research
(``detect2.py`` and ``refine.py``), ported one to one; the refinements that
took false positives from 2/14 to 1/14 on the control set are marked inline.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

import docutils.nodes as N

if TYPE_CHECKING:  # pragma: no cover
    from epythet.validation.parse import ParsedDocstring

Detector = Callable[["ParsedDocstring"], list[str]]

#: Registry filled by :func:`detector`; the ledger loader validates against it.
DETECTORS: dict[str, Detector] = {}

#: Section names napoleon recognises (Google style), lower-cased.
NAPOLEON_SECTIONS = frozenset(
    """args arguments attention attributes caution danger error example examples
    hint important methods note notes parameters receive receives return returns
    raise raises references tip todo warning warnings warns yield yields""".split()
) | {"keyword args", "keyword arguments", "other parameters", "see also"}

#: Common misspellings / near-misses of section names that napoleon ignores.
NEAR_SECTIONS = frozenset(
    {
        "arg",
        "argument",
        "param",
        "params",
        "parameter",
        "attribute",
        "kwarg",
        "kwargs",
        "exception",
        "exceptions",
        "returnss",
        "retruns",
        "yeilds",
        "rasies",
        "exemple",
        "exemples",
        "usage",
        "input",
        "inputs",
        "output",
        "outputs",
    }
)

DIRECTIVE_RE = re.compile(r"^\s*\.\.\s+([a-zA-Z][\w-]*)::", re.M)


def detector(name: str) -> Callable[[Detector], Detector]:
    """Register a detector under ``name`` (the name used in rule YAML)."""

    def register(fn: Detector) -> Detector:
        DETECTORS[name] = fn
        return fn

    return register


def _has(tree: N.Node, *node_types: type) -> bool:
    return any(True for _ in tree.findall(lambda n: isinstance(n, node_types)))


def _short(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


@detector("problematic_nodes")
def problematic_nodes(parsed: "ParsedDocstring") -> list[str]:
    """Unbalanced inline markup: every ``problematic`` node in the tree (DR010)."""
    return [_short(node.astext()) for node in parsed.tree.findall(N.problematic)]


@detector("title_references")
def title_references(parsed: "ParsedDocstring") -> list[str]:
    """Single backticks parsed as a title reference, i.e. italics not code (DR011)."""
    return [_short(node.astext()) for node in parsed.tree.findall(N.title_reference)]


def _definition_terms(parsed: "ParsedDocstring"):
    for dl in parsed.tree.findall(N.definition_list):
        for term in dl.findall(N.term):
            text = term.astext().strip()
            yield dl, term, text, text.rstrip(":").strip()


@detector("section_as_definition_list")
def section_as_definition_list(parsed: "ParsedDocstring") -> list[str]:
    """A Google section (``Args:``) became a definition-list term: napoleon is off (DR012)."""
    return [
        base
        for _, _, _, base in _definition_terms(parsed)
        if base.lower() in NAPOLEON_SECTIONS
    ]


@detector("near_miss_section_term")
def near_miss_section_term(parsed: "ParsedDocstring") -> list[str]:
    """A definition-list term that is a misspelt section name (DR013)."""
    return [
        base
        for _, _, _, base in _definition_terms(parsed)
        if base.lower() in NEAR_SECTIONS and base.lower() not in NAPOLEON_SECTIONS
    ]


@detector("prose_definition_term")
def prose_definition_term(parsed: "ParsedDocstring") -> list[str]:
    """A definition-list term of three or more words: prose eaten by indentation (DR014)."""
    return [
        _short(text)
        for _, _, text, base in _definition_terms(parsed)
        if len(base.split()) >= 3 and base.lower() not in NAPOLEON_SECTIONS
    ]


@detector("param_definition_list")
def param_definition_list(parsed: "ParsedDocstring") -> list[str]:
    """A top-level definition list of single-word terms: probably a parameter list (DR017)."""
    hits = []
    for dl, _, _, base in _definition_terms(parsed):
        if (
            dl.parent is parsed.tree
            and re.fullmatch(r"\w+", base)
            and base.lower() not in NAPOLEON_SECTIONS
        ):
            hits.append(base)
    return hits


@detector("system_messages")
def system_messages(parsed: "ParsedDocstring") -> list[str]:
    """Every message docutils reported while parsing the docstring (DR032)."""
    return [_short(m, 120) for m in parsed.messages]


@detector("blockquote_with_unexpected_indent")
def blockquote_with_unexpected_indent(parsed: "ParsedDocstring") -> list[str]:
    """A block quote *and* an ``Unexpected indentation`` message: stray indent (DR016).

    The message gate is what makes this reliable; a block quote alone is how a
    legitimate quotation is written (research §3.3).
    """
    if not _has(parsed.tree, N.block_quote):
        return []
    if not any("Unexpected indentation" in m for m in parsed.messages):
        return []
    return [_short(bq.astext()) for bq in parsed.tree.findall(N.block_quote)][:1]


@detector("markdown_fence_literal")
def markdown_fence_literal(parsed: "ParsedDocstring") -> list[str]:
    """A Markdown fence collapsed into an inline literal (DR006).

    Refinement from the research: a ``` fence parses as an inline ``literal``
    whose text starts or ends with a backtick, because the fence characters
    are consumed as the literal's delimiters. Testing for three backticks in
    the paragraph text does not work.
    """
    hits = [
        _short(lit.astext())
        for lit in parsed.tree.findall(N.literal)
        if lit.astext().startswith("`") or lit.astext().endswith("`")
    ]
    if hits:
        return hits
    return [
        m.group(0).strip() for m in re.finditer(r"(?m)^\s*(```|~~~)\w*", parsed.text)
    ][:1]


def _outside_system_messages(tree: N.Node, *node_types: type):
    """Nodes of the given types that are not inside a ``system_message``."""
    for node in tree.findall(lambda n: isinstance(n, node_types)):
        parent = node.parent
        while parent is not None and not isinstance(parent, N.system_message):
            parent = parent.parent
        if parent is None:
            yield node


@detector("directive_content_lost")
def directive_content_lost(parsed: "ParsedDocstring") -> list[str]:
    """A directive is written in the source but produced no content node (DR018).

    With stub directives registered, an unknown directive name (``.. codeblock::``)
    or a body that docutils rejected leaves only a system message behind; the
    content the author wrote is gone from the page.
    """
    names = [m.group(1) for m in DIRECTIVE_RE.finditer(parsed.text)]
    if not names:
        return []
    lost = [
        _short(m, 120)
        for m in parsed.messages
        if "Unknown directive type" in m or 'Error in "' in m
    ]
    if lost:
        return lost
    content_types = (
        N.literal_block,
        N.table,
        N.image,
        N.Admonition,
        N.rubric,
        N.math_block,
        N.figure,
        N.comment,
        N.container,
        N.compound,
    )
    if any(True for _ in _outside_system_messages(parsed.tree, *content_types)):
        return []
    return [f".. {name}::" for name in names]


@detector("collapsed_table")
def collapsed_table(parsed: "ParsedDocstring") -> list[str]:
    """A simple-table border in the source with no ``table`` node in the tree (DR019).

    Refinement from the research: the border line must contain two or more
    whitespace-separated runs of ``=``, otherwise a section underline matches.
    """
    if _has(parsed.tree, N.table):
        return []
    for line in parsed.text.splitlines():
        stripped = line.strip()
        if stripped and set(stripped) <= set("= "):
            runs = [run for run in stripped.split(" ") if run]
            if len(runs) >= 2:
                return [stripped]
    return []


@detector("mixed_bullet_markers")
def mixed_bullet_markers(parsed: "ParsedDocstring") -> list[str]:
    """Two adjacent sibling bullet lists: the marker character changed mid-list (DR022)."""
    hits = []
    for bullet_list in parsed.tree.findall(N.bullet_list):
        parent = bullet_list.parent
        if parent is None:
            continue
        following = parent[parent.index(bullet_list) + 1 :]
        # docutils puts its "unexpected unindent" message between the two lists.
        following = [n for n in following if not isinstance(n, N.system_message)]
        if following and isinstance(following[0], N.bullet_list):
            first = bullet_list.get("bullet", "?")
            second = following[0].get("bullet", "?")
            hits.append(f"'{first}' list followed by '{second}' list")
    return hits
