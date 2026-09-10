"""``epythet repair``: apply the normalizer's source-safe rewrites to docstrings in place.

The build-time normalizer (:mod:`epythet.normalizer`) fixes a docstring's
markup on the fly, so the rendered site is right without editing anything.
This module writes the same fixes *back into the source*, for the packages
that want their docstrings right at rest (decision D9). It is deliberately
narrow:

- Only the docstring literal changes. The rest of the file is copied byte
  for byte (exact-span rewriting, no unparsing), and the module's AST with
  docstrings blanked must be identical before and after or the file is not
  written.
- Only the normalizer's *source-safe* rules run (:data:`SOURCE_SAFE_RULES`):
  a blank line before a doctest, list or field list; a Markdown fence to a
  ``code-block`` (or a ``::`` literal block, ``fence_style="literal"``);
  ``Returns: text`` one-liners to real sections; ``## Heading`` to a rubric;
  ``[text](url)`` to an RST link; short underlines padded. Escaping a
  prose ``*args`` is *not* source-safe (it changes what the author wrote,
  and a later reader may not know why the backslash is there), so it stays a
  diagnostic (DR010), like unmatched backticks and every other artifact the
  normalizer cannot fix.
- Every doctest keeps its source lines byte for byte (checked with
  :mod:`doctest`'s own parser); a rewrite that would change one is skipped.
- Every rewritten docstring is re-validated at level 0.5: a rewrite that
  introduces a finding the original did not have is dropped. With
  ``write=True`` the doctests of every touched file are run before and after
  (the module is *imported* for that, so its top level runs; pass
  ``run_doctests=False`` / ``--no-doctests`` for code that must not run), and
  a file whose failures went up is restored. A module that cannot be imported
  is written but reported as unverified.
- Line endings (CRLF), a UTF-8 BOM and tab indentation are preserved; a file
  is replaced atomically.

Dry run is the default and prints a unified diff; ``write=True`` applies.
The seam ``applier=`` swaps the rewriting substrate: :func:`apply_span_edits`
(default, no dependency) or :func:`apply_with_libcst` (when LibCST is
installed; it re-parses the module as a concrete syntax tree and replaces
the string nodes).

>>> from epythet.repair import rewrite_docstring_literal
>>> literal = '\"\"\"Do it.\\n    - one\\n    - two\\n    \"\"\"'
>>> new, reason = rewrite_docstring_literal(literal)
>>> new.split("\\n"), reason
(['\"\"\"Do it.', '', '    - one', '    - two', '    \"\"\"'], None)
>>> rewrite_docstring_literal('\"\"\"Has a \\\\n escape.\"\"\"')[1]
'non-raw literal with backslashes: escapes would change'
"""

from __future__ import annotations

import ast
import difflib
import doctest
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from epythet import normalizer as N
from epythet.validation.docstrings import Docstring, iter_python_files
from epythet.validation.model import Finding

#: The normalizer rules whose rewrite is safe to commit to source, in normalizer order.
SOURCE_SAFE_RULES: tuple[N.Rule, ...] = tuple(
    rule for rule in N.DEFAULT_RULES if rule is not N.escape_unmatched_stars
)
#: Normalizer rules that stay build-time only, and why.
UNSAFE_RULES: dict[str, str] = {
    N.escape_unmatched_stars.__name__: "escaping *args in prose changes what the author wrote; reported as DR010 instead",
}
FENCE_STYLES = ("code-block", "literal")
_PREFIX_CHARS = "rRbBuUfF"
_DOCTEST_FAILURES_RE = re.compile(r"\*\*\*Test Failed\*\*\* (\d+) failure")


# --------------------------------------------------------------------------
# One literal
# --------------------------------------------------------------------------


