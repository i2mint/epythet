"""Level 0 coverage and quality smells: the queue signals, computed from the ``ast`` alone.

The doc-quality research (``research_doc_quality.md`` §2, §6) defines what
the fleet sweep should *queue*, as opposed to gate: a public callable with
no docstring, an entry point with no runnable example, a summary that only
restates the name, a parameter description that only restates the type, a
summary written as meta-language ("This function..."). None of these needs
ruff or pydoclint, so the sweep can run them on a checkout that has neither;
none of them changes the exit code unless ``--fail-on info`` asks for it.

The public surface follows the R1 decision: ``__all__`` is honoured where
present, otherwise every non-underscore name; *entry points* are the names
the package's ``__init__`` binds (its ``__all__``, else what it defines and
imports), and only those owe an example.

Each detector is a function ``PublicObject -> list[str]`` registered under
the name a ``coverage``-kind ledger rule refers to. The two text heuristics
are the research's, verbatim:

- trivial summary: split the identifier on ``snake_case``/``camelCase``,
  split the summary on whitespace, strip stop words, crude lemmatisation;
  flag when the summary's content words are a subset of the name's;
- type restatement: flag a parameter description whose content words are a
  subset of the annotation's tokens (``n: int`` described as "an integer").

>>> trivial_summary_words("load_config", "Load the config.")
True
>>> trivial_summary_words("load_config", "Read pyproject.toml and setup.cfg into a DocsConfig.")
False
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator

from epythet.validation.docstrings import _docstring_node, _iter_defs, iter_python_files
from epythet.validation.ledger import Ledger, Rule
from epythet.validation.model import Finding

COVERAGE_LEVEL = 0

STOP_WORDS = frozenset(
    """a an the of to and or for in on at by with from into as is are be this that
    it its if then else when than which who whom whose get set return returns
    given""".split()
)
#: Crude lemmatisation: strip these suffixes from a word before comparing.
_SUFFIXES = ("ing", "ies", "es", "ed", "s")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_DOCTEST_RE = re.compile(r"^\s*>>>", re.M)
META_LANGUAGE_RE = re.compile(
    r"^\s*(?:this|the)\s+(?:function|method|class|module|helper|routine|decorator|generator|property)\b"
    r"|^\s*(?:a|an)\s+(?:function|method|class|helper|routine|decorator)\s+(?:that|which|to|for)\b"
    r"|^\s*(?:function|method|helper|routine|class)\s+(?:that|which|to|for)\b",
    re.IGNORECASE,
)
#: Annotation tokens that are read as a type word in a description.
_TYPE_SYNONYMS = {
    "int": {"int", "integer"},
    "str": {"str", "string"},
    "bool": {"bool", "boolean", "flag"},
    "float": {"float", "number"},
    "list": {"list"},
    "dict": {"dict", "dictionary", "mapping"},
    "tuple": {"tuple"},
    "set": {"set"},
    "callable": {"callable", "function"},
    "iterable": {"iterable"},
    "path": {"path"},
    "none": {"none"},
    "any": {"any"},
    "object": {"object"},
}


@dataclass
class Param:
    """A signature parameter and, if the docstring describes it, that description."""

    name: str
    annotation: str | None = None
    description: str | None = None


@dataclass
class PublicObject:
    """One public module, class or function, with what a detector needs to judge it."""

    qualname: str
    kind: str  # module | class | function
    file: str
    line: int
    docstring: str | None
    params: list[Param] = field(default_factory=list)
    is_entry_point: bool = False
    name: str = ""

    @property
    def summary(self) -> str:
        """The first non-blank line of the docstring, or ``""``."""
        if not self.docstring:
            return ""
        for line in self.docstring.strip().splitlines():
            if line.strip():
                return line.strip()
        return ""

    @property
    def has_example(self) -> bool:
        return bool(self.docstring) and bool(_DOCTEST_RE.search(self.docstring))


CoverageDetector = Callable[[PublicObject], list[str]]
COVERAGE_DETECTORS: dict[str, CoverageDetector] = {}


def coverage_detector(name: str):
    """Register a coverage detector under the name a rule's ``detector.function`` uses."""

    def register(fn: CoverageDetector) -> CoverageDetector:
        COVERAGE_DETECTORS[name] = fn
        return fn

    return register


# --------------------------------------------------------------------------
# Words
# --------------------------------------------------------------------------


