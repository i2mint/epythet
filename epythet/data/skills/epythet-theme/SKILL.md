---
name: epythet-theme
description: >-
  Choose and parametrize the Sphinx theme of an epythet documentation site:
  the curated pool (furo, shibuya, pydata-sphinx-theme, sphinxawesome-theme,
  sphinx-book-theme, alabaster, sphinx_rtd_theme), rules of thumb for picking
  one, the `theme` / `accent` / `mode` / `theme_options` keys, the derived OKLCH
  accent colour, and where to browse themes. Use when asked to change, choose
  or improve a docs theme, set a brand colour, force light or dark mode, why
  the docs look dated, or "make the docs look like X".
license: Apache-2.0
metadata:
  audience: users
---

# epythet-theme: choose and parametrize a theme

epythet exposes three semantic knobs and a passthrough. Write them in `pyproject.toml`; never hand-edit `docsrc/conf.py` (epythet regenerates it).

```toml
[tool.epythet]
theme = "auto"       # default; or "furo" | "shibuya" | "pydata" | "sphinxawesome" | "book" | "alabaster" | "rtd" | any installed theme
accent = "#3661ac"   # optional brand colour; default: derived from the package name
mode = "auto"        # "auto" | "light" | "dark" (where the theme can force it)

[tool.epythet.theme_options]   # verbatim html_theme_options; always wins over epythet's defaults
announcement = "v2 is in beta"
```

`theme = "auto"` hashes the package name into the pool (furo, shibuya, pydata-sphinx-theme, sphinxawesome-theme), so a fleet gets variety while each package keeps the same look across rebuilds. Names not in the registry are passed straight to Sphinx as `html_theme`.

## Decision procedure (ask at most two questions)

1. **What kind of package is this?** Map through the table below.
2. **Does it have a brand: a logo, a landing page, an audience beyond its maintainer?** Yes: shibuya. No: furo.

If nothing distinguishes it, do not ask a third question: use furo (or leave `auto`).

| Project kind | Theme | Why |
|---|---|---|
| Pure API library, small to medium (the default case) | **furo** | flat wide toctree, no brand, minimal chrome; "biased for smaller docsets" by design |
| Tiny utility, 5 pages or fewer | **alabaster** | 212 KB; no nested sidebar, no right TOC, no mobile drawer, so only for near-flat docs |
| Should look like your frontend work (shadcn, Tailwind) | **sphinxawesome-theme** | Tailwind + Alpine.js, shadcn tokens in the DOM; best search (Algolia DocSearch); right TOC only at 1280 px or wider |
| Data science / ML / scientific | **pydata-sphinx-theme** | reader expectation set by numpy/pandas/scipy; version switcher; the only theme with a stated WCAG position |
| Notebook-heavy / executable docs | **sphinx-book-theme** | MyST-NB styling, launch buttons, margin notes; say the maintenance-mode caveat aloud |
| CLI tool | furo, or shibuya with `page_layout = "simple"` | short, linear docs |
| Web framework, flagship, client-facing, has an opinion | **shibuya** | landing layout, Radix accent palette, "copy page for an LLM" button; most actively developed |
| Legacy site with an established readership | **sphinx_rtd_theme** | familiarity is a value; do not pick it for new work |
| Accessibility is a stated requirement | **pydata-sphinx-theme** | published WCAG 2 AA/AAA targets, automated and manual audits |

By document shape: 5 pages or fewer, alabaster or shibuya `simple`; 5 to 40 flat module pages, furo; deep hierarchy with 100+ pages, pydata (with `show_nav_level`, `navigation_depth`, `collapse_navigation`, and `sphinx-remove-toctrees` for very large API docs). Never alabaster for a nested tree.

## Hard rules

- Default to **furo** (or `auto`). It is what the small-package ecosystem converged on (pip, pytest, attrs, black, mypy).
- Never propose **sphinx-immaterial** (broken on Sphinx 9), **sphinx-material** (unmaintained since 2023), **sphinx-press-theme**, or a MkDocs migration without surfacing the ecosystem state.
- Always `mode = "auto"` unless the user asks otherwise. Never hard-default to dark: it is where contrast regressions hide. `sphinx_rtd_theme` and `alabaster` have no dark mode, which disqualifies them whenever dark mode is wanted.
- Never invent a logo. A derived accent beats a fake glyph.
- Let the accent be derived unless the user names a brand colour; then check its contrast and say so if it fails (see below).
- State the maintenance caveat of the chosen theme: furo is feature-complete and slow (one maintainer); sphinx-book-theme is in maintenance mode with a 2026 revival; pydata releases have broken downstream sites (pin it); shibuya has one maintainer; sphinxawesome is small but healthy.
- Write only `[tool.epythet]` keys, never `docsrc/conf.py`.

