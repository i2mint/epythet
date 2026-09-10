---
name: epythet-ai-artifacts
description: >-
  Find, install and document a repository's AI agent artifacts: skills
  (`SKILL.md` folders under `<pkg>/data/skills`, `skills/`, `.claude/skills`),
  subagents (`.claude/agents`, `<pkg>/data/agents`), instruction files
  (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, `.codex`), and the
  machine-readable documentation a site publishes (`llms.txt`, `<package>.md`,
  `.md` page twins, `objects.inv`). Use when arriving in an unfamiliar repo and
  asking "does this project ship skills or agents", "how do I install this
  package's skill", "where is the agent-readable version of these docs", or
  when adding artifacts to a package so that epythet documents them.
license: Apache-2.0
metadata:
  audience: users
---

# epythet-ai-artifacts: where a repository keeps things for agents

## In one command

```bash
pip install epythet
epythet ai-artifacts /path/to/repo            # human table
epythet ai-artifacts /path/to/repo --format json
```

```python
from epythet import discover_artifacts
found = discover_artifacts("/path/to/repo", package_dir="/path/to/repo/pkg")
[s.name for s in found.skills], [a.name for a in found.subagents], [f.source for f in found.instruction_files]
```

Works on any repository, Python or not (without `pyproject.toml` the `<pkg>/data/...` locations are skipped).

## Where to look, by convention

| Artifact | Locations, in order of preference | Who reads it |
|---|---|---|
| Skills | `<pkg>/data/skills/<name>/SKILL.md` (shipped in the wheel, `gh skill`-installable); `skills/<name>/SKILL.md` (`gh skill`-installable); `.claude/skills/<name>/SKILL.md` (Claude Code only, usually symlinks into one of the first two) | `gh skill` scans any non-hidden `**/skills/*/SKILL.md`; Claude Code reads only `.claude/skills/` |
| Subagents | `<pkg>/data/agents/<name>.md`; `.claude/agents/<name>.md` | Claude Code reads `.claude/agents/`; other hosts by copy |
| Instruction files | `CLAUDE.md`, `.claude/CLAUDE.md` (Claude Code); `AGENTS.md` (Codex, Copilot, Cursor and others); `.github/copilot-instructions.md`; `.cursor/rules/`; `.codex/` | read before working in the repo |
| Machine-readable docs | on the published site: `/llms.txt`, `/<package>.md`, `<page>.html.md` twins, `/objects.inv` | any agent with HTTP |

A skill is a folder holding a `SKILL.md` with a YAML frontmatter (`name` equal to the folder name, `description` saying what it does and when to use it, optional `license`, `metadata`, `allowed-tools`) and a body with the procedure; `references/` and `scripts/` may sit beside it. A subagent file has a frontmatter (`name`, `description`, `tools`) and a system prompt as the body.

## Installing a skill you found

```bash
gh skill preview OWNER/REPO SKILL-NAME                         # read it first (third-party skills are not verified)
gh skill install OWNER/REPO SKILL-NAME --agent claude-code     # or copilot | cursor | codex | gemini
gh skill install OWNER/REPO SKILL-NAME@v1.2.0 --agent codex    # pin to a release
gh skill update --all
```

`gh skill` needs a recent GitHub CLI (older releases lack the command; `gh skill --help` tells you). Offline, or from the wheel, link the package's bundled copy:

```bash
pip install PACKAGE
skill link-skills "$(python -c 'import PACKAGE, os; print(os.path.join(PACKAGE.__path__[0], "data", "skills"))')"
```

A subagent is installed by copying its `.md` file into your project's `.claude/agents/` (or the host's equivalent).

## Reading a site's documentation as an agent

For a site built by epythet at `https://OWNER.github.io/REPO/`:

