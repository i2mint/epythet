# epythet.agent_outputs

Agent-facing outputs: `llms.txt`, Markdown twins, link relations, aggregates.

Humans get the rendered HTML. Agents get, from the same build:

- `llms.txt`: an index of every page with a one-line description, and
  `<page>.md` twins of every page, both produced by the `sphinx_llm.txt`
  extension (which drives a second, Markdown build).
- `<link rel="alternate" type="text/markdown">` and
  `<link rel="describedby" href="llms.txt">` in every HTML page’s `<head>`,
  the llms.txt discovery contract. The plugin does not add these; the
  `html-page-context` hook here does.
- `objects.inv`: the Sphinx inventory, already a machine-readable symbol index.
- Aggregates: one flat document with the whole site, at a stable URL at the
  site root: `<package>.md` (from the Markdown build’s concatenation) and,
  when a renderer is available, `<package>.pdf`. See [`write_aggregates()`](#epythet.agent_outputs.write_aggregates).

The `aggregates` seam is the `aggregates` key of the configuration:
`["md"]` by default, `["md", "pdf"]` when a PDF is wanted.

### Module Attributes

| [`LLMS_FULL_TXT`](#epythet.agent_outputs.LLMS_FULL_TXT)   | File the Markdown build writes when `llms_txt_full_build` is on.   |
|------------------------------------------------------------------|--------------------------------------------------------------------|

### Functions

| [`inject_link_relations`](#epythet.agent_outputs.inject_link_relations)(app, pagename, ...)    | `html-page-context` hook: advertise the Markdown twin and `llms.txt`.           |
|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`inject_link_relations_into_site`](#epythet.agent_outputs.inject_link_relations_into_site)(html_dir)    | Add the link relations to every built page that has a Markdown twin but no tag. |
| [`link_relation_tags`](#epythet.agent_outputs.link_relation_tags)(pagename)                 | The two `<link>` tags for a page, with hrefs relative to that page.             |
| [`markdown_to_pdf`](#epythet.agent_outputs.markdown_to_pdf)(md_path, pdf_path)           | Render a Markdown file to PDF, without LaTeX.                                   |
| [`sphinx_settings`](#epythet.agent_outputs.sphinx_settings)(\*[, description])           | The Sphinx configuration values for the agent outputs.                          |
| [`write_aggregates`](#epythet.agent_outputs.write_aggregates)(html_dir, \*, package_name) | Produce the flat single-document twins at the root of a built site.             |

### epythet.agent_outputs.LLMS_FULL_TXT *= 'llms-full.txt'*

File the Markdown build writes when `llms_txt_full_build` is on.

### epythet.agent_outputs.inject_link_relations(app, pagename, templatename, context, doctree)

`html-page-context` hook: advertise the Markdown twin and `llms.txt`.

### epythet.agent_outputs.inject_link_relations_into_site(html_dir)

Add the link relations to every built page that has a Markdown twin but no tag.

Themes that do not render Sphinx’s `metatags` block (shibuya) get nothing
from the `html-page-context` hook; this post-build pass covers them.
Returns the number of files changed.

* **Return type:**
  [`int`](https://docs.python.org/3/library/functions.html#int)

### epythet.agent_outputs.link_relation_tags(pagename)

The two `<link>` tags for a page, with hrefs relative to that page.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> print(link_relation_tags("_autosummary/pkg.mod"))

<link rel="alternate" type="text/markdown" href="pkg.mod.html.md">
<link rel="describedby" href="../llms.txt" type="text/markdown">
```

### epythet.agent_outputs.markdown_to_pdf(md_path, pdf_path)

Render a Markdown file to PDF, without LaTeX.

Tries, in order: Playwright (Chromium print-to-PDF, best fidelity) and
WeasyPrint. Returns `None`, with a printed notice, when neither is installed.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.agent_outputs.sphinx_settings(, description='')

The Sphinx configuration values for the agent outputs.

`llms_txt_full_build` stays on because its concatenation is the `<pkg>.md`
aggregate; [`write_aggregates()`](#epythet.agent_outputs.write_aggregates) renames it after the build.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

### epythet.agent_outputs.write_aggregates(html_dir, , package_name, aggregates=('md',))

Produce the flat single-document twins at the root of a built site.

* **Parameters:**
  * **html_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – the built site (`docsrc/_build/html`)
  * **package_name** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – names the files: `<package_name>.md` / `.pdf`
  * **aggregates** ([`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`...`](https://docs.python.org/3/library/constants.html#Ellipsis)]) – which of `"md"`, `"pdf"` to produce
* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]
* **Returns:**
  the files written, keyed by kind

The `.md` aggregate is the Markdown build’s `llms-full.txt` renamed, and
`llms.txt` is rewritten to point at it. The `.pdf` aggregate is rendered
from the `.md` one by [`markdown_to_pdf()`](#epythet.agent_outputs.markdown_to_pdf), which needs an optional
renderer; when none is installed the PDF is skipped with a notice.