def fences_to_literal_blocks(lines: list[str]) -> list[str]:
    """The ``fence_style="literal"`` variant: a fence becomes a ``::`` literal block.

    A literal block needs no directive support and, unlike ``code-block``,
    is safe inside a docstring that a doctest runner reads (a ``>>>`` line
    inside it is still literal, but is never mistaken for a directive body).

    >>> N.normalize_text("Run:\\n```bash\\npip install x\\n```\\nDone.", rules=[fences_to_literal_blocks])
    'Run::\\n\\n    pip install x\\n\\nDone.'
    """
    contexts = N.line_contexts(lines)
    out: list[str] = []
    i = 0
    while i < len(lines):
        match = N._FENCE_RE.match(lines[i])
        if not (match and contexts[i] == N.FENCE):
            out.append(lines[i])
            i += 1
            continue
        indent = match.group(1)
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("```"):
            body.append(lines[j])
            j += 1
        nonblank = [line for line in body if line.strip()]
        common = min((N.indent_of(line) for line in nonblank), default=0)
        body = [
            (indent + "    " + line[common:]) if line.strip() else "" for line in body
        ]
        if out and out[-1].strip() and not out[-1].rstrip().endswith("::"):
            out[-1] = out[-1].rstrip() + (
                "::" if not out[-1].rstrip().endswith(":") else ":"
            )
        elif not out or not out[-1].strip():
            out.append(f"{indent}::")
        out.append("")
        out.extend(body)
        out.append("")
        i = j + 1
    return out


def rules_for(
    fence_style: str = "code-block", rules: Sequence[N.Rule] = SOURCE_SAFE_RULES
) -> tuple[N.Rule, ...]:
    """The rule tuple for a fence style (``literal`` swaps the fence rule)."""
    if fence_style not in FENCE_STYLES:
        raise ValueError(
            f"fence_style must be one of {FENCE_STYLES}, got {fence_style!r}"
        )
    if fence_style == "code-block":
        return tuple(rules)
    return tuple(
        fences_to_literal_blocks if rule is N.fences_to_code_blocks else rule
        for rule in rules
    )


def split_literal(segment: str) -> tuple[str, str, str, str] | None:
    """``(prefix, quote, body, closing quote)`` of a string literal's source, or ``None``.

    >>> split_literal('r\"\"\"x\"\"\"')
    ('r', '\"\"\"', 'x', '\"\"\"')
    >>> split_literal("'y'")
    ('', "'", 'y', "'")
    """
    prefix_len = len(segment) - len(segment.lstrip(_PREFIX_CHARS))
    prefix, rest = segment[:prefix_len], segment[prefix_len:]
    for quote in ('"""', "'''", '"', "'"):
        if (
            rest.startswith(quote)
            and rest.endswith(quote)
            and len(rest) >= 2 * len(quote)
        ):
            return prefix, quote, rest[len(quote) : -len(quote)], quote
    return None


def _margin(lines: Sequence[str]) -> str:
    r"""The whitespace every non-blank line after the first starts with (tabs included).

    >>> _margin(["Summary.", "\t\tone", "\t\t\ttwo", ""])
    '\t\t'
    >>> _margin(["one line"])
    ''
    """
    rest = [line for line in lines[1:] if line.strip()]
    if not rest:
        return ""
    margin = rest[0][: len(rest[0]) - len(rest[0].lstrip())]
    for line in rest[1:]:
        while not line.startswith(margin):
            margin = margin[:-1]
    return margin


def _body_indented(lines: Sequence[str]) -> bool:
    """Whether every non-blank line after the first is indented (what ``cleandoc`` flattens).

    >>> _body_indented(["Returns:", "    the x"]), _body_indented(["Text", "- one"])
    (True, False)
    """
    rest = [line for line in lines[1:] if line.strip()]
    return bool(rest) and all(N.indent_of(line) > 0 for line in rest)


def _doctest_sources(text: str) -> list[str] | None:
    """Doctest example sources, or ``None`` when :mod:`doctest` cannot parse the text."""
    try:
        return [
            example.source for example in doctest.DocTestParser().get_examples(text)
        ]
    except ValueError:
        return None


