# epythet.ai_artifacts

Discover a repository’s AI agent artifacts and render the “For AI agents” page.

A repository that ships tooling for coding agents does so by convention, not
registration: skills are folders holding a `SKILL.md` (the Agent Skills spec),
subagents are Markdown files with a frontmatter, and instruction files carry
fixed names. This module reads those conventions and, when anything is found,
renders one page for the documentation site that says what exists, where it
lives, how to install it, and which machine-readable outputs the site itself
publishes (`llms.txt`, the `.md` twins, the flat `<package>.md`,
`objects.inv`).

Where epythet looks (relative to the project root; `{pkg}` is the package
directory):

| artifact          | locations, in order of preference                                                                                                                                |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| skills            | `{pkg}/data/skills/*/SKILL.md` (shipped in the wheel,<br/>`gh skill`-installable), `skills/*/SKILL.md`<br/>(`gh skill`-installable), `.claude/skills/*/SKILL.md` |
| subagents         | `{pkg}/data/agents/*.md`, `.claude/agents/*.md`                                                                                                                  |
| instruction files | `CLAUDE.md`, `.claude/CLAUDE.md`, `AGENTS.md`,<br/>`.github/copilot-instructions.md`, `.cursor/rules`,<br/>`.codex/`                                             |

Symlinks are followed and duplicates removed, so the `.claude/skills/` bridge
that points into `{pkg}/data/skills/` yields one skill, attributed to its real
location. The page is a `PageSpec` (`ai-agents.md`),
produced by [`ai_artifacts_page()`](#epythet.ai_artifacts.ai_artifacts_page) and added to the scaffold by default when
`[tool.epythet] ai_artifacts` is on (the default) and at least one artifact
exists. The default template is [`DEFAULT_TEMPLATE`](#epythet.ai_artifacts.DEFAULT_TEMPLATE); a project can point
`ai_artifacts_template` at its own file, and a hand-written `docsrc/ai-agents.md`
without the epythet marker is never overwritten.

```pycon
>>> import tempfile, pathlib
>>> root = pathlib.Path(tempfile.mkdtemp())
>>> skill = root / "pkg" / "data" / "skills" / "pkg-quickstart"
>>> skill.mkdir(parents=True)
>>> _ = (skill / "SKILL.md").write_text(
...     "---\nname: pkg-quickstart\ndescription: Use pkg.\n---\n\n# Body\n"
... )
>>> found = discover_artifacts(root, package_dir=root / "pkg")
>>> [s.name for s in found.skills], found.skills[0].shipped
(['pkg-quickstart'], True)
>>> found.skills[0].install_command("org/pkg")
'gh skill install org/pkg pkg-quickstart --agent claude-code'
```

### Module Attributes

| [`SKILL_LOCATIONS`](#epythet.ai_artifacts.SKILL_LOCATIONS)           | Skill folders relative to the project root; `{pkg}` is the package directory.                                                                 |
|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| [`AGENT_LOCATIONS`](#epythet.ai_artifacts.AGENT_LOCATIONS)           | Subagent definition folders (one Markdown file per agent).                                                                                    |
| [`INSTRUCTION_LOCATIONS`](#epythet.ai_artifacts.INSTRUCTION_LOCATIONS)     | Instruction files and directories agents read, with the audience each serves.                                                                 |
| [`PAGE_FILENAME`](#epythet.ai_artifacts.PAGE_FILENAME)             | The generated page's filename under `docsrc`.                                                                                                 |
| [`DEFAULT_AGENT_HOST`](#epythet.ai_artifacts.DEFAULT_AGENT_HOST)        | The agent host named in generated `gh skill install` lines.                                                                                   |
| [`DISABLE_ENV`](#epythet.ai_artifacts.DISABLE_ENV)               | Environment variable that switches the page off for a whole fleet build (`0` / `false` / `no` / `off`) without touching any `pyproject.toml`. |
| [`AGENT_OUTPUT_KINDS`](#epythet.ai_artifacts.AGENT_OUTPUT_KINDS)        | The machine-readable outputs every epythet site publishes, in display order.                                                                  |
| [`TEMPLATE_FIELDS`](#epythet.ai_artifacts.TEMPLATE_FIELDS)           | The fields a page template may use.                                                                                                           |
| [`DEFAULT_TEMPLATE`](#epythet.ai_artifacts.DEFAULT_TEMPLATE)          | The default page template; `str.format` fields are the section renders.                                                                       |
| [`AGENT_OUTPUT_DESCRIPTIONS`](#epythet.ai_artifacts.AGENT_OUTPUT_DESCRIPTIONS) | Descriptions of the machine-readable outputs, keyed by kind.                                                                                  |

### Functions

| [`agent_outputs_for`](#epythet.ai_artifacts.agent_outputs_for)(config)                          | The machine-readable outputs a configuration produces, with URLs when known.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`ai_artifacts_page`](#epythet.ai_artifacts.ai_artifacts_page)(config, \*[, artifacts])         | The "For AI agents" `PageSpec` for a project, or `None`.                       |
| [`artifacts_json`](#epythet.ai_artifacts.artifacts_json)(artifacts)                          | `artifacts` as indented JSON (the `--format json` CLI output).                 |
| [`artifacts_table`](#epythet.ai_artifacts.artifacts_table)(artifacts, \*[, repo_stub])        | A plain-text listing of `artifacts` (the default CLI output).                  |
| [`default_pages`](#epythet.ai_artifacts.default_pages)(config)                              | The generated pages a scaffold gets when the caller passes none.               |
| [`discover_artifacts`](#epythet.ai_artifacts.discover_artifacts)(project_dir, \*[, package_dir]) | Find the skills, subagents and instruction files of a project by convention.   |
| [`enabled_by_environment`](#epythet.ai_artifacts.enabled_by_environment)()                           | False when `EPYTHET_AI_ARTIFACTS` is set to `0`, `false`, `no` or `off`.       |
| [`parse_frontmatter`](#epythet.ai_artifacts.parse_frontmatter)(text)                            | The YAML frontmatter of a Markdown file as a dict (`{}` when absent).          |
| [`render_ai_artifacts_page`](#epythet.ai_artifacts.render_ai_artifacts_page)(artifacts, config, \*)    | Render the "For AI agents" page for `artifacts` and a `DocsConfig`.            |
| [`repo_stub_for`](#epythet.ai_artifacts.repo_stub_for)(repo_url)                            | `owner/repo` from a GitHub URL ('' when it is not one).                        |
| [`site_url_for`](#epythet.ai_artifacts.site_url_for)(repo_url)                             | The GitHub Pages URL a GitHub repository publishes to ('' when unknown).       |

### Classes

| [`AIArtifacts`](#epythet.ai_artifacts.AIArtifacts)(project_dir[, skills, ...])           | Everything [`discover_artifacts()`](#epythet.ai_artifacts.discover_artifacts) found for one project.   |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| [`AgentOutput`](#epythet.ai_artifacts.AgentOutput)(kind, filename, description[, url])   | A machine-readable output of the built site, with its URL when known.                                     |
| [`InstructionFile`](#epythet.ai_artifacts.InstructionFile)(source, audience[, is_dir])       | An instruction file or directory (`CLAUDE.md`, `AGENTS.md`, ...).                                         |
| [`Skill`](#epythet.ai_artifacts.Skill)(name, source[, description, audience, ...]) | One skill folder: its `name`, description, and where the real files live.                                 |
| [`Subagent`](#epythet.ai_artifacts.Subagent)(name, source[, description, tools, ...]) | One subagent definition file (`name`, description, tools, source path).                                   |

### epythet.ai_artifacts.AGENT_LOCATIONS *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('{pkg}/data/agents', '.claude/agents')*

Subagent definition folders (one Markdown file per agent).

### epythet.ai_artifacts.AGENT_OUTPUT_DESCRIPTIONS *= {'aggregate_md': 'the whole documentation as one Markdown file', 'aggregate_pdf': 'the whole documentation as one PDF, for reading', 'llms': 'an index of every page with a one-line description ([llms.txt](https://llmstxt.org) format)', 'md_twins': 'a rendered Markdown twin of every page, advertised from each page\\'s \`<head>\` with \`<link rel="alternate" type="text/markdown">\`', 'objects_inv': 'the Sphinx inventory: a symbol-to-URL index (\`sphobjinv convert plain objects.inv -\`)'}*

Descriptions of the machine-readable outputs, keyed by kind.

### epythet.ai_artifacts.AGENT_OUTPUT_KINDS *= ('llms', 'aggregate_md', 'aggregate_pdf', 'md_twins', 'objects_inv')*

The machine-readable outputs every epythet site publishes, in display order.

### *class* epythet.ai_artifacts.AIArtifacts(project_dir, skills=(), subagents=(), instruction_files=())

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Everything [`discover_artifacts()`](#epythet.ai_artifacts.discover_artifacts) found for one project.

#### to_dict()

A JSON-ready view (paths relative to the project root).

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

### *class* epythet.ai_artifacts.AgentOutput(kind, filename, description, url='')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A machine-readable output of the built site, with its URL when known.

### epythet.ai_artifacts.DEFAULT_AGENT_HOST *= 'claude-code'*

The agent host named in generated `gh skill install` lines.

### epythet.ai_artifacts.DEFAULT_TEMPLATE *= '{marker}\\n\\n# For AI agents\\n\\n\`{name}\` ships artifacts for coding agents alongside its code. This page lists\\nthem, says where each lives in the repository, and points at the\\nmachine-readable copies of this documentation.\\n{skills_section}{subagents_section}{instructions_section}{outputs_section}'*

The default page template; `str.format` fields are the section renders.

### epythet.ai_artifacts.DISABLE_ENV *= 'EPYTHET_AI_ARTIFACTS'*

Environment variable that switches the page off for a whole fleet build
(`0` / `false` / `no` / `off`) without touching any `pyproject.toml`.

### epythet.ai_artifacts.INSTRUCTION_LOCATIONS *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)], ...]* *= (('CLAUDE.md', 'Claude Code'), ('.claude/CLAUDE.md', 'Claude Code'), ('AGENTS.md', 'Codex, Copilot, Cursor and other agents'), ('.github/copilot-instructions.md', 'GitHub Copilot'), ('.cursor/rules', 'Cursor'), ('.codex', 'Codex'))*

Instruction files and directories agents read, with the audience each serves.

### *class* epythet.ai_artifacts.InstructionFile(source, audience, is_dir=False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

An instruction file or directory (`CLAUDE.md`, `AGENTS.md`, …).

### epythet.ai_artifacts.PAGE_FILENAME *= 'ai-agents.md'*

The generated page’s filename under `docsrc`.

### epythet.ai_artifacts.SKILL_LOCATIONS *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('{pkg}/data/skills', 'skills', '.claude/skills')*

Skill folders relative to the project root; `{pkg}` is the package directory.

### *class* epythet.ai_artifacts.Skill(name, source, description='', audience='', shipped=False, installable=True)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One skill folder: its `name`, description, and where the real files live.

`source` is the project-relative POSIX path of the folder that holds the
files (a symlink in `.claude/skills/` is attributed to its target).
`shipped` is true when that folder is under the package directory, so the
skill is inside the wheel; `installable` when `gh skill` can see it (a
non-hidden path).

#### install_command(repo_stub, , agent='claude-code')

The `gh skill install` line, or `None` when `gh skill` cannot see it.

```pycon
>>> Skill("x", "pkg/data/skills/x").install_command("org/repo")
'gh skill install org/repo x --agent claude-code'
>>> Skill("x", ".claude/skills/x", installable=False).install_command("o/r")
```

### *class* epythet.ai_artifacts.Subagent(name, source, description='', tools='', shipped=False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One subagent definition file (`name`, description, tools, source path).

### epythet.ai_artifacts.TEMPLATE_FIELDS *= frozenset({'display_name', 'instructions_section', 'marker', 'name', 'outputs_section', 'repo_stub', 'site_url', 'skills_section', 'subagents_section'})*

The fields a page template may use.

### epythet.ai_artifacts.agent_outputs_for(config)

The machine-readable outputs a configuration produces, with URLs when known.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`AgentOutput`](#epythet.ai_artifacts.AgentOutput)]

```pycon
>>> from epythet.config import DocsConfig
>>> cfg = DocsConfig(project_dir="/tmp/x", name="x", repo_url="https://github.com/o/x")
>>> [o.filename for o in agent_outputs_for(cfg)]
['llms.txt', 'x.md', '<page>.html.md', 'objects.inv']
>>> agent_outputs_for(cfg)[0].url
'https://o.github.io/x/llms.txt'
```

### epythet.ai_artifacts.ai_artifacts_page(config, , artifacts=None)

The “For AI agents” `PageSpec` for a project, or `None`.

`None` when `config.ai_artifacts` is off, when the `EPYTHET_AI_ARTIFACTS`
environment variable is `0`/`false` (the fleet-wide switch), or when no
artifact was found. The template is `config.ai_artifacts_template` (a
file, relative to the project root) when set, else [`DEFAULT_TEMPLATE`](#epythet.ai_artifacts.DEFAULT_TEMPLATE).

* **Raises:**
  [**ConfigError**](epythet.config.html.md#epythet.config.ConfigError) – when the template file is missing or has a field the
  renderer does not provide (literal braces must be doubled: `{{`).

### epythet.ai_artifacts.artifacts_json(artifacts)

`artifacts` as indented JSON (the `--format json` CLI output).

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.ai_artifacts.artifacts_table(artifacts, , repo_stub='')

A plain-text listing of `artifacts` (the default CLI output).

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.ai_artifacts.default_pages(config)

The generated pages a scaffold gets when the caller passes none.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)

### epythet.ai_artifacts.discover_artifacts(project_dir, , package_dir=None)

Find the skills, subagents and instruction files of a project by convention.

* **Parameters:**
  * **project_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – the repository root
  * **package_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/library/constants.html#None)) – the importable package directory, for `{pkg}/data/...`
    (skipped when `None`)
* **Return type:**
  [`AIArtifacts`](#epythet.ai_artifacts.AIArtifacts)

### epythet.ai_artifacts.enabled_by_environment()

False when `EPYTHET_AI_ARTIFACTS` is set to `0`, `false`, `no` or `off`.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

```pycon
>>> os.environ[DISABLE_ENV] = "0"; enabled_by_environment()
False
>>> del os.environ[DISABLE_ENV]; enabled_by_environment()
True
```

### epythet.ai_artifacts.parse_frontmatter(text)

The YAML frontmatter of a Markdown file as a dict (`{}` when absent).

Uses PyYAML when installed; otherwise, or when PyYAML rejects the block (an
unquoted `description: Use when x: y` is a common slip), a small reader
that understands the subset skills and agents use: `key: value` scalars,
`>`/`|` block scalars, one level of nested mapping, `[a, b]` flow
lists and trailing comments. A malformed frontmatter never raises.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

```pycon
>>> parse_frontmatter("---\ndescription: Use when a: b\nname: x\n---\n")
{'description': 'Use when a: b', 'name': 'x'}
```

```pycon
>>> parse_frontmatter("---\nname: x\nmetadata:\n  audience: users\n---\nbody")
{'name': 'x', 'metadata': {'audience': 'users'}}
>>> parse_frontmatter("no frontmatter")
{}
```

### epythet.ai_artifacts.render_ai_artifacts_page(artifacts, config, , template='{marker}\\\\n\\\\n# For AI agents\\\\n\\\\n\`{name}\` ships artifacts for coding agents alongside its code. This page lists\\\\nthem, says where each lives in the repository, and points at the\\\\nmachine-readable copies of this documentation.\\\\n{skills_section}{subagents_section}{instructions_section}{outputs_section}', agent='claude-code')

Render the “For AI agents” page for `artifacts` and a `DocsConfig`.

* **Parameters:**
  * **template** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – a `str.format` template with the fields `marker`,
    `name`, `display_name`, `repo_stub`, `site_url`, `skills_section`,
    `subagents_section`, `instructions_section`, `outputs_section`
  * **agent** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – the host named in the `gh skill install` lines
* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.ai_artifacts.repo_stub_for(repo_url)

`owner/repo` from a GitHub URL (’’ when it is not one).

Deeper paths, fragments and queries are dropped, so an `Issues` URL in
`[project.urls]` still names the repository.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> repo_stub_for("https://github.com/i2mint/epythet.git")
'i2mint/epythet'
>>> repo_stub_for("https://github.com/i2mint/epythet/issues#readme")
'i2mint/epythet'
>>> repo_stub_for("git@github.com:i2mint/epythet.git")
'i2mint/epythet'
>>> repo_stub_for("https://gitlab.com/o/r")
''
```

### epythet.ai_artifacts.site_url_for(repo_url)

The GitHub Pages URL a GitHub repository publishes to (’’ when unknown).

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> site_url_for("https://github.com/i2mint/epythet")
'https://i2mint.github.io/epythet/'
>>> site_url_for("")
''
```