## The accent colour

When `accent` is unset, epythet derives one hue per package name in OKLCH at fixed lightness and chroma (L 0.46, C 0.13 in light mode; L 0.78 in dark mode), so **every possible colour clears WCAG AA against white and AAA against a dark background by construction**. Same name, same colour, forever.

An explicit `accent = "#hex"` is used as given in light mode and lifted to the dark-mode lightness for dark mode. Check a brand colour before committing to it:

```python
from epythet.themes import contrast_ratio, dark_variant
contrast_ratio("#3661ac", "#ffffff")   # >= 4.5 is WCAG AA for text
dark_variant("#3661ac")                 # what dark mode will use
```

Per theme, the accent becomes: furo `light_css_variables` / `dark_css_variables` (`color-brand-primary`, `color-brand-content`); shibuya `accent_color` (the nearest Radix colour *name*, since shibuya takes names, not hex); pydata and sphinx-book-theme `--pst-color-primary` in a generated `_static/epythet.css`; sphinxawesome `--color-brand` / `--color-accent` in the same stylesheet. You never write those yourself.

## Per-theme options worth knowing (`[tool.epythet.theme_options]`)

- **furo**: `announcement`, `sidebar_hide_name`, `light_logo` / `dark_logo`, `footer_icons`, `top_of_page_buttons`, `source_repository` / `source_branch` / `source_directory` (edit links; epythet leaves them off because API pages are generated), `navigation_with_keys` (epythet sets it on). Typos in `*_css_variables` are silently ignored: check spelling. Docs: https://pradyunsg.me/furo/customisation/
- **shibuya**: `page_layout` (`default` | `simple` | `landing`), `dark_code` (epythet sets it on), `github_url`, `nav_links`, `color_mode`. Docs: https://shibuya.lepture.com/customisation/
- **pydata-sphinx-theme**: `logo`, `announcement` (accepts a URL fetched at runtime), `switcher` + `show_version_warning_banner`, `navbar_start/center/end`, `show_nav_level`, `navigation_depth`, `search_as_you_type`, `icon_links`. Docs: https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/
- **sphinxawesome-theme**: `show_breadcrumbs`, `main_nav_links`, `awesome_external_links`, `logo_light` / `logo_dark`, `extra_header_link_icons`, Algolia DocSearch via `docsearch_*`. Docs: https://sphinxawesome.xyz/how-to/options/
- **sphinx-book-theme**: `repository_url`, `use_repository_button`, `use_issues_button`, `launch_buttons`, `show_navbar_depth`. Docs: https://sphinx-book-theme.readthedocs.io/en/stable/reference.html
- **alabaster**: `description`, `github_button`, `github_user` / `github_repo`, `fixed_sidebar`. Docs: https://alabaster.readthedocs.io/en/latest/customization.html
- **sphinx_rtd_theme**: `navigation_depth`, `collapse_navigation`, `style_nav_header_background`. Docs: https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html

## Installation

The pool themes (furo, shibuya, pydata-sphinx-theme, sphinxawesome-theme) and alabaster install with epythet. `pip install "epythet[themes]"` adds sphinx-book-theme and sphinx_rtd_theme. Any other installed theme works by name; a missing one fails the build with the theme's import error, so install it in the docs environment (for the Pages action, list it in the project's own dependencies or a `docs` extra that CI installs).

## Where to browse

- https://sphinx-themes.org/ : the gallery to use. Every theme rendered against the same kitchen-sink corpus at desktop, tablet and phone widths; curated by furo's author.
- https://themes.sphinx-doc.org/ : the official gallery, thinner and staler; a second opinion.
- Do not send users to sphinxthemes.com (a storefront).

Then the chosen theme's own docs and demo: furo https://pradyunsg.me/furo/ ; shibuya https://shibuya.lepture.com/ ; pydata https://pydata-sphinx-theme.readthedocs.io/ (kitchen sink under Examples); sphinxawesome https://sphinxawesome.xyz/ ; sphinx-book-theme https://sphinx-book-theme.readthedocs.io/ ; alabaster https://alabaster.readthedocs.io/ ; sphinx_rtd_theme https://sphinx-rtd-theme.readthedocs.io/ .

## Checking the result

```bash
epythet quickstart . --ignore tests/
open docsrc/_build/html/index.html
```

Look at the landing page, one module page, and both colour modes. The `epythet.themes` module is the registry: `choose_theme(name, "auto")` tells you what `auto` picks for a package, `resolve_theme(...)` shows the exact `html_theme_options` epythet will emit.
