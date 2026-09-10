"""``epythet migrate-style``: rewrite RST field lists as Google (or NumPy) sections, opt-in.

The fleet keeps both conventions and napoleon renders both, so nothing here
runs by default anywhere (maintainer decision 6: normalizer only, no mass
style conversion). This is the tool for the one package, module or file
whose maintainer wants ``:param x:`` lines to become an ``Args:`` section.

It is built on :mod:`epythet.repair`'s machinery and inherits every one of
its guarantees: exact-span rewriting, an unchanged AST outside docstrings,
byte-identical doctest sources, and a level-0.5 re-validation of each
rewritten docstring. On top of that it only converts what round-trips:

- the *field region* is the first contiguous block of ``:param``,
  ``:type``, ``:returns``, ``:rtype`` and ``:raises`` lines (with their
  indented continuations); prose before it and everything after it, doctests
  included, is copied verbatim;
- a region holding any other field (``:keyword``, ``:var``, ``:meta``, ...)
  is left alone, because ``docstring_parser.compose`` drops or mangles those;
- the composed section is parsed back and must describe the same
  parameters, return and exceptions as the original, or the docstring is
  left alone.

The conversion itself is ``docstring_parser.parse(..., style=REST)`` then
``compose(..., style=GOOGLE)`` (research §9); the substrate that writes it
back is the ``applier=`` seam of :func:`epythet.repair.repair`.

>>> from epythet.migrate import convert_fields
>>> print(convert_fields(":param x: the x value\\n:type x: int\\n:returns: x doubled\\n:rtype: int", to="google"))
Args:
    x (int): the x value
<BLANKLINE>
Returns:
    int: x doubled
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Sequence

from epythet import normalizer as N
from epythet.repair import (
    Applier,
    RepairReport,
    apply_span_edits,
    apply_with_libcst,
    render_repair,
    repair,
)

TARGET_STYLES = ("google", "numpy")
#: Field names whose conversion round-trips through ``docstring_parser``.
CONVERTIBLE_FIELDS = frozenset(
    {
        "param",
        "parameter",
        "arg",
        "argument",
        "type",
        "returns",
        "return",
        "rtype",
        "raises",
        "raise",
        "except",
        "exception",
    }
)
_FIELD_RE = re.compile(r"^(\s*):([a-zA-Z]+)(?:\s+[^:]*)?:")


def _field_name(line: str) -> str | None:
    match = _FIELD_RE.match(line)
    return match.group(2).lower() if match else None


def field_region(lines: Sequence[str]) -> tuple[int, int] | None:
    """``(start, end)`` of the first RST field block, or ``None``; ``end`` is exclusive.

    A block starts at a field line and takes every following field line at
    the same indentation and every continuation (a deeper-indented line, or a
    blank line followed by one of those).

    >>> field_region(["Summary.", "", ":param x: the x", "    more", ":returns: y", "", "Then prose."])
    (2, 5)
    >>> field_region(["No fields."]) is None
    True
    """
    contexts = N.line_contexts(lines)
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if contexts[i] == N.FIELD and _field_name(line)
        ),
        None,
    )
    if start is None:
        return None
    indent = N.indent_of(lines[start])
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            following = end + 1
            if (
                following < len(lines)
                and lines[following].strip()
                and (
                    (
                        _field_name(lines[following])
                        and N.indent_of(lines[following]) == indent
                    )
                    or N.indent_of(lines[following]) > indent
                )
            ):
                end += 1
                continue
            break
        if _field_name(line) and N.indent_of(line) == indent:
            end += 1
            continue
        if N.indent_of(line) > indent and contexts[end] not in (N.DOCTEST, N.FENCE):
            end += 1
            continue
        break
    return start, end


def _facts(docstring) -> tuple:
    """What a docstring says, independent of its style: params, return, raises."""
    params = tuple(
        (
            p.arg_name,
            (p.type_name or None),
            " ".join((p.description or "").split()),
            bool(p.is_optional),
        )
        for p in docstring.params
    )
    returns = None
    if docstring.returns is not None:
        r = docstring.returns
        returns = (
            (r.type_name or None),
            " ".join((r.description or "").split()),
            r.is_generator,
        )
    raises = tuple(
        ((r.type_name or None), " ".join((r.description or "").split()))
        for r in docstring.raises
    )
    return params, returns, raises


def convert_fields(region: str, *, to: str = "google") -> str | None:
    """Convert one RST field block to a Google or NumPy section block, or ``None`` if unsafe."""
    from docstring_parser import DocstringStyle, RenderingStyle, compose, parse

    if to not in TARGET_STYLES:
        raise ValueError(f"to must be one of {TARGET_STYLES}, got {to!r}")
    names = {_field_name(line) for line in region.splitlines() if _field_name(line)}
    if not names or not names <= CONVERTIBLE_FIELDS:
        return None
    stub = "Summary.\n\n"
    try:
        parsed = parse(stub + region, style=DocstringStyle.REST)
    except Exception:
        return None
    if not (parsed.params or parsed.returns or parsed.raises):
        return None
    style = DocstringStyle.GOOGLE if to == "google" else DocstringStyle.NUMPYDOC
    composed = compose(parsed, style=style, rendering_style=RenderingStyle.CLEAN)
    try:
        back = parse(composed, style=style)
    except Exception:
        return None
    if _facts(back) != _facts(parsed):
        return None
    body = composed[len("Summary.") :].lstrip("\n")
    # docstring_parser composes an untyped return as ``    : text``; drop the stray colon.
    body = re.sub(r"^(\s+): (?=\S)", r"\1", body, flags=re.M)
    return body.rstrip("\n")


def field_regions(lines: Sequence[str]) -> list[tuple[int, int]]:
    """Every field block of a docstring, in order.

    >>> field_regions([":param x: x", "", "prose", "", ":returns: y"])
    [(0, 1), (4, 5)]
    """
    regions: list[tuple[int, int]] = []
    offset = 0
    while True:
        region = field_region(lines[offset:])
        if region is None:
            return regions
        start, end = region[0] + offset, region[1] + offset
        regions.append((start, end))
        offset = end


def rst_fields_to_sections(to: str = "google") -> N.Rule:
    """A normalizer-shaped rule (``lines -> lines``) converting the docstring's field block.

    A docstring with more than one field block is left alone: converting one
    would leave a mixed-style docstring behind.
    """

    def rule(lines: list[str]) -> list[str]:
        regions = field_regions(lines)
        if len(regions) != 1:
            return lines
        start, end = regions[0]
        block = lines[start:end]
        while block and not block[-1].strip():
            block.pop()
            end -= 1
        indent = N.indent_of(block[0])
        dedented = "\n".join(line[indent:] if line.strip() else "" for line in block)
        converted = convert_fields(dedented, to=to)
        if converted is None:
            return lines
        pad = " " * indent
        new_block = [
            (pad + line) if line.strip() else "" for line in converted.split("\n")
        ]
        out = lines[:start]
        if out and out[-1].strip():
            out.append("")
        out += new_block
        rest = lines[end:]
        if rest and rest[0].strip():
            out.append("")
        return out + rest

    rule.__name__ = f"rst_fields_to_{to}"
    return rule


def migrate_style(
    path: str | os.PathLike,
    *,
    to: str = "google",
    write: bool = False,
    ignore: Iterable[str] = (),
    ledger=None,
    napoleon: bool = True,
    run_doctests: bool = True,
    applier: Applier = apply_span_edits,
) -> RepairReport:
    """Convert the RST field lists under ``path`` (a file, package or project) to ``to`` sections.

    Dry run by default; see :func:`epythet.repair.repair` for the arguments,
    which are the same.
    """
    if to not in TARGET_STYLES:
        raise ValueError(f"to must be one of {TARGET_STYLES}, got {to!r}")
    report = repair(
        path,
        write=write,
        rules=(rst_fields_to_sections(to),),
        ignore=ignore,
        ledger=ledger,
        napoleon=napoleon,
        run_doctests=run_doctests,
        applier=applier,
    )
    for file in report.files:
        for edit in file.edits:
            if edit.applied or edit.reason:
                continue
            edit.reason = _why_not_converted(edit.before)
    return report


def _why_not_converted(literal: str) -> str | None:
    """Why a docstring literal with fields was left alone, or ``None`` when it has no fields."""
    from epythet.repair import split_literal

    parts = split_literal(literal)
    if parts is None:
        return None
    lines = parts[2].split("\n")
    regions = field_regions(lines)
    if not regions:
        return None
    if len(regions) > 1:
        return f"{len(regions)} separate field blocks; converting one would mix styles"
    start, end = regions[0]
    names = {_field_name(line) for line in lines[start:end] if _field_name(line)}
    unconvertible = sorted(names - CONVERTIBLE_FIELDS)
    if unconvertible:
        return f"fields that do not round-trip: {', '.join(unconvertible)}"
    return (
        "the converted section did not describe the same parameters, return and raises"
    )


def migrate_style_command(
    path: str,
    *,
    to: str = "google",
    write: bool = False,
    ignore: list[str] | None = None,
    ledger: str | None = None,
    no_napoleon: bool = False,
    no_doctests: bool = False,
    applier: str = "span",
    quiet: bool = False,
) -> None:
    """Rewrite RST field lists (:param x:) as Google or NumPy sections, one file or package at a time.

    Opt-in and never part of a fleet sweep. Dry run by default: prints the
    diff --write would apply. Docstrings whose fields would not round-trip
    (:keyword, :var, :meta, ...) are left alone and listed.

    :param path: A .py file, a package directory, or a project root.
    :param to: Target convention: google or numpy.
    :param write: Apply the changes (after re-validating each docstring and re-running doctests).
    :param ignore: Skip files whose path contains this string (repeat -i for several).
    :param ledger: Directory of extra rule YAML files overlaid on the bundled ledger.
    :param no_napoleon: Re-validate without napoleon's Google/NumPy pre-processing.
    :param no_doctests: Do not run each touched file's doctests before and after writing.
    :param applier: The rewriting substrate: span (default) or libcst.
    :param quiet: Print the summary only, not the diff.
    """
    import cw

    if to not in TARGET_STYLES:
        raise cw.CommandError(f"--to must be one of {list(TARGET_STYLES)}", code=2)
    appliers = {"span": apply_span_edits, "libcst": apply_with_libcst}
    if applier not in appliers:
        raise cw.CommandError(f"--applier must be one of {list(appliers)}", code=2)
    try:
        report = migrate_style(
            path,
            to=to,
            write=write,
            ignore=ignore or (),
            ledger=ledger,
            napoleon=not no_napoleon,
            run_doctests=not no_doctests,
            applier=appliers[applier],
        )
    except FileNotFoundError as e:
        raise cw.CommandError(str(e), code=2) from e
    except ImportError as e:
        raise cw.CommandError(f"{e} (pip install 'epythet[migrate]')", code=2) from e
    print(render_repair(report, diff=not quiet))
    if any(f.verification and not f.written for f in report.changed):
        raise cw.CommandError("a written file had to be restored; see above", code=3)
