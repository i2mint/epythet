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
from typing import Iterable, Iterator

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


def iter_file_docstrings(
    path: Path, *, root: Path | None = None
) -> Iterator[Docstring]:
    """Yield the module, class and function docstrings of one file, in source order.

    Files that do not parse are skipped silently: a syntax error is the linter's
    business, not the renderer's.
    """
    path = Path(path)
    root = Path(root) if root is not None else path.parent
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, ValueError, UnicodeDecodeError):
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
        for child in getattr(node, "body", []):
            if isinstance(child, ast.ClassDef):
                yield from visit(child, f"{qualname}.{child.name}", "class")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from visit(child, f"{qualname}.{child.name}", "function")

    yield from visit(tree, module, "module")


def iter_python_files(
    package_dir: Path, *, ignore: Iterable[str] = ()
) -> Iterator[Path]:
    """Every ``.py`` under ``package_dir``, skipping caches and ``ignore`` substrings."""
    ignore = tuple(ignore)
    for path in sorted(Path(package_dir).rglob("*.py")):
        posix = path.as_posix()
        if "__pycache__" in path.parts:
            continue
        if any(token in posix for token in ignore):
            continue
        yield path


def iter_docstrings(
    package_dir: Path, *, ignore: Iterable[str] = ()
) -> Iterator[Docstring]:
    """Yield every docstring in a package directory tree."""
    package_dir = Path(package_dir)
    for path in iter_python_files(package_dir, ignore=ignore):
        yield from iter_file_docstrings(path, root=package_dir)


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
        if any(part.startswith("_") and part != "__init__.py" for part in path.parts):
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