def _lemma(word: str) -> str:
    """Strip plural and verb suffixes to a fixed point, so both sides of a comparison agree.

    >>> _lemma("strings"), _lemma("string"), _lemma("classes"), _lemma("loaded")
    ('str', 'str', 'cla', 'load')
    """
    word = word.lower()
    while True:
        for suffix in _SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        else:
            return word


def name_words(identifier: str) -> set[str]:
    """Content words of an identifier: ``load_config`` -> ``{"load", "config"}``.

    >>> sorted(name_words("DocsConfig")), sorted(name_words("mk_parser"))
    (['config', 'doc'], ['mk', 'parser'])
    """
    parts = []
    for chunk in identifier.replace("_", " ").split():
        parts += _CAMEL_RE.split(chunk)
    return {_lemma(p) for p in parts if p and p.lower() not in STOP_WORDS}


def content_words(text: str) -> set[str]:
    """Content words of prose: lower-cased, stop words out, crudely lemmatised."""
    return {_lemma(w) for w in _WORD_RE.findall(text) if w.lower() not in STOP_WORDS}


def trivial_summary_words(identifier: str, summary: str) -> bool:
    """Whether the summary's content words are all in the identifier's (the *lazy* smell)."""
    words = content_words(summary)
    return bool(words) and words <= name_words(identifier)


def annotation_words(annotation: str) -> set[str]:
    """Words a reader could use to restate an annotation: ``list[int]`` -> int, list, integer..."""
    words: set[str] = set()
    for token in _WORD_RE.findall(annotation):
        lowered = token.lower()
        words |= _TYPE_SYNONYMS.get(lowered, {lowered})
        words |= name_words(token)
    return {_lemma(w) for w in words}


def restates_type(param: Param) -> bool:
    """Whether a parameter's description only restates its annotation.

    >>> restates_type(Param("n", "int", "an integer"))
    True
    >>> restates_type(Param("n", "int", "how many retries before giving up"))
    False
    >>> restates_type(Param("n", None, "an integer"))
    False
    """
    if not param.annotation or not param.description:
        return False
    words = content_words(param.description) - name_words(param.name)
    return bool(words) and words <= annotation_words(param.annotation)


# --------------------------------------------------------------------------
# Collecting the public surface
# --------------------------------------------------------------------------


def _names_in_all(tree: ast.Module) -> set[str] | None:
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            value = node.value
            if isinstance(value, (ast.List, ast.Tuple)):
                return {
                    e.value
                    for e in value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                }
    return None


def entry_point_names(package_dir: Path) -> set[str]:
    """Names the package's ``__init__`` exposes: ``__all__``, else what it binds without a leading underscore."""
    init = Path(package_dir) / "__init__.py"
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return set()
    declared = _names_in_all(tree)
    if declared is not None:
        return declared
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                if bound != "*":
                    names.add(bound)
        elif isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return {n for n in names if not n.startswith("_")}


