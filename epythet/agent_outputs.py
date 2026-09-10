"""Agent-facing outputs: ``llms.txt``, Markdown twins, link relations, aggregates.

Humans get the rendered HTML. Agents get, from the same build:

- ``llms.txt``: an index of every page with a one-line description, and
  ``<page>.md`` twins of every page, both produced by the ``sphinx_llm.txt``
  extension (which drives a second, Markdown build).
- ``<link rel="alternate" type="text/markdown">`` and
  ``<link rel="describedby" href="llms.txt">`` in every HTML page's ``<head>``,
  the llms.txt discovery contract. The plugin does not add these; the
  ``html-page-context`` hook here does.
- ``objects.inv``: the Sphinx inventory, already a machine-readable symbol index.
- Aggregates: one flat document with the whole site, at a stable URL at the
  site root: ``<package>.md`` (from the Markdown build's concatenation) and,
  when a renderer is available, ``<package>.pdf``. See :func:`write_aggregates`.

The ``aggregates`` seam is the ``aggregates`` key of the configuration:
``["md"]`` by default, ``["md", "pdf"]`` when a PDF is wanted.
"""

from __future__ import annotations

import shutil
from pathlib import Path

#: File the Markdown build writes when ``llms_txt_full_build`` is on.
LLMS_FULL_TXT = "llms-full.txt"


def sphinx_settings(*, description: str = "") -> dict:
    """The Sphinx configuration values for the agent outputs.

    ``llms_txt_full_build`` stays on because its concatenation is the ``<pkg>.md``
    aggregate; :func:`write_aggregates` renames it after the build.
    """
    return {
        "llms_txt_enabled": True,
        "llms_txt_full_build": True,
        "llms_txt_description": description,
        "llms_txt_summary_enabled": False,
    }


def inject_link_relations(app, pagename, templatename, context, doctree):
    """``html-page-context`` hook: advertise the Markdown twin and ``llms.txt``."""
    depth = pagename.count("/")
    root = "../" * depth
    metatags = context.get("metatags", "")
    metatags += (
        f'\n<link rel="alternate" type="text/markdown" href="{pagename}.html.md">'
        f'\n<link rel="describedby" href="{root}llms.txt" type="text/markdown">'
    )
    context["metatags"] = metatags


def write_aggregates(
    html_dir: str | Path, *, package_name: str, aggregates: tuple[str, ...] = ("md",)
) -> dict[str, Path]:
    """Produce the flat single-document twins at the root of a built site.

    :param html_dir: the built site (``docsrc/_build/html``)
    :param package_name: names the files: ``<package_name>.md`` / ``.pdf``
    :param aggregates: which of ``"md"``, ``"pdf"`` to produce
    :return: the files written, keyed by kind

    The ``.md`` aggregate is the Markdown build's ``llms-full.txt`` renamed, and
    ``llms.txt`` is rewritten to point at it. The ``.pdf`` aggregate is rendered
    from the ``.md`` one by :func:`markdown_to_pdf`, which needs an optional
    renderer; when none is installed the PDF is skipped with a notice.
    """
    html_dir = Path(html_dir)
    written: dict[str, Path] = {}
    md_target = html_dir / f"{package_name}.md"
    full = html_dir / LLMS_FULL_TXT
    if "md" in aggregates and full.is_file():
        shutil.move(str(full), str(md_target))
        _point_llms_txt_at(html_dir / "llms.txt", LLMS_FULL_TXT, md_target.name)
        written["md"] = md_target
    if "pdf" in aggregates and md_target.is_file():
        pdf = markdown_to_pdf(md_target, html_dir / f"{package_name}.pdf")
        if pdf is not None:
            written["pdf"] = pdf
    return written


def markdown_to_pdf(md_path: Path, pdf_path: Path) -> Path | None:
    """Render a Markdown file to PDF, without LaTeX.

    Tries, in order: Playwright (Chromium print-to-PDF, best fidelity) and
    WeasyPrint. Returns ``None``, with a printed notice, when neither is installed.
    """
    html = _markdown_to_html(md_path)
    for renderer in (_pdf_via_playwright, _pdf_via_weasyprint):
        try:
            renderer(html, pdf_path)
            return pdf_path
        except ImportError:
            continue
    print(
        f"Skipping {pdf_path.name}: no PDF renderer installed. "
        "Install one with `pip install playwright && playwright install chromium` "
        "or `pip install weasyprint`."
    )
    return None


def _markdown_to_html(md_path: Path) -> str:
    try:
        import markdown_it  # noqa: F401  (a myst-parser dependency)
        from markdown_it import MarkdownIt

        body = (
            MarkdownIt("commonmark", {"html": False})
            .enable("table")
            .render(md_path.read_text(encoding="utf-8"))
        )
    except ImportError:
        body = f"<pre>{md_path.read_text(encoding='utf-8')}</pre>"
    return (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "body{font-family:system-ui,sans-serif;max-width:52em;margin:2em auto;line-height:1.45}"
        "pre,code{font-family:ui-monospace,monospace;font-size:.9em}"
        "pre{background:#f4f4f4;padding:.6em;overflow-x:auto;white-space:pre-wrap}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.2em .5em}"
        f"</style><title>{md_path.stem}</title></head><body>{body}</body></html>"
    )


def _pdf_via_playwright(html: str, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=str(pdf_path), format="A4", print_background=True)
        browser.close()


def _pdf_via_weasyprint(html: str, pdf_path: Path) -> None:
    from weasyprint import HTML

    HTML(string=html).write_pdf(str(pdf_path))


def _point_llms_txt_at(llms_txt: Path, old_name: str, new_name: str) -> None:
    if llms_txt.is_file():
        text = llms_txt.read_text(encoding="utf-8")
        llms_txt.write_text(text.replace(old_name, new_name), encoding="utf-8")
