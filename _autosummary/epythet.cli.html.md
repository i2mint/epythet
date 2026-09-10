# epythet.cli

Command line access to epythet.

`epythet quickstart PROJECT_DIR [--ignore ...]` is the command the
`publish-github-pages` action runs: it scaffolds `docsrc`, builds the HTML
and writes it to `PROJECT_DIR/docsrc/_build/html`.

### Module Attributes

| [`COMMANDS`](#epythet.cli.COMMANDS)        | The commands `epythet` exposes, in the order they appear in `--help`.                                                                             |
|------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`TOOL_COMMANDS`](#epythet.cli.TOOL_COMMANDS)   | The v2 source-editing and fleet commands, by their command-line name.                                                                             |
| [`LEDGER_COMMANDS`](#epythet.cli.LEDGER_COMMANDS) | maintenance of the artifact ledger.                                                                                                               |
| [`CONVENTION`](#epythet.cli.CONVENTION)      | the command modules use `from __future__ import annotations`, and `list[str]` must still become `nargs="*"` (`--ignore a b`), not a single value. |

### Functions

| [`ai_artifacts`](#epythet.cli.ai_artifacts)(project_dir, \*[, format])   | List the AI agent artifacts a project ships (skills, subagents, instruction files).   |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`check_pages`](#epythet.cli.check_pages)(repo, \*[, no_url_check])     | Diagnose GitHub Pages setup for a repo.                                               |
| [`configure_pages`](#epythet.cli.configure_pages)(repo, \*[, branch, path]) | Enable or fix GitHub Pages for a repo.                                                |
| [`epythet_cli`](#epythet.cli.epythet_cli)([argv])                       | Entry point for the `epythet` console script.                                         |
| [`mk_epythet_parser`](#epythet.cli.mk_epythet_parser)(\*\*parser_kwargs)      | The full `epythet` parser: the flat commands, the tool commands, the `ledger` group.  |
| [`quickstart`](#epythet.cli.quickstart)(project_dir, \*[, ignore])     | Scaffold docsrc and build the HTML documentation in one go.                           |

### epythet.cli.COMMANDS *= [<function make_docsrc>, <function make_autodocs>, <function make>, <function quickstart>, <function check_pages>, <function configure_pages>, <function validate>, <function ai_artifacts>]*

The commands `epythet` exposes, in the order they appear in `--help`.

### epythet.cli.CONVENTION *= Convention(naming='by_name_if_has_default', short_flags=True, hyphenate_commands=True, hyphenate_groups=False, default_in_help=True, hints_when_declared=False, resolve_hints=True, decode=<function argh_decode>, egress=<function argh_egress>)*

the command
modules use `from __future__ import annotations`, and `list[str]` must
still become `nargs="*"` (`--ignore a b`), not a single value.

* **Type:**
  cw’s argh-compatible convention, resolving string annotations

### epythet.cli.LEDGER_COMMANDS *= {'propose': <function propose_command>}*

maintenance of the artifact ledger.

* **Type:**
  `epythet ledger <command>`

### epythet.cli.TOOL_COMMANDS *= {'migrate-style': <function migrate_style_command>, 'repair': <function repair_command>, 'sweep': <function sweep_command>}*

The v2 source-editing and fleet commands, by their command-line name.

### epythet.cli.ai_artifacts(project_dir, , format='table')

List the AI agent artifacts a project ships (skills, subagents, instruction files).

Looks where agents and `gh skill` look: `<pkg>/data/skills`, `skills/`,
`.claude/skills`, `<pkg>/data/agents`, `.claude/agents`, `CLAUDE.md`,
`AGENTS.md`, `.cursor/rules`, `.codex`. The same discovery feeds the
generated “For AI agents” documentation page.

* **Parameters:**
  * **project_dir** – the project root
  * **format** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – table (human) or json

### epythet.cli.check_pages(repo, , no_url_check=False)

Diagnose GitHub Pages setup for a repo.

* **Parameters:**
  * **repo** – GitHub repo as ‘owner/repo’, or path to a local git checkout.
  * **no_url_check** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Skip checking if the docs URL actually responds.

### epythet.cli.configure_pages(repo, , branch='gh-pages', path='/')

Enable or fix GitHub Pages for a repo. Requires gh CLI or GITHUB_TOKEN.

* **Parameters:**
  * **repo** – GitHub repo as ‘owner/repo’, or path to a local git checkout.
  * **branch** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Branch to serve Pages from (default: gh-pages).
  * **path** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Folder within the branch (default: /).

### epythet.cli.epythet_cli(argv=None)

Entry point for the `epythet` console script.

### epythet.cli.mk_epythet_parser(\*\*parser_kwargs)

The full `epythet` parser: the flat commands, the tool commands, the `ledger` group.

### epythet.cli.quickstart(project_dir, , ignore=None)

Scaffold docsrc and build the HTML documentation in one go.

Equivalent to `make-docsrc` then `make html`, with `ignore` applied
to the API generator. An empty `ignore` (the action passes `--ignore`
with no values when its input is unset, or `""`) means “use the configured
default”; each value may itself be comma-separated.

* **Parameters:**
  * **project_dir** – Path to root project directory (pyproject.toml or setup.cfg)
  * **ignore** ([`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – skip file if path contains any ignore strings