def rewrite_docstring_literal(
    segment: str, *, rules: Sequence[N.Rule] = SOURCE_SAFE_RULES
) -> tuple[str, str | None]:
    """Rewrite one docstring literal's source; returns ``(new_segment, reason_if_unsafe)``.

    The body is dedented the way :func:`inspect.cleandoc` does (the first
    line stays as written), the rules run, and the result is re-indented to
    the original margin. Indentation-only lines (the closing-quote line) are
    preserved.
    """
    parts = split_literal(segment)
    if parts is None:
        return segment, "not a plain string literal"
    prefix, quote, body, _ = parts
    if "b" in prefix.lower() or "f" in prefix.lower():
        return segment, "bytes or f-string literal"
    if "r" not in prefix.lower() and "\\" in body:
        return segment, "non-raw literal with backslashes: escapes would change"
    lines = body.split("\n")
    trailing = None
    if len(lines) > 1 and not lines[-1].strip():
        trailing = lines.pop()  # the closing quote's own line: keep its indentation
    margin = _margin(lines)
    dedented = [
        lines[0],
        *[line[len(margin) :] if line.strip() else "" for line in lines[1:]],
    ]
    before_sources = _doctest_sources("\n".join(dedented))
    if before_sources is None:
        return segment, "doctest could not parse the docstring; fix the doctest first"
    normalized = N.normalize_docstring(dedented, rules=rules)
    while normalized and not normalized[-1].strip() and trailing is not None:
        normalized.pop()
    if normalized == dedented:
        return segment, None
    if len(quote) == 1 and (len(normalized) > 1 or "\n" in normalized[0]):
        return segment, "single-quoted docstring would need a triple-quoted rewrite"
    if _doctest_sources("\n".join(normalized)) != before_sources:
        return segment, "the rewrite would change a doctest's source"
    reindented = [(margin + line) if line.strip() else "" for line in normalized[1:]]
    if (
        _body_indented(normalized)
        and not _body_indented(dedented)
        and normalized[0].strip()
    ):
        # The rewrite indented everything under the first line (a one-line section
        # became a header with a body). ``inspect.cleandoc`` strips the common
        # indentation of the lines after the first, so only the leading-newline
        # form keeps the body under its header.
        reindented[:0] = ["", margin + normalized[0].strip()]
    else:
        reindented.insert(0, normalized[0])
    if trailing is not None:
        reindented.append(trailing)
    new_body = "\n".join(reindented)
    if quote in new_body:
        return segment, "the rewrite would contain the quote sequence"
    return f"{prefix}{quote}{new_body}{quote}", None


# --------------------------------------------------------------------------
# One file
# --------------------------------------------------------------------------


@dataclass
class DocstringEdit:
    """One docstring the repair rewrote (or refused to)."""

    qualname: str
    line: int
    start: int  # character offset of the literal in the source
    end: int
    before: str  # literal source
    after: str
    reason: str | None = None  # why it was not rewritten
    fixed: list[str] = field(default_factory=list)  # rule ids no longer firing
    remaining: list[str] = field(default_factory=list)  # rule ids still firing

    @property
    def applied(self) -> bool:
        return self.reason is None and self.after != self.before


@dataclass
class FileRepair:
    """What the repair did to one file."""

    path: Path
    original: str
    repaired: str
    edits: list[DocstringEdit] = field(default_factory=list)
    skipped: str | None = None  # the whole file was left alone, and why
    written: bool = False
    verification: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.repaired != self.original

    @property
    def applied(self) -> list[DocstringEdit]:
        return [e for e in self.edits if e.applied]

    @property
    def refused(self) -> list[DocstringEdit]:
        """Docstrings left for a hand: a refused rewrite, or findings no rule fixes.

        A docstring that was rewritten but still has findings counts too, so
        the number is the same on the dry run, the write, and the run after.
        """
        return [e for e in self.edits if e.reason or e.remaining]

    def diff(self) -> str:
        """The unified diff of the file, empty when nothing changed."""
        return "".join(
            difflib.unified_diff(
                self.original.splitlines(keepends=True),
                self.repaired.splitlines(keepends=True),
                fromfile=f"a/{self.path.name}",
                tofile=f"b/{self.path.name}",
            )
        )


