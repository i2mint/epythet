"""Generated Sphinx settings and the theme registry."""

from pathlib import Path

from epythet.config import DocsConfig
from epythet.confgen import api_toctree_entry, sphinx_settings
from epythet.themes import (
    AUTO_POOL,
    THEMES,
    accent_for,
    choose_theme,
    contrast_ratio,
    oklch_to_hex,
    resolve_theme,
)


def _cfg(**kw):
    # /tmp/proj/proj does not import, so "auto" would resolve to autoapi here;
    # these tests pin the generator (resolution is covered in test_config.py).
    kw.setdefault("api_generator", "autosummary")
    return DocsConfig(project_dir="/tmp/proj", name="proj", package_dir="proj", **kw)


def test_defaults_generate_autosummary_furo_class_site():
    s = sphinx_settings(_cfg(theme="furo"))
    assert s["html_theme"] == "furo"
    assert "sphinx.ext.autosummary" in s["extensions"]
    assert "sphinx.ext.napoleon" in s["extensions"]
    assert "myst_parser" in s["extensions"]
    assert "epythet.sphinx_ext" in s["extensions"]
    assert "sphinx_llm.txt" in s["extensions"]
    assert s["default_role"] == "code"
    assert s["autodoc_typehints"] == "description"
    assert s["napoleon_preprocess_types"] is False
    assert s["myst_fence_as_directive"] == ["mermaid"]
    assert "alert" in s["myst_enable_extensions"]
    assert s["html_show_copyright"] is False
    assert s["llms_txt_full_build"] is True
    assert api_toctree_entry(_cfg()) == "api"


def test_dropped_dependencies_are_gone():
    s = sphinx_settings(_cfg())
    assert "sphinx_toggleprompt" not in s["extensions"]
    assert "toggleprompt_offset_right" not in s
    assert not any("commonmark" in e for e in s["extensions"])


def test_autoapi_generator():
    s = sphinx_settings(_cfg(api_generator="autoapi", ignore=["tests/", "scrap/"]))
    assert "autoapi.extension" in s["extensions"]
    assert "sphinx.ext.autosummary" not in s["extensions"]
    assert s["autoapi_dirs"] == [str(Path("/tmp/proj/proj").absolute())]
    assert s["autoapi_ignore"] == ["*tests/*", "*scrap/*", "*__main__*"]
    assert "imported-members" not in s["autoapi_options"]
    assert api_toctree_entry(_cfg(api_generator="autoapi")) == "api/index"


def test_autosummary_ignore_becomes_exclude_patterns():
    s = sphinx_settings(_cfg(ignore=["tests/", "scrap/"]))
    assert "_autosummary/*tests*" in s["exclude_patterns"]
    assert "_build" in s["exclude_patterns"]


def test_agent_outputs_off():
    s = sphinx_settings(_cfg(agent_outputs=False))
    assert "sphinx_llm.txt" not in s["extensions"]
    assert s["epythet_agent_outputs"] is False


def test_copyright_and_display_name():
    s = sphinx_settings(_cfg(copyright="2026, Jane", display_name="Proj!"))
    assert s["copyright"] == "2026, Jane"
    assert s["html_show_copyright"] is True
    assert s["html_title"] == "Proj!"


def test_theme_options_passthrough_wins():
    s = sphinx_settings(
        _cfg(theme="furo", theme_options={"navigation_with_keys": False})
    )
    assert s["html_theme_options"]["navigation_with_keys"] is False


def test_repo_url_reaches_theme_options_and_is_dropped_when_empty():
    s = sphinx_settings(_cfg(theme="shibuya", repo_url="https://github.com/org/proj"))
    assert s["html_theme_options"]["github_url"] == "https://github.com/org/proj"
    no_repo = sphinx_settings(_cfg(theme="shibuya"))["html_theme_options"]
    assert "github_url" not in no_repo
    furo = sphinx_settings(_cfg(theme="furo", repo_url="https://github.com/org/proj"))
    assert (
        "source_repository" not in furo["html_theme_options"]
    )  # generated pages would 404


# -- themes -----------------------------------------------------------------


def test_auto_theme_is_deterministic_and_in_the_pool():
    assert choose_theme("dol") == choose_theme("dol")
    assert choose_theme("dol") in AUTO_POOL
    assert {choose_theme(n) for n in ("dol", "i2", "creek", "meshed", "wads")} > {
        "furo"
    }


def test_explicit_theme_and_aliases():
    assert choose_theme("x", "furo") == "furo"
    assert choose_theme("x", "pydata") == "pydata_sphinx_theme"
    assert choose_theme("x", "some_custom_theme") == "some_custom_theme"
    assert (
        resolve_theme("x", theme="some_custom_theme").html_theme == "some_custom_theme"
    )


def test_accent_is_deterministic_and_accessible():
    light, dark = accent_for("dol")
    assert (light, dark) == accent_for("dol")
    assert contrast_ratio(light, "#ffffff") >= 4.5
    assert contrast_ratio(dark, "#131415") >= 7


def test_accent_floor_holds_for_every_hue():
    from epythet.themes import ACCENT_C, DARK_L, LIGHT_L

    assert (
        min(
            contrast_ratio(oklch_to_hex(LIGHT_L, ACCENT_C, h), "#ffffff")
            for h in range(360)
        )
        >= 6
    )
    assert (
        min(
            contrast_ratio(oklch_to_hex(DARK_L, ACCENT_C, h), "#131415")
            for h in range(360)
        )
        >= 8
    )


def test_accent_override_and_mode_per_theme():
    furo = resolve_theme("x", theme="furo", accent="#3661ac")
    assert (
        furo.html_theme_options["light_css_variables"]["color-brand-primary"]
        == "#3661ac"
    )
    dark = furo.html_theme_options["dark_css_variables"]["color-brand-primary"]
    assert dark != "#3661ac" and contrast_ratio(dark, "#131415") >= 7
    shibuya = resolve_theme("x", theme="shibuya", accent="#3661ac", mode="dark")
    assert shibuya.html_theme_options["accent_color"] == "indigo"
    assert shibuya.html_theme_options["color_mode"] == "dark"
    pydata = resolve_theme(
        "x", theme="pydata_sphinx_theme", accent="#3661ac", mode="light"
    )
    assert "--pst-color-primary: #3661ac" in pydata.css
    assert pydata.html_context == {"default_mode": "light"}


def test_css_file_only_when_theme_needs_it():
    assert sphinx_settings(_cfg(theme="furo"))["html_css_files"] == []
    assert sphinx_settings(_cfg(theme="alabaster"))["html_css_files"] == []
    assert sphinx_settings(_cfg(theme="pydata"))["html_css_files"] == ["epythet.css"]
