"""Docstring extraction from Python source, without importing anything.

Every level below the build reads docstrings straight from the ``ast``, so the
package under validation never has to be importable (and never runs). What
autodoc would see is approximated with :func:`inspect.cleandoc`, which is
what Sphinx's ``prepare_docstring`` does modulo tab expansion.

Each :class:`Docstring` carries both the *processed* text (what Python hands
to Sphinx) and the literal's *source segment* (what the author typed), because
one seed rule (DR020, backslashes eaten by a non-raw string) is only visible
in the latter.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

DocKind = str  # "module" | "class" | "function"


@dataclass
class Docstring:
    """One docstring and where it came from."""

    file: str
    line: int
    def_line: int
    qualname: str
    kind: DocKind
    text: str
    source: str
    is_raw: bool

    @property
    def lines(self) -> list[str]:
        """The processed text, split into lines."""
        return self.text.splitlines()


def _module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([root.name, *parts]) if parts else root.name


def _docstring_node(node: ast.AST) -> ast.Constant | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def _is_raw_literal(segment: str | None) -> bool:
    """Whether a string literal's source uses an ``r``/``R`` prefix.

    >>> _is_raw_literal("r'x'"), _is_raw_literal("'x'"), _is_raw_literal("Rb'x'")
    (True, False, True)
    """
    if not segment:
        return False
    prefix = segment[: len(segment) - len(segment.lstrip("rRbBuUfF"))]
    return "r" in prefix.lower()


_CONTAINERS = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
)
if hasattr(ast, "TryStar"):  # Python 3.11+
    _CONTAINERS += (ast.TryStar,)
if hasattr(ast, "Match"):  # Python 3.10+
    _CONTAINERS += (ast.Match, ast.match_case)


def _iter_defs(node: ast.AST) -> Iterator[ast.AST]:
    """Class and function definitions directly owned by ``node``.

    Definitions nested in ``if``/``try``/``with``/loop bodies belong to the same
    owner (autodoc documents them), so those statements are looked through.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            yield child
        elif isinstance(child, _CONTAINERS):
            yield from _iter_defs(child)


def iter_file_docstrings(
    path: Path,
    *,
    root: Path | None = None,
    on_skip: Callable[[Path, str], None] | None = None,
) -> Iterator[Docstring]:
    """Yield the module, class and function docstrings of one file, in source order.

    A file that does not parse or decode is skipped; ``on_skip(path, reason)``
    is called so the caller can report it (a syntax error is the linter's
    business, but silence would hide a docstring from the ledger).
    """
    path = Path(path)
    root = Path(root) if root is not None else path.parent
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, ValueError, UnicodeDecodeError) as e:
        if on_skip is not None:
            on_skip(path, f"{type(e).__name__}: {e}")
        return
    module = _module_name(path, root)
    rel = (
        path.relative_to(root.parent).as_posix() if root in path.parents else path.name
    )

    def visit(node: ast.AST, qualname: str, kind: DocKind) -> Iterator[Docstring]:
        doc = _docstring_node(node)
        if doc is not None:
            segment = ast.get_source_segment(source, doc) or ""
            yield Docstring(
                file=rel,
                line=doc.lineno,
                def_line=getattr(node, "lineno", doc.lineno),
                qualname=qualname,
                kind=kind,
                text=inspect.cleandoc(doc.value),
                source=segment,
                is_raw=_is_raw_literal(segment),
            )
        for child in _iter_defs(node):
            child_kind = "class" if isinstance(child, ast.ClassDef) else "function"
            yield from visit(child, f"{qualname}.{child.name}", child_kind)

    yield from visit(tree, module, "module")


def _in_package(path: Path, package_dir: Path) -> bool:
    """Whether every directory from ``package_dir`` down to ``path`` is a package.

    Data directories inside a package (epythet's own ``ledger/rules`` fixtures,
    for instance) hold ``.py`` files autodoc never sees; they are skipped the
    same way ``epythet.autogen`` skips them.
    """
    for parent in path.relative_to(package_dir).parents:
        if parent != Path(".") and not (package_dir / parent / "__init__.py").exists():
            return False
    return True


def iter_python_files(
    package_dir: Path, *, ignore: Iterable[str] = ()
) -> Iterator[Path]:
    """Every ``.py`` in the package tree, skipping caches, non-package dirs and ``ignore`` substrings."""
    ignore = tuple(ignore)
    package_dir = Path(package_dir)
    for path in sorted(package_dir.rglob("*.py")):
        posix = path.as_posix()
        if "__pycache__" in path.parts or not _in_package(path, package_dir):
            continue
        if any(token in posix for token in ignore):
            continue
        yield path


def iter_docstrings(
    package_dir: Path,
    *,
    ignore: Iterable[str] = (),
    on_skip: Callable[[Path, str], None] | None = None,
) -> Iterator[Docstring]:
    """Yield every docstring in a package directory tree."""
    package_dir = Path(package_dir)
    for path in iter_python_files(package_dir, ignore=ignore):
        yield from iter_file_docstrings(path, root=package_dir, on_skip=on_skip)


@dataclass
class Coverage:
    """How many public objects were seen and how many lack a docstring."""

    checked: int = 0
    undocumented: int = 0


def count_public_objects(package_dir: Path, *, ignore: Iterable[str] = ()) -> Coverage:
    """Count public modules, classes and functions, and those without a docstring.

    "Public" means no leading underscore anywhere in the dotted name below the
    package. Nested functions are counted like any other def.
    """
    coverage = Coverage()
    for path in iter_python_files(Path(package_dir), ignore=ignore):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError, UnicodeDecodeError):
            continue
        rel_parts = path.relative_to(Path(package_dir)).parts
        if any(part.startswith("_") and part != "__init__.py" for part in rel_parts):
            continue
        nodes = [tree] + [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        ]
        for node in nodes:
            coverage.checked += 1
            if _docstring_node(node) is None:
                coverage.undocumented += 1
    return coverage
