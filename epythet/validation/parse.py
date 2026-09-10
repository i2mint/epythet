"""Level 0.5: parse each docstring's docutils doctree and run the ledger's detectors.

This is the load-bearing level of ``epythet validate``: the research measured
that a strict ``sphinx-build -W -n`` is silent on 12 of 21 artifact classes,
while the doctree of the docstring, parsed in isolation, exposes 20 of them at
about a thousand docstrings per second and without a build.

Two things make a naive implementation fail and are handled here:

- plain docutils knows nothing of ``:func:``, ``.. versionadded::`` and the
  rest of Sphinx's vocabulary, so stub roles and directives are registered
  first (otherwise nearly every correct Sphinx docstring is flagged);
- with ``sphinx.ext.napoleon`` enabled fleet-wide, Google sections are
  rewritten before docutils sees them, so the same transform is applied here
  (``napoleon=True``) and rules can opt out via ``applies_to.napoleon``.

``file_insertion_enabled`` and ``raw_enabled`` are off so that a docstring can
never make the validator read a file or inject raw HTML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator

import docutils.nodes as N
from docutils import frontend
from docutils.core import publish_doctree
from docutils.parsers.rst import Directive, directives, roles

from epythet.validation.detectors import DETECTORS
from epythet.validation.docstrings import Docstring
from epythet.validation.ledger import PARSE_KINDS, Ledger, Rule
from epythet.validation.model import Finding

PARSE_LEVEL = 0.5

SPHINX_ROLES = """any attr class const data exc func kbd meth mod obj term ref doc download
numref envvar option program samp file guilabel menuselection abbr command dfn
math eq py:func py:class py:meth py:mod py:obj py:attr py:data py:exc py:const
c:func cpp:class rst:dir rst:role token regexp pep rfc keyword manpage
c:type c:member c:macro js:func js:class""".split()

SPHINX_DIRECTIVES = """autoclass autofunction automodule automethod autoattribute autodata
autoexception currentmodule module function class method attribute data property
exception versionadded versionchanged deprecated versionremoved seealso
code-block literalinclude toctree index only tabs tab-set tab-item card grid
mermaid autosummary glossary productionlist rubric centered hlist todo
plot ipython jupyter-execute nbinput nboutput doctest testcode testoutput
testsetup highlight sourcecode deprecated-removed collapse dropdown""".split()


class _StubDirective(Directive):
    """Accepts any arguments/options and renders its body as a literal block."""

    has_content = True
    required_arguments = 0
    optional_arguments = 99
    final_argument_whitespace = True
    option_spec: dict = {}

    def run(self):
        return [N.literal_block("", "\n".join(self.content))]


class _OneArgumentStub(_StubDirective):
    """A stub with the real directive's argument count, so a missing blank line
    after ``.. code-block:: python`` is still an error (research DR018 specimen)."""

    optional_arguments = 1
    final_argument_whitespace = False


#: Directives whose real implementation takes at most one argument.
ONE_ARGUMENT_DIRECTIVES = frozenset(
    {"code-block", "code", "sourcecode", "literalinclude", "math"}
)


def _stub_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    return [N.literal(rawtext, text)], []


_STUBS_INSTALLED = False


def install_stubs() -> None:
    """Register stub Sphinx roles and directives with docutils (idempotent)."""
    global _STUBS_INSTALLED
    if _STUBS_INSTALLED:
        return
    for role in SPHINX_ROLES:
        roles.register_local_role(role, _stub_role)
    for name in SPHINX_DIRECTIVES:
        stub = _OneArgumentStub if name in ONE_ARGUMENT_DIRECTIVES else _StubDirective
        directives.register_directive(name, stub)
    _STUBS_INSTALLED = True


class _MessageSink:
    """A ``warning_stream`` that keeps every docutils message as one string."""

    def __init__(self):
        self.messages: list[str] = []

    def write(self, text: str) -> None:
        text = text.strip()
        if text:
            self.messages.append(text)

    def flush(self) -> None:
        pass


_SETTINGS = dict(
    report_level=2,
    halt_level=5,
    file_insertion_enabled=False,
    raw_enabled=False,
    _disable_config=True,
    docinfo_xform=False,
    smart_quotes=False,
)


def parse_rst(text: str) -> tuple[N.document, list[str]]:
    """Parse RST text into a doctree, returning it with the docutils messages."""
    install_stubs()
    sink = _MessageSink()
    tree = publish_doctree(
        text, settings_overrides={**_SETTINGS, "warning_stream": sink}
    )
    return tree, sink.messages


def napoleon_transform(text: str) -> str:
    """Rewrite Google/NumPy sections into RST fields the way ``sphinx.ext.napoleon`` does.

    Returns ``text`` unchanged when Sphinx is not importable; the caller records
    a note in that case.
    """
    try:
        from sphinx.ext.napoleon import Config
        from sphinx.ext.napoleon.docstring import GoogleDocstring, NumpyDocstring
    except ImportError:
        return text
    config = Config(napoleon_use_param=True, napoleon_use_rtype=True)
    return str(NumpyDocstring(str(GoogleDocstring(text, config)), config))


def sphinx_available() -> bool:
    """Whether ``sphinx.ext.napoleon`` can be imported."""
    try:
        import sphinx.ext.napoleon  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class ParsedDocstring:
    """One docstring, its (possibly napoleon-transformed) text, doctree and messages."""

    docstring: Docstring
    text: str
    tree: N.document
    messages: list[str]
    _paragraphs: list[str] | None = field(default=None, repr=False)
    _literals: list[str] | None = field(default=None, repr=False)

    @property
    def paragraphs(self) -> list[str]:
        """Prose of every paragraph not inside a system message.

        Text inside inline ``literal`` nodes is left out, so a field marker
        quoted as code (double backticks around ``:param x:``) never trips a
        prose regex.
        """
        if self._paragraphs is None:
            self._paragraphs = [
                _prose_text(p)
                for p in self.tree.findall(N.paragraph)
                if not isinstance(p.parent, N.system_message)
            ]
        return self._paragraphs

    @property
    def literals(self) -> list[str]:
        """Text of every inline literal."""
        if self._literals is None:
            self._literals = [lit.astext() for lit in self.tree.findall(N.literal)]
        return self._literals

    def texts_for(self, node: str) -> list[str]:
        """The text corpus a ``regex`` detector scans: ``paragraph``, ``literal`` or ``any``."""
        if node == "paragraph":
            return self.paragraphs
        if node == "literal":
            return self.literals
        return self.paragraphs + self.literals


def _prose_text(paragraph: N.paragraph) -> str:
    """The paragraph's text with inline literals blanked out."""
    parts = []
    for node in paragraph.findall(N.Text):
        parent = node.parent
        while parent is not None and parent is not paragraph:
            if isinstance(parent, (N.literal, N.literal_block, N.raw)):
                break
            parent = parent.parent
        else:
            parts.append(node.astext())
    return "".join(parts)