1. `llms.txt` lists every page with a one-line description and names the flat aggregate.
2. `<package>.md` is the whole documentation as one Markdown file: the thing to load into context. (`<package>.pdf` exists when the project enabled it.)
3. Every HTML page has a `.md` twin at `<page>.html.md`, advertised in its `<head>` with `<link rel="alternate" type="text/markdown">`.
4. `objects.inv` maps every documented symbol to its URL (`sphobjinv convert plain objects.inv -`).

Locally, after `epythet quickstart PROJECT_DIR`, the same files are under `PROJECT_DIR/docsrc/_build/html/`.

## How epythet documents them: the "For AI agents" page

When a project has any artifact and `[tool.epythet] ai_artifacts` is on (the default), `epythet quickstart` / `make-docsrc` generates `docsrc/ai-agents.md`, added to the site toctree after the API pages and served at `/ai-agents.html`. It lists each skill with its description, `gh skill install` line and source folder; each subagent with description and tools; the instruction files; and the machine-readable outputs with their URLs (derived from the GitHub URL in `[project.urls]`).

Overriding the template: set `ai_artifacts_template = "docsrc/_templates/ai-agents.md"` (any project-relative path) to a `str.format` template using the fields `{marker}`, `{name}`, `{display_name}`, `{repo_stub}`, `{site_url}`, `{skills_section}`, `{subagents_section}`, `{instructions_section}`, `{outputs_section}` (double literal braces: `{{`). A hand-written `docsrc/ai-agents.md` without the `<!-- generated by epythet -->` marker is never overwritten. `ai_artifacts = false` turns the page off for a project; the environment variable `EPYTHET_AI_ARTIFACTS=0` turns it off for a whole CI fleet without editing any `pyproject.toml`. When the artifacts disappear, the generated page is removed on the next scaffold. From Python: `epythet.ai_artifacts.render_ai_artifacts_page(artifacts, config, template=...)`.

## Adding artifacts to a package so they are found

Follow the layout rule (one real location, symlinks only as a bridge):

1. **Consumer skills** that should ship with `pip install`: real files in `<pkg>/data/skills/<name>/SKILL.md`. This one location is both in the wheel and visible to `gh skill`. Hatchling includes `<pkg>/**` by default; check the wheel with `unzip -l dist/*.whl | grep skills`.
2. **Maintainer-only skills**: real files in repo-root `skills/<name>/`, named `<pkg>-dev-<topic>`, with `metadata.audience: developers`.
3. **Claude Code bridge**: one relative symlink per skill in `.claude/skills/` (`.claude/skills/<name> -> ../../<pkg>/data/skills/<name>`). Never symlink the whole directory, and never keep real files in both `skills/` and `<pkg>/data/skills/` (`gh skill` reports duplicates).
4. **Subagents**: real files in `<pkg>/data/agents/<name>.md` when they should ship, with `.claude/agents/<name>.md -> ../../<pkg>/data/agents/<name>.md`; otherwise directly in `.claude/agents/`.
5. Spec-check every `SKILL.md`: `name` equals the folder name, lowercase `[a-z0-9-]`, 64 characters or fewer; `description` 1024 characters or fewer with trigger phrases; only the spec's top-level keys (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`); `allowed-tools` as a space-separated string; custom keys such as `audience` under `metadata`. Validate with `gh skill publish --dry-run` or `skill validate <dir>`.
6. Add the `gh skill install` lines to the README, rebuild the docs, and confirm `epythet ai-artifacts .` lists everything.

## Example: epythet's own artifacts

```bash
epythet ai-artifacts $(python -c 'import epythet, os; print(os.path.dirname(os.path.dirname(epythet.__file__)))')
gh skill install i2mint/epythet epythet-setup --agent claude-code
```

Skills: `epythet-setup`, `epythet-pages`, `epythet-docstring-style`, `epythet-validate`, `epythet-repair-migrate`, `epythet-theme`, `epythet-ai-artifacts`. Subagents: `docs-reviewer`, `docs-migrator`. Documented at https://i2mint.github.io/epythet/ai-agents.html and aggregated at https://i2mint.github.io/epythet/epythet.md.
