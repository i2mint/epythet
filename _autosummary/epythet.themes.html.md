# epythet.themes

Theme registry, deterministic theme choice, and the OKLCH accent palette.

epythet exposes three semantic knobs (`theme`, `accent`, `mode`) and a
verbatim `theme_options` passthrough. This module translates the three knobs
into each theme’s own vocabulary, so a project never needs to know that furo
wants `light_css_variables` while shibuya wants a Radix colour *name* and
pydata wants a CSS variable in a stylesheet.

Themes are chosen from the curated registry `THEMES`. `theme = "auto"`
(the default) hashes the package name into [`AUTO_POOL`](#epythet.themes.AUTO_POOL), so the fleet gets
variety while every package keeps the same look across rebuilds. A name that is
not in the registry is passed straight to Sphinx as `html_theme`.

The accent colour, when not configured, is derived from the package name in
OKLCH with fixed lightness and chroma, so any hue clears WCAG AA against white
(light mode) and AAA against a dark background. Same name, same colour, forever;
change [`ACCENT_SALT`](#epythet.themes.ACCENT_SALT) to reshuffle the whole fleet.

```pycon
>>> accent_for("dol") == accent_for("dol")
True
>>> light, dark = accent_for("dol")
>>> light.startswith("#") and len(light) == 7
True
>>> choose_theme("dol", "furo")
'furo'
>>> choose_theme("dol", "auto") in AUTO_POOL
True
```

### Module Attributes

| [`ACCENT_SALT`](#epythet.themes.ACCENT_SALT)    | Changing the salt reshuffles every derived hue in the fleet at once.   |
|-----------------------------------------------------------------|------------------------------------------------------------------------|
| [`LIGHT_L`](#epythet.themes.LIGHT_L)        | 1 on white at C=0.13).                                                 |
| [`DARK_L`](#epythet.themes.DARK_L)         | 1 on #131415 at C=0.13).                                               |
| [`ACCENT_C`](#epythet.themes.ACCENT_C)       | OKLCH chroma for both modes.                                           |
| [`THEME_ALIASES`](#epythet.themes.THEME_ALIASES)  | Aliases accepted in `[tool.epythet] theme` for registry entries.       |
| [`AUTO_POOL`](#epythet.themes.AUTO_POOL)      | the modern, brand-neutral themes.                                      |
| [`BUNDLED_THEMES`](#epythet.themes.BUNDLED_THEMES) | Themes epythet depends on and therefore can always use.                |

### Functions

| [`accent_for`](#epythet.themes.accent_for)(name)                              | `(light_hex, dark_hex)` accents for a package name: same hue, per-mode lightness.                                       |
|------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`choose_theme`](#epythet.themes.choose_theme)(package_name[, theme])           | Resolve the configured `theme` to a registry key or a raw theme name.                                                   |
| [`contrast_ratio`](#epythet.themes.contrast_ratio)(hex_a, hex_b)                  | WCAG 2 contrast ratio between two colours.                                                                              |
| [`dark_variant`](#epythet.themes.dark_variant)(hex_color)                       | The dark-mode twin of an accent: same hue, lightness lifted to [`DARK_L`](#epythet.themes.DARK_L). |
| [`hex_to_oklch`](#epythet.themes.hex_to_oklch)(hex_color)                       | `(L, C, h)` in OKLCH for an sRGB hex colour.                                                                            |
| [`hex_to_rgb`](#epythet.themes.hex_to_rgb)(hex_color)                         | `'#3661ac'` to `(54, 97, 172)`.                                                                                         |
| [`hue_for`](#epythet.themes.hue_for)(name, \*[, salt])                     | A stable hue in `[0, 360)` for a package name.                                                                          |
| [`nearest_radix_name`](#epythet.themes.nearest_radix_name)(hue)                       | The Radix colour whose hue is closest (circularly) to `hue`.                                                            |
| [`oklch_to_hex`](#epythet.themes.oklch_to_hex)(L, C, h)                         | Convert an OKLCH colour to an sRGB hex string (gamut-clipped).                                                          |
| [`resolve_theme`](#epythet.themes.resolve_theme)(package_name, \*[, theme, ...]) | Translate the semantic knobs into a concrete Sphinx theme configuration.                                                |
| [`theme_spec`](#epythet.themes.theme_spec)(name)                              | The registry entry for `name`, or a bare passthrough spec for unknown themes.                                           |

### Classes

| [`ResolvedTheme`](#epythet.themes.ResolvedTheme)(html_theme, ...)                  | Everything the Sphinx configuration needs for the chosen theme.   |
|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| [`ThemeSpec`](#epythet.themes.ThemeSpec)(html_theme, pip_name[, options, ...]) | How one Sphinx theme expresses epythet's three semantic knobs.    |

### epythet.themes.ACCENT_C *= 0.13*

OKLCH chroma for both modes.

### epythet.themes.ACCENT_SALT *= 'epythet-accent-v1'*

Changing the salt reshuffles every derived hue in the fleet at once.

### epythet.themes.AUTO_POOL *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('furo', 'shibuya', 'pydata_sphinx_theme', 'sphinxawesome_theme')*

the modern, brand-neutral themes.
Order matters (it is what the hash indexes); append, never reorder.

* **Type:**
  What `theme = "auto"` chooses from

### epythet.themes.BUNDLED_THEMES *= ('furo', 'shibuya', 'pydata_sphinx_theme', 'sphinxawesome_theme')*

Themes epythet depends on and therefore can always use.

### epythet.themes.DARK_L *= 0.78*

1 on #131415 at C=0.13).

* **Type:**
  OKLCH lightness for the dark-mode accent (>= 8.6

### epythet.themes.LIGHT_L *= 0.46*

1 on white at C=0.13).

* **Type:**
  OKLCH lightness for the light-mode accent (>= 6.2

### *class* epythet.themes.ResolvedTheme(html_theme, html_theme_options, html_context, css, accent_light, accent_dark)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Everything the Sphinx configuration needs for the chosen theme.

### epythet.themes.THEME_ALIASES *= {'awesome': 'sphinxawesome_theme', 'book': 'sphinx_book_theme', 'pydata': 'pydata_sphinx_theme', 'pydata-sphinx-theme': 'pydata_sphinx_theme', 'rtd': 'sphinx_rtd_theme', 'sphinx-book-theme': 'sphinx_book_theme', 'sphinx-rtd-theme': 'sphinx_rtd_theme', 'sphinxawesome': 'sphinxawesome_theme', 'sphinxawesome-theme': 'sphinxawesome_theme'}*

Aliases accepted in `[tool.epythet] theme` for registry entries.

### *class* epythet.themes.ThemeSpec(html_theme, pip_name, options=<factory>, accent=<function ThemeSpec.<lambda>>, mode=<function ThemeSpec.<lambda>>, css=<function ThemeSpec.<lambda>>, context=<function ThemeSpec.<lambda>>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

How one Sphinx theme expresses epythet’s three semantic knobs.

`options` are the “beautiful default” `html_theme_options`; strings may
contain `{repo_url}`, `{description}` and `{docs_dir}` placeholders.
`accent` maps `(light_hex, dark_hex)` to extra theme options and `mode`
maps `"auto" | "light" | "dark"` likewise. `css` returns stylesheet text
for themes whose colours are CSS variables rather than options. `context`
maps the mode to `html_context` entries.

### epythet.themes.accent_for(name)

`(light_hex, dark_hex)` accents for a package name: same hue, per-mode lightness.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.themes.choose_theme(package_name, theme='auto')

Resolve the configured `theme` to a registry key or a raw theme name.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> choose_theme("x", "pydata")
'pydata_sphinx_theme'
>>> choose_theme("x", "my_custom_theme")
'my_custom_theme'
```

### epythet.themes.contrast_ratio(hex_a, hex_b)

WCAG 2 contrast ratio between two colours.

* **Return type:**
  [`float`](https://docs.python.org/3/library/functions.html#float)

```pycon
>>> round(contrast_ratio("#000000", "#ffffff"), 1)
21.0
```

### epythet.themes.dark_variant(hex_color)

The dark-mode twin of an accent: same hue, lightness lifted to [`DARK_L`](#epythet.themes.DARK_L).

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> contrast_ratio(dark_variant("#3661ac"), "#131415") > 7
True
```

### epythet.themes.hex_to_oklch(hex_color)

`(L, C, h)` in OKLCH for an sRGB hex colour.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/library/functions.html#float), [`float`](https://docs.python.org/3/library/functions.html#float), [`float`](https://docs.python.org/3/library/functions.html#float)]

```pycon
>>> L, C, h = hex_to_oklch(oklch_to_hex(0.5, 0.13, 200))
>>> round(L, 2), round(C, 2), round(h)
(0.5, 0.13, 200)
```

### epythet.themes.hex_to_rgb(hex_color)

`'#3661ac'` to `(54, 97, 172)`.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/library/functions.html#int), [`int`](https://docs.python.org/3/library/functions.html#int), [`int`](https://docs.python.org/3/library/functions.html#int)]

```pycon
>>> hex_to_rgb("#ffffff")
(255, 255, 255)
```

### epythet.themes.hue_for(name, , salt='epythet-accent-v1')

A stable hue in `[0, 360)` for a package name.

* **Return type:**
  [`int`](https://docs.python.org/3/library/functions.html#int)

```pycon
>>> 0 <= hue_for("dol") < 360
True
>>> hue_for("dol") == hue_for("dol")
True
```

### epythet.themes.nearest_radix_name(hue)

The Radix colour whose hue is closest (circularly) to `hue`.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> nearest_radix_name(206)
'blue'
>>> nearest_radix_name(359)
'red'
```

### epythet.themes.oklch_to_hex(L, C, h)

Convert an OKLCH colour to an sRGB hex string (gamut-clipped).

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> oklch_to_hex(0, 0, 0)
'#000000'
>>> oklch_to_hex(1, 0, 0)
'#ffffff'
```

### epythet.themes.resolve_theme(package_name, , theme='auto', accent='', mode='auto', theme_options=None, repo_url='', description='', docs_dir='docsrc')

Translate the semantic knobs into a concrete Sphinx theme configuration.

`theme_options` is merged last and wins over every default. Options whose
placeholder could not be filled (no `repo_url`) are dropped rather than
rendered as an empty string.

* **Return type:**
  [`ResolvedTheme`](#epythet.themes.ResolvedTheme)

```pycon
>>> rt = resolve_theme("dol", theme="furo", accent="#3661ac")
>>> rt.html_theme, rt.html_theme_options["light_css_variables"]["color-brand-primary"]
('furo', '#3661ac')
>>> resolve_theme("dol", theme="furo", theme_options={"sidebar_hide_name": True}
...     ).html_theme_options["sidebar_hide_name"]
True
```

### epythet.themes.theme_spec(name)

The registry entry for `name`, or a bare passthrough spec for unknown themes.

* **Return type:**
  [`ThemeSpec`](#epythet.themes.ThemeSpec)
