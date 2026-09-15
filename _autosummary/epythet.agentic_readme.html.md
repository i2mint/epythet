# epythet.agentic_readme

Check that a README documents a project’s agentic aspects; render and place the section.

A project that ships skills, subagents or instruction files, and whose site
publishes agent-readable documentation (`llms.txt`, `<package>.md`), should
say so in its README: that is where an agent arriving at the repository looks
first. [`check_readme()`](#epythet.agentic_readme.check_readme) reuses [`epythet.ai_artifacts.discover_artifacts()`](epythet.ai_artifacts.html.md#epythet.ai_artifacts.discover_artifacts)
to learn what exists and reads the README to see whether each kind is mentioned
(a `gh skill install` line, a skill or agent name, `CLAUDE.md`, `llms.txt`,
a heading about agents). The result is a [`ReadmeReport`](#epythet.agentic_readme.ReadmeReport): one
[`KindCheck`](#epythet.agentic_readme.KindCheck) per kind, each `ok`, `warn` or `n/a`. The check is a
heuristic: a mention counts whatever the sentence around it says.

[`render_section()`](#epythet.agentic_readme.render_section) produces the README section from the effective snippets
([`epythet.userconfig`](epythet.userconfig.html.md#module-epythet.userconfig): the user’s `agentic-readme-section.md` and
`agentic-readme-humor.md` over the packaged defaults) and the effective
[`ReadmePolicy`](epythet.userconfig.html.md#epythet.userconfig.ReadmePolicy) (the user’s `config.toml`, with a
project’s `[tool.epythet.readme]` keys on top so a committed README does not
depend on who ran the tool). [`place_section()`](#epythet.agentic_readme.place_section) puts it between two marker
comments so a later run updates it in place: before the first heading after the
title when `agentic_first` is on, at the end otherwise. The “for humans” line
links to the heading that follows the section.

```pycon
>>> readme = "# pkg\n\nTagline.\n\n# Install\n\npip install pkg\n"
>>> start, end, heading, level = place_section(readme, agentic_first=True)
>>> readme[start:end], heading.title, level
('', 'Install', 1)
>>> humans_link_for(heading)
'[Install](#install)'
```

### Module Attributes

| [`MARKER_START`](#epythet.agentic_readme.MARKER_START)      | The comments that delimit the generated section in a README (each on its own line).   |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`README_NAMES`](#epythet.agentic_readme.README_NAMES)      | README filenames, in order of preference.                                             |
| [`KINDS`](#epythet.agentic_readme.KINDS)             | The kinds a check reports on, in display order.                                       |
| [`SECTION_SNIPPET`](#epythet.agentic_readme.SECTION_SNIPPET)   | The snippet names the section is rendered from.                                       |
| [`NEUTRAL_INTRO`](#epythet.agentic_readme.NEUTRAL_INTRO)     | The opener used when `humor` is off.                                                  |
| [`MAX_BLURB`](#epythet.agentic_readme.MAX_BLURB)         | Longest blurb (first sentence of a description) shown per skill or agent.             |
| [`HEADLINE_SUFFIXES`](#epythet.agentic_readme.HEADLINE_SUFFIXES) | Skill name suffixes that make a skill the one named in the install line.              |
| [`SECTION_FIELDS`](#epythet.agentic_readme.SECTION_FIELDS)    | The fields a section snippet may use.                                                 |

### Functions

| [`ai_readme_check`](#epythet.agentic_readme.ai_readme_check)(project_dir, \*[, format, ...])    | Report whether the README documents the project's agentic aspects; draft or write the section.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`blurb`](#epythet.agentic_readme.blurb)(description, \*[, max_length])               | The first sentence of a skill or agent description, short enough for a table cell.               |
| [`check_readme`](#epythet.agentic_readme.check_readme)(project_dir, \*[, config, ...])       | Which agentic aspects the project has, and whether its README mentions each.                     |
| [`draft_section`](#epythet.agentic_readme.draft_section)(project_dir, \*[, user_config, ...]) | Render the section for a project as it would be placed: `(section, readme_text, start, end)`.    |
| [`find_readme`](#epythet.agentic_readme.find_readme)(project_dir)                           | The project's README, by the usual names (`None` when there is none).                            |
| [`github_anchor`](#epythet.agentic_readme.github_anchor)(title)                               | GitHub's anchor for a heading title.                                                             |
| [`headings_of`](#epythet.agentic_readme.headings_of)(text)                                  | Every ATX heading outside fenced code blocks.                                                    |
| [`headline_skill`](#epythet.agentic_readme.headline_skill)(skills)                             | The skill named in the install line: a `*-setup`-like one if any, else the first installable.    |
| [`humans_link_for`](#epythet.agentic_readme.humans_link_for)(heading)                           | `[Title](#anchor)` for the heading after the section, or a plain fallback.                       |
| [`instruction_text`](#epythet.agentic_readme.instruction_text)(\*[, snippets])                   | The instruction the skill hands an agent when the policy is `add`.                               |
| [`load`](#epythet.agentic_readme.load)(project_dir, \*[, config, artifacts, ...])    | Resolve a project once; each argument given is used instead of being loaded.                     |
| [`load_project`](#epythet.agentic_readme.load_project)(project_dir)                          | `(config, artifacts)` for a project; `config` is `None` for a non-Python tree.                   |
| [`marker_span`](#epythet.agentic_readme.marker_span)(text, \*[, strict])                    | The character span of the marked section (`None` when there is none).                            |
| [`place_section`](#epythet.agentic_readme.place_section)(text, \*, agentic_first)             | Where the section goes in `text`: `(start, end, next_heading, level)`.                           |
| [`read_readme`](#epythet.agentic_readme.read_readme)(path)                                  | `(text, newline)`: the README with `\n` line ends, and the style to write back.                  |
| [`render_section`](#epythet.agentic_readme.render_section)(artifacts, config, \*, policy)      | The README section for `artifacts`, from the effective snippets and `policy`.                    |
| [`splice_section`](#epythet.agentic_readme.splice_section)(text, section, \*, start, end)      | `text` with `section` in place of `text[start:end]`, blank lines kept sane.                      |
| [`write_section`](#epythet.agentic_readme.write_section)(project_dir, \*[, user_config])      | Add or update the marked section in the project's README; returns `(path, outcome)`.             |

### Classes

| [`Heading`](#epythet.agentic_readme.Heading)(line, level, title)                    | A Markdown ATX heading: its line index, level and title text.                                   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| [`KindCheck`](#epythet.agentic_readme.KindCheck)(kind, present, documented[, ...])    | One artifact kind: whether the project has it and whether the README covers it.                 |
| [`Project`](#epythet.agentic_readme.Project)(root, config, artifacts, readme, ...)  | What every entry point needs once: config, artifacts, README, effective policy.                 |
| [`ReadmeReport`](#epythet.agentic_readme.ReadmeReport)(project_dir, readme, checks, ...) | The outcome of [`check_readme()`](#epythet.agentic_readme.check_readme) for one project. |

### Exceptions

| [`SectionError`](#epythet.agentic_readme.SectionError)   | The README or a snippet is in a state the tool will not write over.   |
|-----------------------------------------------------------------|-----------------------------------------------------------------------|

### epythet.agentic_readme.HEADLINE_SUFFIXES *= ('-setup', '-quickstart', '-start')*

Skill name suffixes that make a skill the one named in the install line.

### *class* epythet.agentic_readme.Heading(line, level, title)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A Markdown ATX heading: its line index, level and title text.

### epythet.agentic_readme.KINDS *= ('skills', 'subagents', 'instruction_files', 'agent_docs', 'section')*

The kinds a check reports on, in display order.

### *class* epythet.agentic_readme.KindCheck(kind, present, documented, items=(), evidence='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One artifact kind: whether the project has it and whether the README covers it.

#### *property* status *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

`n/a` when absent from the project, else `ok` or `warn`.

### epythet.agentic_readme.MARKER_START *= '<!-- epythet:agentic-readme:start -->'*

The comments that delimit the generated section in a README (each on its own line).

### epythet.agentic_readme.MAX_BLURB *= 140*

Longest blurb (first sentence of a description) shown per skill or agent.

### epythet.agentic_readme.NEUTRAL_INTRO *= 'If you are a human'*

The opener used when `humor` is off.

### *class* epythet.agentic_readme.Project(root, config, artifacts, readme, user_config, policy, project_overrides)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What every entry point needs once: config, artifacts, README, effective policy.

### epythet.agentic_readme.README_NAMES *= ('README.md', 'readme.md', 'README.markdown', 'README.rst', 'README.txt', 'README')*

README filenames, in order of preference.

### *class* epythet.agentic_readme.ReadmeReport(project_dir, readme, checks, policy, user_config, project_overrides)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The outcome of [`check_readme()`](#epythet.agentic_readme.check_readme) for one project.

`policy` is the effective `ReadmePolicy`; `user_config` and
`project_overrides` are where it came from.

#### *property* status *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

`warn` when anything present is undocumented, else `ok`.

#### table()

The plain-text listing (the default CLI output).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### to_dict()

A JSON-ready view (`--format json`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### *property* warnings *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[KindCheck](#epythet.agentic_readme.KindCheck), ...]*

The kinds present in the project but missing from the README.

### epythet.agentic_readme.SECTION_FIELDS *= frozenset({'docs_block', 'for_humans_intro', 'heading', 'humans_link', 'instructions_block', 'marker_end', 'marker_start', 'name', 'repo_stub', 'site_url', 'skills_block', 'subagents_block'})*

The fields a section snippet may use.

### epythet.agentic_readme.SECTION_SNIPPET *= 'agentic-readme-section'*

The snippet names the section is rendered from.

### *exception* epythet.agentic_readme.SectionError

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

The README or a snippet is in a state the tool will not write over.

Raised for unpaired or repeated markers, a README that is not UTF-8 or not
Markdown, and a section snippet that fails to format or drops the markers.

### epythet.agentic_readme.ai_readme_check(project_dir, , format='table', fail_on='', draft=False, write=False)

Report whether the README documents the project’s agentic aspects; draft or write the section.

Reuses `epythet ai-artifacts` discovery (skills, subagents, instruction
files) plus the agent-readable outputs the site publishes, and looks for
each in the README: a `gh skill install` line or skill name, a subagent
name, `CLAUDE.md` / `AGENTS.md`, `llms.txt` / `<package>.md`, and a
heading about agents (or epythet’s own section markers). The effective
policy (`~/.config/epythet/config.toml` `[readme]`, overridden by the
project’s `[tool.epythet.readme]`) is part of the output so a skill can
read it. `--write` is explicit: it writes whatever the policy says.

* **Parameters:**
  * **project_dir** – the project root
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – table (human) or json
  * **fail_on** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `warn` to exit 1 when anything present is undocumented (default: exit 0)
  * **draft** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – print the README section rendered from the effective snippets and policy, without writing
  * **write** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add or update the section in `README.md` between epythet’s markers

### epythet.agentic_readme.blurb(description, , max_length=140)

The first sentence of a skill or agent description, short enough for a table cell.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> blurb("Find and fix things. Use when asked to fix.")
'find and fix things'
>>> blurb("Do the thing and then some: a, b, c, " + "and more " * 30)
'do the thing and then some'
```

### epythet.agentic_readme.check_readme(project_dir, , config=None, artifacts=None, user_config=None)

Which agentic aspects the project has, and whether its README mentions each.

* **Parameters:**
  * **config** – the [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig) (loaded when omitted)
  * **artifacts** ([`AIArtifacts`](epythet.ai_artifacts.html.md#epythet.ai_artifacts.AIArtifacts) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – discovery result (computed when omitted)
  * **user_config** ([`UserConfig`](epythet.userconfig.html.md#epythet.userconfig.UserConfig) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – the user’s policy (read from the config dir when omitted)
* **Return type:**
  [`ReadmeReport`](#epythet.agentic_readme.ReadmeReport)

### epythet.agentic_readme.draft_section(project_dir, , user_config=None, config=None, artifacts=None)

Render the section for a project as it would be placed: `(section, readme_text, start, end)`.

`readme_text` is the current README (`""` when none exists); `start`
and `end` delimit the span the section replaces.

* **Raises:**
  [**SectionError**](#epythet.agentic_readme.SectionError) – on unpaired markers, a non-UTF-8 README, or a broken snippet
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)]

### epythet.agentic_readme.find_readme(project_dir)

The project’s README, by the usual names (`None` when there is none).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### epythet.agentic_readme.github_anchor(title)

GitHub’s anchor for a heading title.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> github_anchor("For AI agents"), github_anchor("What it *fixes*: `x`")
('for-ai-agents', 'what-it-fixes-x')
>>> github_anchor("my_function and [links](https://x)")
'my_function-and-links'
```

### epythet.agentic_readme.headings_of(text)

Every ATX heading outside fenced code blocks.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Heading`](#epythet.agentic_readme.Heading)]

```pycon
>>> [h.title for h in headings_of("# A\n```\n# not one\n```\n## B\n")]
['A', 'B']
```

### epythet.agentic_readme.headline_skill(skills)

The skill named in the install line: a `*-setup`-like one if any, else the first installable.

### epythet.agentic_readme.humans_link_for(heading)

`[Title](#anchor)` for the heading after the section, or a plain fallback.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.agentic_readme.instruction_text(\*, snippets=<function snippet_text>)

The instruction the skill hands an agent when the policy is `add`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.agentic_readme.load(project_dir, , config=None, artifacts=None, user_config=None)

Resolve a project once; each argument given is used instead of being loaded.

* **Return type:**
  [`Project`](#epythet.agentic_readme.Project)

### epythet.agentic_readme.load_project(project_dir)

`(config, artifacts)` for a project; `config` is `None` for a non-Python tree.

A tree without `pyproject.toml` or `setup.cfg` is inspected without a
config. A tree that has one but cannot be loaded raises
[`ConfigError`](epythet.config.html.md#epythet.config.ConfigError): a broken `[tool.epythet]` must not
silently change what gets written.

### epythet.agentic_readme.marker_span(text, , strict=True)

The character span of the marked section (`None` when there is none).

Markers count only on their own line outside fenced code, so a README that
shows them in an example is not mistaken for one that has the section.

* **Parameters:**
  **strict** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – raise [`SectionError`](#epythet.agentic_readme.SectionError) on an unpaired or repeated marker
  (`False`: report such a README as having no section)
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### epythet.agentic_readme.place_section(text, , agentic_first)

Where the section goes in `text`: `(start, end, next_heading, level)`.

`text[start:end]` is the span to replace: the existing marked section when
there is one (its position is kept, wherever the author moved it), else an
empty span right before the first heading after the title (`agentic_first`)
or at the end of the file. `next_heading` is the heading that follows the
span (the “for humans” target) and `level` the heading level the section
should use to sit among its siblings. Headings inside the existing section
are ignored, so rewriting never changes the level.

* **Raises:**
  [**SectionError**](#epythet.agentic_readme.SectionError) – on unpaired markers
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int), [`Heading`](#epythet.agentic_readme.Heading) | [`None`](https://docs.python.org/3/builtins/constants.html#None), [`int`](https://docs.python.org/3/builtins/functions.html#int)]

### epythet.agentic_readme.read_readme(path)

`(text, newline)`: the README with `\n` line ends, and the style to write back.

* **Raises:**
  [**SectionError**](#epythet.agentic_readme.SectionError) – when the file is not UTF-8
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### epythet.agentic_readme.render_section(artifacts, config, \*, policy, level=1, humans_link='the top of the page', snippets=<function snippet_text>, agent='claude-code')

The README section for `artifacts`, from the effective snippets and `policy`.

* **Parameters:**
  * **level** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – heading level (`1` renders `# For AI agents`)
  * **humans_link** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – what the “for humans” sentence points at
  * **snippets** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – `name -> text` resolver (the seam tests use to inject text)
  * **agent** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the host named in the `gh skill install` line
* **Raises:**
  [**SectionError**](#epythet.agentic_readme.SectionError) – when the section snippet fails to format or drops a marker
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.agentic_readme.splice_section(text, section, , start, end)

`text` with `section` in place of `text[start:end]`, blank lines kept sane.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.agentic_readme.write_section(project_dir, , user_config=None)

Add or update the marked section in the project’s README; returns `(path, outcome)`.

`outcome` is `added`, `updated` or `unchanged`. The README must be
Markdown (`README.md`); a missing README is created with the section alone.
Line endings are kept as found (CRLF stays CRLF).

* **Raises:**
  [**SectionError**](#epythet.agentic_readme.SectionError) – when there is nothing agentic to document, the README is
  not Markdown or not UTF-8, it has unpaired markers, or the snippet is broken
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
