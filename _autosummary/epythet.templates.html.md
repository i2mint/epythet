# epythet.templates

Text templates for the generated `docsrc` files.

Only two files are generated: the `conf.py` shim and the `index.md` landing
page. Everything else (the API tree, the agent twins) is produced by Sphinx
extensions at build time.

### Module Attributes

| [`CONF_SHIM_MARKER`](#epythet.templates.CONF_SHIM_MARKER)         | Marker line present in every conf.py epythet generated (v2), used to decide whether an existing file may be overwritten.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|---------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`LEGACY_CONF_MARKER`](#epythet.templates.LEGACY_CONF_MARKER)       | The old (0.1.x) template's signature line, also safe to overwrite.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| [`INDEX_MARKER`](#epythet.templates.INDEX_MARKER)             | Marker in the generated index.md, used to decide whether to overwrite it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| [`aggregates_block`](#epythet.templates.aggregates_block)         | Footer of the landing page pointing at the single-document twins.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| [`LEGACY_DOCSRC_GITIGNORES`](#epythet.templates.LEGACY_DOCSRC_GITIGNORES) | What 0.1.x wrote to docsrc/.gitignore; safe to replace.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| [`autosummary_module_rst`](#epythet.templates.autosummary_module_rst)   | autosummary's stock `module.rst` (Sphinx 9) with two changes to the `modules` block: (1) the recursion runs over `all_modules` (every submodule, minus `_`-prefixed ones unless `__all__` names them) rather than `modules`, because with `autosummary_ignore_module_all = False` a package whose `__init__` declares an `__all__` of *objects* would otherwise get no submodule pages at all (a third of the fleet declares one); (2) submodules matching the ignore fragments are left out of the recursion, so no stub is generated (and no second import attempted) for tests/, scrap/, examples/. |

### epythet.templates.CONF_SHIM_MARKER *= 'from epythet.sphinx_conf import \*'*

Marker line present in every conf.py epythet generated (v2), used to decide
whether an existing file may be overwritten.

### epythet.templates.INDEX_MARKER *= '<!-- generated by epythet -->'*

Marker in the generated index.md, used to decide whether to overwrite it.

### epythet.templates.LEGACY_CONF_MARKER *= 'from epythet.config_parser import parse_config'*

The old (0.1.x) template’s signature line, also safe to overwrite.

### epythet.templates.LEGACY_DOCSRC_GITIGNORES *= ('_build/', '_build')*

What 0.1.x wrote to docsrc/.gitignore; safe to replace.

### epythet.templates.aggregates_block *= '<p class="epythet-aggregates">This documentation as a single file: {links}.</p>\\n'*

Footer of the landing page pointing at the single-document twins. Raw HTML,
because MyST would read a relative `.md` link as a (missing) page reference.

### epythet.templates.autosummary_module_rst *= '{{{{ fullname | escape | underline}}}}\\n\\n.. automodule:: {{{{ fullname }}}}\\n\\n   {{% block attributes %}}\\n   {{%- if attributes %}}\\n   .. rubric:: {{{{ \_(\\'Module Attributes\\') }}}}\\n\\n   .. autosummary::\\n   {{% for item in attributes %}}\\n      {{{{ item }}}}\\n   {{%- endfor %}}\\n   {{% endif %}}\\n   {{%- endblock %}}\\n\\n   {{%- block functions %}}\\n   {{%- if functions %}}\\n   .. rubric:: {{{{ \_(\\'Functions\\') }}}}\\n\\n   .. autosummary::\\n   {{% for item in functions %}}\\n      {{{{ item }}}}\\n   {{%- endfor %}}\\n   {{% endif %}}\\n   {{%- endblock %}}\\n\\n   {{%- block classes %}}\\n   {{%- if classes %}}\\n   .. rubric:: {{{{ \_(\\'Classes\\') }}}}\\n\\n   .. autosummary::\\n   {{% for item in classes %}}\\n      {{{{ item }}}}\\n   {{%- endfor %}}\\n   {{% endif %}}\\n   {{%- endblock %}}\\n\\n   {{%- block exceptions %}}\\n   {{%- if exceptions %}}\\n   .. rubric:: {{{{ \_(\\'Exceptions\\') }}}}\\n\\n   .. autosummary::\\n   {{% for item in exceptions %}}\\n      {{{{ item }}}}\\n   {{%- endfor %}}\\n   {{% endif %}}\\n   {{%- endblock %}}\\n\\n{{%- block modules %}}\\n{{%- set ignored = {ignored_fragments} %}}\\n{{%- set ns = namespace(kept=[]) %}}\\n{{%- for item in all_modules %}}\\n{{%- if (item in modules or not item.startswith(\\'_\\')) and not (ignored | select("in", \\'.\\' ~ item ~ \\'.\\') | list) %}}\\n{{%- set ns.kept = ns.kept + [item] %}}\\n{{%- endif %}}\\n{{%- endfor %}}\\n{{%- if ns.kept %}}\\n.. rubric:: Modules\\n\\n.. autosummary::\\n   :toctree:\\n   :recursive:\\n{{% for item in ns.kept %}}\\n   {{{{ item }}}}\\n{{%- endfor %}}\\n{{% endif %}}\\n{{%- endblock %}}\\n'*

autosummary’s stock `module.rst` (Sphinx 9) with two changes to the
`modules` block: (1) the recursion runs over `all_modules` (every
submodule, minus `_`-prefixed ones unless `__all__` names them) rather
than `modules`,
because with `autosummary_ignore_module_all = False` a package whose
`__init__` declares an `__all__` of *objects* would otherwise get no
submodule pages at all (a third of the fleet declares one); (2) submodules
matching the ignore fragments are left out of the recursion, so no stub is
generated (and no second import attempted) for tests/, scrap/, examples/.
