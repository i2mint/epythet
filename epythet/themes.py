"""Theme registry, deterministic theme choice, and the OKLCH accent palette.

epythet exposes three semantic knobs (``theme``, ``accent``, ``mode``) and a
verbatim ``theme_options`` passthrough. This module translates the three knobs
into each theme's own vocabulary, so a project never needs to know that furo
wants ``light_css_variables`` while shibuya wants a Radix colour *name* and
pydata wants a CSS variable in a stylesheet.

Themes are chosen from the curated registry :data:`THEMES`. ``theme = "auto"``
(the default) hashes the package name into :data:`AUTO_POOL`, so the fleet gets
variety while every package keeps the same look across rebuilds. A name that is
not in the registry is passed straight to Sphinx as ``html_theme``.

The accent colour, when not configured, is derived from the package name in
OKLCH with fixed lightness and chroma, so any hue clears WCAG AA against white
(light mode) and AAA against a dark background. Same name, same colour, forever;
change :data:`ACCENT_SALT` to reshuffle the whole fleet.

>>> accent_for("dol") == accent_for("dol")
True
>>> light, dark = accent_for("dol")
>>> light.startswith("#") and len(light) == 7
True
>>> choose_theme("dol", "furo")
'furo'
>>> choose_theme("dol", "auto") in AUTO_POOL
True
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Callable

# --------------------------------------------------------------------------
# OKLCH accent
# --------------------------------------------------------------------------

#: Changing the salt reshuffles every derived hue in the fleet at once.
ACCENT_SALT = "epythet-accent-v1"
#: OKLCH lightness for the light-mode accent (>= 6.2:1 on white at C=0.13).
LIGHT_L = 0.46
#: OKLCH lightness for the dark-mode accent (>= 8.6:1 on #131415 at C=0.13).
DARK_L = 0.78
#: OKLCH chroma for both modes.
ACCENT_C = 0.13


def hue_for(name: str, *, salt: str = ACCENT_SALT) -> int:
    """A stable hue in ``[0, 360)`` for a package name.

    >>> 0 <= hue_for("dol") < 360
    True
    >>> hue_for("dol") == hue_for("dol")
    True
    """
    digest = hashlib.blake2s(f"{salt}:{name}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % 360


def accent_for(name: str) -> tuple[str, str]:
    """``(light_hex, dark_hex)`` accents for a package name: same hue, per-mode lightness."""
    h = hue_for(name)
    return oklch_to_hex(LIGHT_L, ACCENT_C, h), oklch_to_hex(DARK_L, ACCENT_C, h)


def oklch_to_hex(L: float, C: float, h: float) -> str:
    """Convert an OKLCH colour to an sRGB hex string (gamut-clipped).

    >>> oklch_to_hex(0, 0, 0)
    '#000000'
    >>> oklch_to_hex(1, 0, 0)
    '#ffffff'
    """
    a = C * math.cos(math.radians(h))
    b = C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_**3, m_**3, s_**3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return "#" + "".join(f"{_gamma_byte(c):02x}" for c in (r, g, bl))


def _gamma_byte(c: float) -> int:
    c = min(1.0, max(0.0, c))
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(min(1.0, max(0.0, c)) * 255)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """``'#3661ac'`` to ``(54, 97, 172)``.

    >>> hex_to_rgb("#ffffff")
    (255, 255, 255)
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2 contrast ratio between two colours.

    >>> round(contrast_ratio("#000000", "#ffffff"), 1)
    21.0
    """

    def luminance(hex_color):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

        r, g, b = (channel(v) for v in hex_to_rgb(hex_color))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    la, lb = luminance(hex_a), luminance(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# HSL hues of the Radix step-9 colours shibuya ships (same hue space as _hue_of_hex).
_RADIX_HUES = {
    "tomato": 10, "orange": 23, "amber": 42, "yellow": 53, "lime": 81,
    "grass": 131, "green": 151, "jade": 164, "teal": 173, "cyan": 191,
    "blue": 206, "indigo": 226, "iris": 240, "violet": 252, "purple": 272,
    "plum": 292, "pink": 322, "crimson": 336, "ruby": 348, "red": 358,
}  # fmt: skip


def nearest_radix_name(hue: float) -> str:
    """The Radix colour whose hue is closest (circularly) to ``hue``.

    >>> nearest_radix_name(206)
    'blue'
    >>> nearest_radix_name(359)
    'red'
    """
    return min(
        _RADIX_HUES,
        key=lambda n: min(abs(hue - _RADIX_HUES[n]), 360 - abs(hue - _RADIX_HUES[n])),
    )


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ThemeSpec:
    """How one Sphinx theme expresses epythet's three semantic knobs.

    ``options`` are the "beautiful default" ``html_theme_options``; strings may
    contain ``{repo_url}``, ``{description}`` and ``{docs_dir}`` placeholders.
    ``accent`` maps ``(light_hex, dark_hex)`` to extra theme options and ``mode``
    maps ``"auto" | "light" | "dark"`` likewise. ``css`` returns stylesheet text
    for themes whose colours are CSS variables rather than options. ``context``
    maps the mode to ``html_context`` entries.
    """

    html_theme: str
    pip_name: str
    options: dict[str, Any] = field(default_factory=dict)
    accent: Callable[[str, str], dict[str, Any]] = lambda light, dark: {}
    mode: Callable[[str], dict[str, Any]] = lambda m: {}
    css: Callable[[str, str], str] = lambda light, dark: ""
    context: Callable[[str], dict[str, Any]] = lambda m: {}


def _furo_accent(light, dark):
    return {
        "light_css_variables": {
            "color-brand-primary": light,
            "color-brand-content": light,
        },
        "dark_css_variables": {
            "color-brand-primary": dark,
            "color-brand-content": dark,
        },
    }


def _css_variables(selector_light, selector_dark, var_names):
    def css(light, dark):
        light_vars = "".join(f"  {v}: {light};\n" for v in var_names)
        dark_vars = "".join(f"  {v}: {dark};\n" for v in var_names)
        return (
            f"{selector_light} {{\n{light_vars}}}\n{selector_dark} {{\n{dark_vars}}}\n"
        )

    return css


THEMES: dict[str, ThemeSpec] = {
    "furo": ThemeSpec(
        html_theme="furo",
        pip_name="furo",
        options={
            "navigation_with_keys": True,
            "top_of_page_buttons": ["view", "edit"],
            "source_repository": "{repo_url}",
            "source_branch": "master",
            "source_directory": "{docs_dir}/",
        },
        accent=_furo_accent,
    ),
    "shibuya": ThemeSpec(
        html_theme="shibuya",
        pip_name="shibuya",
        options={
            "dark_code": True,
            "github_url": "{repo_url}",
            "page_layout": "default",
        },
        accent=lambda light, dark: {
            "accent_color": nearest_radix_name(_hue_of_hex(light))
        },
        mode=lambda m: {"color_mode": m},
    ),
    "pydata_sphinx_theme": ThemeSpec(
        html_theme="pydata_sphinx_theme",
        pip_name="pydata-sphinx-theme",
        options={
            "github_url": "{repo_url}",
            "navigation_depth": 3,
            "show_nav_level": 1,
            "back_to_top_button": True,
            "pygments_light_style": "a11y-high-contrast-light",
            "pygments_dark_style": "a11y-high-contrast-dark",
        },
        css=_css_variables(
            'html[data-theme="light"]',
            'html[data-theme="dark"]',
            ["--pst-color-primary"],
        ),
        context=lambda m: {"default_mode": m},
    ),
    "sphinxawesome_theme": ThemeSpec(
        html_theme="sphinxawesome_theme",
        pip_name="sphinxawesome-theme",
        options={
            "show_breadcrumbs": True,
            "awesome_headerlinks": True,
            "awesome_external_links": True,
            "main_nav_links": {"GitHub": "{repo_url}"},
        },
        css=_css_variables(":root", "html.dark", ["--color-brand", "--color-accent"]),
    ),
    "sphinx_book_theme": ThemeSpec(
        html_theme="sphinx_book_theme",
        pip_name="sphinx-book-theme",
        options={
            "repository_url": "{repo_url}",
            "use_repository_button": True,
            "use_issues_button": True,
            "show_navbar_depth": 1,
        },
        css=_css_variables(
            'html[data-theme="light"]',
            'html[data-theme="dark"]',
            ["--pst-color-primary"],
        ),
        context=lambda m: {"default_mode": m},
    ),
    "alabaster": ThemeSpec(
        html_theme="alabaster",
        pip_name="alabaster",
        options={"github_button": True, "description": "{description}"},
        css=_css_variables(":root", ":root", []),
    ),
    "sphinx_rtd_theme": ThemeSpec(
        html_theme="sphinx_rtd_theme",
        pip_name="sphinx-rtd-theme",
        options={"navigation_depth": 4, "collapse_navigation": False},
    ),
}

#: Aliases accepted in ``[tool.epythet] theme`` for registry entries.
THEME_ALIASES = {
    "pydata": "pydata_sphinx_theme",
    "pydata-sphinx-theme": "pydata_sphinx_theme",
    "sphinxawesome": "sphinxawesome_theme",
    "sphinxawesome-theme": "sphinxawesome_theme",
    "awesome": "sphinxawesome_theme",
    "book": "sphinx_book_theme",
    "sphinx-book-theme": "sphinx_book_theme",
    "rtd": "sphinx_rtd_theme",
    "sphinx-rtd-theme": "sphinx_rtd_theme",
}

#: What ``theme = "auto"`` chooses from: the modern, brand-neutral themes.
#: Order matters (it is what the hash indexes); append, never reorder.
AUTO_POOL: tuple[str, ...] = (
    "furo",
    "shibuya",
    "pydata_sphinx_theme",
    "sphinxawesome_theme",
)

#: Themes epythet depends on and therefore can always use.
BUNDLED_THEMES = AUTO_POOL


def choose_theme(package_name: str, theme: str = "auto") -> str:
    """Resolve the configured ``theme`` to a registry key or a raw theme name.

    >>> choose_theme("x", "pydata")
    'pydata_sphinx_theme'
    >>> choose_theme("x", "my_custom_theme")
    'my_custom_theme'
    """
    if theme == "auto":
        digest = hashlib.blake2s(
            f"{ACCENT_SALT}:theme:{package_name}".encode(), digest_size=8
        ).digest()
        return AUTO_POOL[int.from_bytes(digest, "big") % len(AUTO_POOL)]
    return THEME_ALIASES.get(theme, theme)


def theme_spec(name: str) -> ThemeSpec:
    """The registry entry for ``name``, or a bare passthrough spec for unknown themes."""
    return THEMES.get(name, ThemeSpec(html_theme=name, pip_name=name))


@dataclass(frozen=True)
class ResolvedTheme:
    """Everything the Sphinx configuration needs for the chosen theme."""

    html_theme: str
    html_theme_options: dict[str, Any]
    html_context: dict[str, Any]
    css: str
    accent_light: str
    accent_dark: str


def resolve_theme(
    package_name: str,
    *,
    theme: str = "auto",
    accent: str = "",
    mode: str = "auto",
    theme_options: dict[str, Any] | None = None,
    repo_url: str = "",
    description: str = "",
    docs_dir: str = "docsrc",
) -> ResolvedTheme:
    """Translate the semantic knobs into a concrete Sphinx theme configuration.

    ``theme_options`` is merged last and wins over every default. Options whose
    placeholder could not be filled (no ``repo_url``) are dropped rather than
    rendered as an empty string.

    >>> rt = resolve_theme("dol", theme="furo", accent="#3661ac")
    >>> rt.html_theme, rt.html_theme_options["light_css_variables"]["color-brand-primary"]
    ('furo', '#3661ac')
    >>> resolve_theme("dol", theme="furo", theme_options={"sidebar_hide_name": True}
    ...     ).html_theme_options["sidebar_hide_name"]
    True
    """
    name = choose_theme(package_name, theme)
    spec = theme_spec(name)
    if accent:
        light = dark = accent
    else:
        light, dark = accent_for(package_name)
    substitutions = {
        "repo_url": repo_url,
        "description": description,
        "docs_dir": docs_dir,
    }
    options = _fill_placeholders(spec.options, substitutions)
    options.update(spec.accent(light, dark))
    if mode != "auto":
        options.update(spec.mode(mode))
    options.update(theme_options or {})
    context = spec.context(mode) if mode != "auto" else {}
    return ResolvedTheme(
        html_theme=spec.html_theme,
        html_theme_options=options,
        html_context=context,
        css=spec.css(light, dark),
        accent_light=light,
        accent_dark=dark,
    )


def _fill_placeholders(
    options: dict[str, Any], values: dict[str, str]
) -> dict[str, Any]:
    """Substitute ``{repo_url}``-style placeholders, dropping entries left empty."""
    out: dict[str, Any] = {}
    for key, value in options.items():
        filled = _fill_value(value, values)
        if filled is not None:
            out[key] = filled
    return out


def _fill_value(value: Any, values: dict[str, str]) -> Any:
    if isinstance(value, str) and "{" in value:
        filled = value.format(**values)
        # A placeholder that resolved to nothing leaves e.g. "/" behind: drop it.
        stripped = filled.strip("/")
        return filled if stripped and stripped != value.strip("/{}") else None
    if isinstance(value, dict):
        filled = _fill_placeholders(value, values)
        return filled or None
    return value


def _hue_of_hex(hex_color: str) -> float:
    """Approximate hue (degrees) of an sRGB hex colour, via HSL. Good enough for naming."""
    r, g, b = (v / 255 for v in hex_to_rgb(hex_color))
    hi, lo = max(r, g, b), min(r, g, b)
    if hi == lo:
        return 0.0
    d = hi - lo
    if hi == r:
        h = ((g - b) / d) % 6
    elif hi == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return (h * 60) % 360