def _line_offsets(source: str) -> list[int]:
    """Character offset of the start of each line; ``\\n`` only, as ``ast`` counts lines.

    (``str.splitlines`` would also split on form feeds and U+2028, which the
    parser does not.)
    """
    offsets = [0]
    for line in source.split("\n")[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    offsets.append(len(source) + 1)
    return offsets


def _offset(offsets: list[int], source: str, lineno: int, col: int) -> int:
    """Character offset of ``(lineno, col)``; ``col`` is a UTF-8 byte offset in ``ast``."""
    line_start = offsets[lineno - 1]
    line = source[
        line_start : offsets[lineno] if lineno < len(offsets) else len(source)
    ]
    return line_start + len(line.encode("utf-8")[:col].decode("utf-8", errors="ignore"))


def iter_docstring_nodes(tree: ast.Module):
    """``(qualname, node, constant)`` for every docstring in a parsed module."""
    from epythet.validation.docstrings import _docstring_node, _iter_defs

    def visit(node, qualname):
        constant = _docstring_node(node)
        if constant is not None:
            yield qualname, node, constant
        for child in _iter_defs(node):
            yield from visit(
                child, f"{qualname}.{child.name}" if qualname else child.name
            )

    yield from visit(tree, "")


def _ast_fingerprint(source: str) -> str:
    """The module's AST with every docstring blanked: what a repair must not change."""
    tree = ast.parse(source)
    for _qualname, _node, constant in iter_docstring_nodes(tree):
        constant.value = ""
    return ast.dump(tree)


Applier = Callable[[str, Sequence[DocstringEdit]], str]


def apply_span_edits(source: str, edits: Sequence[DocstringEdit]) -> str:
    """Splice each edit's ``after`` over its ``[start, end)`` span, last edit first."""
    out = source
    for edit in sorted(
        (e for e in edits if e.applied), key=lambda e: e.start, reverse=True
    ):
        out = out[: edit.start] + edit.after + out[edit.end :]
    return out


def apply_with_libcst(source: str, edits: Sequence[DocstringEdit]) -> str:
    """The LibCST applier: replace the matching ``SimpleString`` nodes of a concrete syntax tree."""
    import libcst as cst
    from libcst.metadata import MetadataWrapper, PositionProvider

    wanted = {(e.line, e.before): e.after for e in edits if e.applied}

    class Replace(cst.CSTTransformer):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def leave_SimpleString(self, original, updated):
            position = self.get_metadata(PositionProvider, original)
            key = (position.start.line, original.value)
            if key in wanted:
                return updated.with_changes(value=wanted[key])
            return updated

    return MetadataWrapper(cst.parse_module(source)).visit(Replace()).code


def _findings_for_text(text: str, *, qualname: str, rules, napoleon: bool) -> list[str]:
    """Rule ids that fire on a docstring text at level 0.5."""
    from epythet.validation.parse import findings_for, parse_docstring

    doc = Docstring(
        file="",
        line=0,
        def_line=0,
        qualname=qualname,
        kind="function",
        text=text,
        source="",
        is_raw=True,
    )
    return sorted(
        {f.rule for f in findings_for(parse_docstring(doc, napoleon=napoleon), rules)}
    )


def repair_source(
    source: str,
    *,
    rules: Sequence[N.Rule] = SOURCE_SAFE_RULES,
    ledger_rules=(),
    napoleon: bool = True,
    applier: Applier = apply_span_edits,
    path: Path | None = None,
) -> FileRepair:
    """Repair every docstring of one module's source text; nothing is written."""
    import inspect

    repair = FileRepair(path=path or Path("<source>"), original=source, repaired=source)
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        repair.skipped = f"{type(e).__name__}: {e}"
        return repair
    offsets = _line_offsets(source)
    for qualname, _node, constant in iter_docstring_nodes(tree):
        start = _offset(offsets, source, constant.lineno, constant.col_offset)
        end = _offset(offsets, source, constant.end_lineno, constant.end_col_offset)
        before = source[start:end]
        after, reason = rewrite_docstring_literal(before, rules=rules)
        edit = DocstringEdit(
            qualname=qualname or "<module>",
            line=constant.lineno,
            start=start,
            end=end,
            before=before,
            after=after,
            reason=reason,
        )
        if ledger_rules:
            was = _findings_for_text(
                inspect.cleandoc(constant.value),
                qualname=edit.qualname,
                rules=ledger_rules,
                napoleon=napoleon,
            )
            edit.remaining = was
            if edit.applied:
                new_parts = split_literal(after)
                new_text = (
                    inspect.cleandoc(new_parts[2]) if new_parts else constant.value
                )
                now = _findings_for_text(
                    new_text,
                    qualname=edit.qualname,
                    rules=ledger_rules,
                    napoleon=napoleon,
                )
                introduced = sorted(set(now) - set(was))
                if introduced:
                    edit.after, edit.reason = (
                        before,
                        f"the rewrite would introduce {', '.join(introduced)}",
                    )
                else:
                    edit.fixed = sorted(set(was) - set(now))
                    edit.remaining = now
        repair.edits.append(edit)
    if not repair.applied:
        return repair
    repaired = applier(source, repair.edits)
    try:
        if _ast_fingerprint(repaired) != _ast_fingerprint(source):
            repair.skipped = (
                "the rewrite changed the module's AST outside its docstrings"
            )
            return repair
    except SyntaxError as e:
        repair.skipped = f"the rewrite does not parse: {e}"
        return repair
    repair.repaired = repaired
    return repair


# --------------------------------------------------------------------------
# A package
# --------------------------------------------------------------------------


@dataclass
class RepairReport:
    """Everything one ``repair`` run did."""

    root: Path
    files: list[FileRepair] = field(default_factory=list)
    write: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> list[FileRepair]:
        return [f for f in self.files if f.changed]

    @property
    def refused(self) -> list[tuple[FileRepair, DocstringEdit]]:
        return [(f, e) for f in self.files for e in f.refused]

    def counts(self) -> dict[str, int]:
        return {
            "files": len(self.files),
            "files_changed": len(self.changed),
            "docstrings_rewritten": sum(len(f.applied) for f in self.files),
            "docstrings_refused": len(self.refused),
            "files_written": sum(1 for f in self.files if f.written),
        }

    def diff(self) -> str:
        return "".join(f.diff() for f in self.changed)


#: Runs a module's doctests by importing it under its dotted name (so relative
#: imports work) and prints ``failed attempted``; exit 3 when it cannot be imported.
_DOCTEST_RUNNER = """\
import doctest, importlib, sys
try:
    module = importlib.import_module(sys.argv[1])
except BaseException as e:
    print(f"import failed: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(3)
result = doctest.testmod(module)
print(result.failed, result.attempted)
sys.exit(1 if result.failed else 0)
"""
IMPORT_FAILED = -1


def _module_name(path: Path, project_dir: Path) -> str | None:
    """``pkg.sub.mod`` for a file under ``project_dir`` (or ``src/``), by its ``__init__`` chain."""
    path = Path(path).resolve()
    for root in (Path(project_dir).resolve(), Path(project_dir).resolve() / "src"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if parts and all(
            (root / Path(*parts[: i + 1]) / "__init__.py").exists()
            for i in range(len(parts) - (0 if rel.name == "__init__.py" else 1))
        ):
            return ".".join(parts)
    return None


def _doctest_failures(path: Path, *, project_dir: Path) -> tuple[int, int, str]:
    """``(returncode, failures, tail)`` of the file's doctests, run in a subprocess.

    ``failures`` is :data:`IMPORT_FAILED` when the module cannot be imported,
    which the caller reports as "not verified" rather than as a pass.
    """
    env = dict(os.environ)
    roots = [str(project_dir), str(Path(project_dir) / "src")]
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (*roots, env.get("PYTHONPATH", "")) if p
    )
    module = _module_name(path, project_dir)
    if module is None:
        command = [sys.executable, "-m", "doctest", str(path)]
    else:
        command = [sys.executable, "-c", _DOCTEST_RUNNER, module]
    proc = subprocess.run(
        command, cwd=project_dir, env=env, capture_output=True, text=True
    )
    output = (proc.stdout + proc.stderr).strip()
    tail = output.splitlines()[-1] if output else ""
    if module is not None:
        if proc.returncode == 3 or "import failed" in output:
            return proc.returncode, IMPORT_FAILED, tail
        try:
            failed, _attempted = proc.stdout.split()[-2:]
            return proc.returncode, int(failed), tail
        except (ValueError, IndexError):
            return proc.returncode, IMPORT_FAILED, tail
    match = _DOCTEST_FAILURES_RE.search(output)
    failures = (
        int(match.group(1)) if match else (0 if proc.returncode == 0 else IMPORT_FAILED)
    )
    return proc.returncode, failures, tail


def _read_source(path: Path) -> tuple[str, str, bool]:
    """``(text with LF newlines, original newline, had_bom)``."""
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), newline, bom