_RST_PARAM_RE = re.compile(
    r"^\s*:(?:param|parameter|arg|argument|key|keyword)\s+(?:[^:]*?\s)?(\*{0,2}\w+)\s*:\s*(.*)$"
)
_GOOGLE_ARGS_HEADER_RE = re.compile(
    r"^\s*(?:args|arguments|parameters|keyword args|keyword arguments|other parameters)\s*:\s*$",
    re.IGNORECASE,
)
_GOOGLE_PARAM_RE = re.compile(r"^(\s+)(\*{0,2}\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)$")
_NUMPY_PARAM_RE = re.compile(r"^(\*{0,2}\w+)(?:\s*:\s*.*)?$")
_NUMPY_HEADER = ("parameters", "other parameters")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def param_descriptions(docstring: str) -> dict[str, str]:
    """``{name: description}`` from an RST, Google or NumPy docstring, first line plus continuations.

    Deliberately not delegated to ``docstring_parser`` (an optional extra):
    a detector's verdict must not depend on what is installed.

    >>> param_descriptions(":param n: how many\\n    retries\\n:param delay: seconds")
    {'n': 'how many retries', 'delay': 'seconds'}
    >>> param_descriptions("Args:\\n    n (int): how many\\n    delay: seconds\\n\\nReturns:\\n    x")
    {'n': 'how many', 'delay': 'seconds'}
    >>> param_descriptions("Parameters\\n----------\\nn : int\\n    how many\\ndelay\\n    seconds\\n\\nReturns\\n-------")
    {'n': 'how many', 'delay': 'seconds'}
    """
    lines = docstring.replace("\t", "    ").splitlines()
    found: dict[str, list[str]] = {}
    current: str | None = None
    current_indent = -1
    mode: str | None = None  # "rst" | "google" | "numpy"
    section_indent = -1
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if mode == "rst":
                current = None
            continue
        rst = _RST_PARAM_RE.match(line)
        if rst:
            mode, current, current_indent = (
                "rst",
                rst.group(1).lstrip("*"),
                _indent(line),
            )
            found[current] = [rst.group(2).strip()]
            continue
        if _GOOGLE_ARGS_HEADER_RE.match(line):
            mode, section_indent, current = "google", _indent(line), None
            continue
        if (
            stripped.lower() in _NUMPY_HEADER
            and index + 1 < len(lines)
            and set(lines[index + 1].strip()) <= {"-", "="}
            and lines[index + 1].strip()
        ):
            mode, section_indent, current = "numpy", _indent(line), None
            continue
        if mode == "google":
            if _indent(line) <= section_indent:
                mode, current = None, None
                continue
            google = _GOOGLE_PARAM_RE.match(line)
            if google and (current is None or _indent(line) <= current_indent):
                current, current_indent = google.group(2).lstrip("*"), _indent(line)
                found[current] = [google.group(3).strip()]
                continue
        elif mode == "numpy":
            if _indent(line) == section_indent:
                following = lines[index + 1].strip() if index + 1 < len(lines) else ""
                if following and set(following) <= {"-", "="}:
                    mode, current = None, None  # the next section's header
                    continue
                numpy = _NUMPY_PARAM_RE.match(stripped)
                if numpy:
                    current, current_indent = numpy.group(1).lstrip("*"), _indent(line)
                    found[current] = []
                continue
            if _indent(line) < section_indent:
                mode, current = None, None
                continue
        if current is not None and _indent(line) > current_indent:
            found[current].append(stripped)
            continue
        if mode == "rst":
            current = None
    return {name: " ".join(" ".join(parts).split()) for name, parts in found.items()}


def _params_of(node: ast.AST, source: str, docstring: str | None) -> list[Param]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    described = param_descriptions(docstring) if docstring else {}
    params = []
    args = node.args
    for arg in [
        *args.posonlyargs,
        *args.args,
        *args.kwonlyargs,
        *filter(None, (args.vararg, args.kwarg)),
    ]:
        if arg.arg in ("self", "cls"):
            continue
        annotation = (
            ast.get_source_segment(source, arg.annotation) if arg.annotation else None
        )
        params.append(Param(arg.arg, annotation, described.get(arg.arg)))
    return params


def iter_public_objects(
    package_dir: Path,
    *,
    ignore: Iterable[str] = (),
    files: Iterable[Path] | None = None,
    all_entry_points: bool = False,
) -> Iterator[PublicObject]:
    """Every public module, class and function under ``package_dir``.

    Public means no leading underscore anywhere in the dotted name below the
    package; a module's ``__all__``, when present, narrows its public names.
    ``all_entry_points`` treats every top-level name as an entry point (rule
    fixtures use it: they have no package ``__init__``).
    """
    package_dir = Path(package_dir)
    entry_points = entry_point_names(package_dir)
    for path in (
        files if files is not None else iter_python_files(package_dir, ignore=ignore)
    ):
        path = Path(path)
        try:
            rel = path.relative_to(package_dir)
        except ValueError:
            rel = Path(path.name)
        if any(part.startswith("_") and part != "__init__.py" for part in rel.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError, UnicodeDecodeError):
            continue
        module_parts = list(rel.with_suffix("").parts)
        if module_parts and module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        module = ".".join([package_dir.name, *module_parts])
        file = rel.as_posix()
        declared = _names_in_all(tree)
        doc = _docstring_node(tree)
        yield PublicObject(
            qualname=module,
            kind="module",
            file=file,
            line=1,
            docstring=doc.value if doc else None,
            name=module.rsplit(".", 1)[-1],
        )
        is_init = rel.name == "__init__.py"

        def visit(owner: ast.AST, qualname: str, top: bool) -> Iterator[PublicObject]:
            for child in _iter_defs(owner):
                if child.name.startswith("_"):
                    continue
                if top and declared is not None and child.name not in declared:
                    continue
                doc = _docstring_node(child)
                text = doc.value if doc else None
                kind = "class" if isinstance(child, ast.ClassDef) else "function"
                yield PublicObject(
                    qualname=f"{qualname}.{child.name}",
                    kind=kind,
                    file=file,
                    line=child.lineno,
                    docstring=text,
                    params=_params_of(child, source, text),
                    is_entry_point=top
                    and (all_entry_points or child.name in entry_points or is_init),
                    name=child.name,
                )
                if kind == "class":
                    yield from visit(child, f"{qualname}.{child.name}", False)

        yield from visit(tree, module, True)