DOCTEST_LINE_RE = re.compile(r"^\s*(>>>|\.\.\.)(\s|$)")


def parse_docstring(docstring: Docstring, *, napoleon: bool = True) -> ParsedDocstring:
    """Parse one docstring (after the optional napoleon transform)."""
    text = napoleon_transform(docstring.text) if napoleon else docstring.text
    tree, messages = parse_rst(text)
    return ParsedDocstring(docstring=docstring, text=text, tree=tree, messages=messages)


def _regex_hits(rule: Rule, parsed: ParsedDocstring) -> list[str]:
    pattern = rule.pattern
    node = rule.detector.get("node", "paragraph")
    return [
        m.group(0) for text in parsed.texts_for(node) for m in pattern.finditer(text)
    ]


def _source_hits(rule: Rule, parsed: ParsedDocstring) -> list[str]:
    detector = rule.detector
    if detector.get("requires_non_raw") and parsed.docstring.is_raw:
        return []
    corpus = (
        parsed.docstring.source
        if detector.get("scan") == "literal"
        else parsed.docstring.text
    )
    lines = corpus.splitlines()
    if detector.get("skip_doctest_lines"):
        lines = [line for line in lines if not DOCTEST_LINE_RE.match(line)]
    pattern = rule.pattern
    if detector.get("whole_text"):
        return [m.group(0) for m in pattern.finditer("\n".join(lines))]
    return [m.group(0) for line in lines for m in pattern.finditer(line)]


def evaluate_rule(rule: Rule, parsed: ParsedDocstring) -> list[str]:
    """Run one parse-level rule over one parsed docstring; returns the evidence list."""
    if rule.kind == "regex":
        return _regex_hits(rule, parsed)
    if rule.kind == "source":
        return _source_hits(rule, parsed)
    if rule.kind == "doctree":
        return DETECTORS[rule.detector["function"]](parsed)
    raise ValueError(f"{rule.id}: kind {rule.kind!r} is not a parse-level detector")


def findings_for(
    parsed: ParsedDocstring, rules: Iterable[Rule], *, level: float = PARSE_LEVEL
) -> Iterator[Finding]:
    """One finding per (docstring, rule) that fired, carrying the first hit and the count.

    A rule whose detector declares ``only_if_no_other_hits: true`` (the
    catch-all DR032) is evaluated last and reported only when nothing more
    specific fired on the same docstring, so a docutils message never appears
    twice under two rule ids.
    """
    doc = parsed.docstring
    rules = sorted(rules, key=lambda r: bool(r.detector.get("only_if_no_other_hits")))
    fired = False
    for rule in rules:
        if rule.detector.get("only_if_no_other_hits") and fired:
            continue
        hits = evaluate_rule(rule, parsed)
        if not hits:
            continue
        fired = True
        evidence = hits[0]
        message = rule.format_message(evidence)
        if len(hits) > 1:
            message += f" ({len(hits)} occurrences)"
        yield rule.finding(
            level=level,
            evidence=evidence,
            file=doc.file,
            line=doc.line,
            object=doc.qualname,
            message=message,
        )


def run_parse_level(
    docstrings: Iterable[Docstring], ledger: Ledger, *, napoleon: bool = True
) -> list[Finding]:
    """Level 0.5 over a stream of docstrings."""
    rules = [r for r in ledger.of_kind(*PARSE_KINDS) if r.applies(napoleon=napoleon)]
    findings: list[Finding] = []
    for docstring in docstrings:
        parsed = parse_docstring(docstring, napoleon=napoleon)
        findings.extend(findings_for(parsed, rules))
    return findings