def _write_source(path: Path, text: str, *, newline: str, bom: bool) -> None:
    """Write ``text`` back with the file's own newline and BOM, replacing the file atomically."""
    data = text.replace("\n", newline).encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    tmp = path.with_name(f".{path.name}.epythet-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _files_under(path: Path, *, ignore: Iterable[str]) -> tuple[Path, list[Path]]:
    """``(project_dir, files)`` for a file, a package directory or a project root."""
    from epythet.validation.core import resolve_package

    path = Path(path).expanduser().resolve()
    if path.is_file():
        return _find_project(path.parent), [path]
    try:
        resolved = resolve_package(path)
    except FileNotFoundError:
        # A plain directory of .py files (no __init__, no pyproject): every file in it.
        files = [
            p
            for p in sorted(path.rglob("*.py"))
            if "__pycache__" not in p.parts
            and not any(t in p.as_posix() for t in ignore)
        ]
        if not files:
            raise
        return path, files
    return resolved.project_dir, list(
        iter_python_files(resolved.package_dir, ignore=ignore)
    )


def _find_project(start: Path) -> Path:
    from epythet.validation.core import _find_project_dir

    return _find_project_dir(start)


def repair(
    path: str | os.PathLike,
    *,
    write: bool = False,
    fence_style: str = "code-block",
    rules: Sequence[N.Rule] = SOURCE_SAFE_RULES,
    ignore: Iterable[str] = (),
    ledger=None,
    napoleon: bool = True,
    revalidate: bool = True,
    run_doctests: bool = True,
    applier: Applier = apply_span_edits,
) -> RepairReport:
    """Repair the docstrings under ``path`` (a file, package directory or project root).

    Args:
        path: What to repair.
        write: Apply the rewrites; the default only computes them (dry run).
        fence_style: What a Markdown fence becomes: ``code-block`` or ``literal``.
        rules: The normalizer rules to apply; :data:`SOURCE_SAFE_RULES` by default.
        ignore: Path substrings to skip, as ``epythet validate --ignore``.
        ledger: The rule catalog used to re-validate (``None`` = bundled).
        napoleon: Parse docstrings with napoleon's Google/NumPy pre-processing.
        revalidate: Drop a rewrite that introduces a level-0.5 finding.
        run_doctests: With ``write``, run each touched file's doctests before
            and after, and restore a file whose failures went up.
        applier: The rewriting substrate; :func:`apply_span_edits` or
            :func:`apply_with_libcst`.
    """
    from epythet.validation.ledger import PARSE_KINDS, load_ledger

    project_dir, files = _files_under(Path(path), ignore=ignore)
    report = RepairReport(root=Path(path), write=write)
    ledger_rules = ()
    if revalidate:
        catalog = load_ledger(ledger)
        ledger_rules = [
            r for r in catalog.of_kind(*PARSE_KINDS) if r.applies(napoleon=napoleon)
        ]
    active_rules = rules_for(fence_style, rules)
    for file in files:
        try:
            source, newline, bom = _read_source(file)
        except (OSError, UnicodeDecodeError) as e:
            report.files.append(
                FileRepair(
                    path=file,
                    original="",
                    repaired="",
                    skipped=f"{type(e).__name__}: {e}",
                )
            )
            continue
        result = repair_source(
            source,
            rules=active_rules,
            ledger_rules=ledger_rules,
            napoleon=napoleon,
            applier=applier,
            path=file,
        )
        report.files.append(result)
        if not (write and result.changed):
            continue
        before = (
            _doctest_failures(file, project_dir=project_dir) if run_doctests else None
        )
        _write_source(file, result.repaired, newline=newline, bom=bom)
        result.written = True
        if not run_doctests:
            continue
        after = _doctest_failures(file, project_dir=project_dir)
        if before[1] == IMPORT_FAILED and after[1] == IMPORT_FAILED:
            result.verification.append(
                f"not verified: the module could not be imported to run its doctests ({after[2]})"
            )
        elif after[1] == IMPORT_FAILED or after[1] > max(before[1], 0):
            _write_source(file, source, newline=newline, bom=bom)
            result.written = False
            result.verification.append(
                f"restored: doctest failures went from {before[1]} to {after[1]} ({after[2]})"
            )
        else:
            result.verification.append(
                f"doctests: {before[1]} failure(s) before, {after[1]} after"
            )
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def repair_command(
    path: str,
    *,
    write: bool = False,
    fence_style: str = "code-block",
    ignore: list[str] | None = None,
    ledger: str | None = None,
    no_napoleon: bool = False,
    no_doctests: bool = False,
    applier: str = "span",
    quiet: bool = False,
) -> None:
    """Rewrite docstrings so they render right: blank lines, fences, one-liner sections, links.

    Dry run by default: prints a unified diff of what --write would change.
    Unsafe cases (prose *args, unmatched backticks, backslashes in a non-raw
    docstring) are reported, never rewritten. Exit 0 when nothing is left to
    do or every write was verified; 3 when a written file had to be restored.

    :param path: A .py file, a package directory, or a project root.
    :param write: Apply the changes (after re-validating each docstring and re-running doctests).
    :param fence_style: What a Markdown fence becomes: code-block or literal.
    :param ignore: Skip files whose path contains this string (repeat -i for several).
    :param ledger: Directory of extra rule YAML files overlaid on the bundled ledger.
    :param no_napoleon: Re-validate without napoleon's Google/NumPy pre-processing.
    :param no_doctests: Do not run each touched file's doctests before and after writing.
    :param applier: The rewriting substrate: span (default) or libcst.
    :param quiet: Print the summary only, not the diff.
    """
    import cw

    from epythet.validation.ledger import LedgerError

    if fence_style not in FENCE_STYLES:
        raise cw.CommandError(
            f"--fence-style must be one of {list(FENCE_STYLES)}", code=2
        )
    appliers = {"span": apply_span_edits, "libcst": apply_with_libcst}
    if applier not in appliers:
        raise cw.CommandError(f"--applier must be one of {list(appliers)}", code=2)
    try:
        report = repair(
            path,
            write=write,
            fence_style=fence_style,
            ignore=ignore or (),
            ledger=ledger,
            napoleon=not no_napoleon,
            run_doctests=not no_doctests,
            applier=appliers[applier],
        )
    except (FileNotFoundError, LedgerError) as e:
        raise cw.CommandError(str(e), code=2) from e
    except ImportError as e:
        raise cw.CommandError(f"{e} (pip install 'epythet[repair]')", code=2) from e
    print(render_repair(report, diff=not quiet))
    if any(f.verification and not f.written for f in report.changed):
        raise cw.CommandError("a written file had to be restored; see above", code=3)


def render_repair(report: RepairReport, *, diff: bool = True) -> str:
    """The human report: the diff (dry run) or what was written, then the refusals."""
    lines: list[str] = []
    if diff and not report.write:
        lines.append(report.diff().rstrip("\n"))
    for file in report.changed:
        if report.write:
            state = "written" if file.written else "NOT written"
            lines.append(
                f"{file.path}: {len(file.applied)} docstring(s) rewritten, {state}"
            )
            lines += [f"    {v}" for v in file.verification]
        for edit in file.applied:
            if edit.fixed:
                lines.append(
                    f"    {file.path.name}:{edit.line} {edit.qualname}: fixed {', '.join(edit.fixed)}"
                )
    if report.refused:
        lines.append("")
        lines.append("needs a hand:")
        for file, edit in report.refused:
            if edit.reason:
                why = edit.reason
            elif edit.applied:
                why = "rewritten, but findings remain"
            else:
                why = "no source-safe rule fixes this"
            still = f" [{', '.join(edit.remaining)}]" if edit.remaining else ""
            lines.append(f"  {file.path}:{edit.line} {edit.qualname}: {why}{still}")
    for file in report.files:
        if file.skipped:
            lines.append(f"skipped {file.path}: {file.skipped}")
    counts = report.counts()
    mode = "written" if report.write else "would change (dry run; add --write)"
    lines.append("")
    lines.append(
        f"{counts['docstrings_rewritten']} docstring(s) in {counts['files_changed']} of "
        f"{counts['files']} file(s) {mode}; {counts['docstrings_refused']} left for a hand"
    )
    return "\n".join(line for line in lines if line is not None)