# --------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------


@coverage_detector("missing_docstring")
def missing_docstring(obj: PublicObject) -> list[str]:
    """A public module, class or function with no docstring at all (DQ001)."""
    return [obj.qualname] if not obj.docstring or not obj.docstring.strip() else []


@coverage_detector("entry_point_without_example")
def entry_point_without_example(obj: PublicObject) -> list[str]:
    """An entry point (bound by the package ``__init__``) whose docstring has no ``>>>`` (DQ002)."""
    if obj.kind == "module" or not obj.is_entry_point or not obj.docstring:
        return []
    return [] if obj.has_example else [obj.qualname]


@coverage_detector("trivial_summary")
def trivial_summary(obj: PublicObject) -> list[str]:
    """A summary whose content words all come from the object's name (DQ003)."""
    if obj.kind == "module":
        return []
    summary = obj.summary
    return [summary] if summary and trivial_summary_words(obj.name, summary) else []


@coverage_detector("type_restatement")
def type_restatement(obj: PublicObject) -> list[str]:
    """A parameter description that only restates the annotation (DQ004)."""
    return [f"{p.name}: {p.description}" for p in obj.params if restates_type(p)]


@coverage_detector("meta_language_summary")
def meta_language_summary(obj: PublicObject) -> list[str]:
    """A summary that talks about the object instead of saying what it does (DQ005)."""
    summary = obj.summary
    return [summary] if summary and META_LANGUAGE_RE.match(summary) else []


@dataclass
class CoverageCase:
    """One tagged specimen of a coverage fixture: the object and what the tag promises."""

    name: str
    line: int
    expect_hit: bool
    rule_ids: tuple[str, ...]
    object: PublicObject


def iter_coverage_cases(fixture_path: Path) -> Iterator[CoverageCase]:
    """The tagged specimens of a coverage fixture (a specimen may have no docstring at all)."""
    from epythet.validation.ledger import FIXTURE_TAG_RE

    fixture_path = Path(fixture_path)
    lines = fixture_path.read_text(encoding="utf-8").splitlines()
    for obj in iter_public_objects(
        fixture_path.parent, files=[fixture_path], all_entry_points=True
    ):
        if obj.kind == "module":
            continue
        header = lines[obj.line - 1] if obj.line - 1 < len(lines) else ""
        tag = FIXTURE_TAG_RE.search(header)
        if tag is None:
            continue
        yield CoverageCase(
            name=obj.qualname,
            line=obj.line,
            expect_hit=tag.group(1) == "ruleid",
            rule_ids=tuple(s.strip() for s in tag.group(2).split(",")),
            object=obj,
        )


def evaluate_coverage_rule(rule: Rule, obj: PublicObject) -> list[str]:
    """Run one ``coverage``-kind rule over one public object."""
    return COVERAGE_DETECTORS[rule.detector["function"]](obj)


def run_coverage_level(
    package_dir: Path, ledger: Ledger, *, ignore: Iterable[str] = ()
) -> tuple[list[Finding], int, int]:
    """Level 0 coverage: ``(findings, objects_checked, objects_undocumented)``."""
    rules = ledger.of_kind("coverage")
    findings: list[Finding] = []
    checked = undocumented = 0
    for obj in iter_public_objects(Path(package_dir), ignore=ignore):
        checked += 1
        if not obj.docstring:
            undocumented += 1
        for rule in rules:
            hits = evaluate_coverage_rule(rule, obj)
            if not hits:
                continue
            message = rule.format_message(hits[0])
            if len(hits) > 1:
                message += f" ({len(hits)} occurrences)"
            findings.append(
                rule.finding(
                    level=COVERAGE_LEVEL,
                    evidence=hits[0],
                    file=f"{Path(package_dir).name}/{obj.file}",
                    line=obj.line,
                    object=obj.qualname,
                    message=message,
                )
            )
    return findings, checked, undocumented
