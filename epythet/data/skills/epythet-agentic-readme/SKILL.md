---
name: epythet-agentic-readme
description: >-
  Make sure a repository's README documents its agentic aspects: the skills,
  subagents and instruction files it ships (`<pkg>/data/skills`, `.claude/skills`,
  `.claude/agents`, `CLAUDE.md`, `AGENTS.md`) and the agent-readable docs its
  site publishes (`llms.txt`, `<package>.md`). Runs `epythet ai-readme-check`,
  reads the user's policy (`~/.config/epythet/config.toml`: warn or add, humour,
  agents first) and either reports what is missing or adds and updates a marked
  "For AI agents" section rendered from user-overridable snippets
  (`epythet snippets`). Use when asked "does the README mention the skills",
  "add the agent section to the README", "document the agentic aspects",
  when finishing a docs sweep, or before releasing a package that ships skills.
license: Apache-2.0
metadata:
  audience: users
---

# epythet-agentic-readme: the README knows what it ships for agents

An agent arriving at a repository reads the README first. If the repository ships skills, subagents or instruction files, or its documentation site publishes `llms.txt` and `<package>.md`, the README should say so, before anything else if the maintainer wants it that way. This skill checks, and then does what the user's policy says.

## Procedure

1. **Check.** From the project root:

   ```bash
   epythet ai-readme-check . --format json
   ```

   The output has `checks` (one per kind: `section`, `skills`, `subagents`, `instruction_files`, `agent_docs`, each `ok`, `warn` or `n/a`) and `policy.readme` (the effective `[readme]` table: `agentic_aspects`, `humor`, `agentic_first`). `epythet ai-readme-check .` without `--format` prints the same as a table. Exit code is 0 either way; add `--fail-on warn` in CI to fail on an undocumented kind.

2. **Branch on the policy.**

   - `agentic_aspects = "warn"` (the packaged default): report the `warn` rows to the user, one line each, and stop. Say how to switch to `add` locally (below). Do not edit the README.
   - `agentic_aspects = "add"`: follow the instruction snippet, which the user may have rewritten:

     ```bash
     epythet snippets show agentic-readme-instruction
     ```

     Then let epythet write the section, so it lands between marker comments and stays idempotent:

     ```bash
     epythet ai-readme-check . --write
     ```

     The section goes right after the README's intro, before the first section heading, when `agentic_first` is true; at the end otherwise. A later `--write` updates it in place wherever the author moved it. The check runs again after the write and its table is the report.

3. **Review the prose as a stranger would.** Read the section in the README. The humour line (one per package, chosen stably from the pool) is light and on the writer's side of the joke; if it is not, fix the pool, not the README. No em-dashes, no "not X but Y", no closing paragraph that restates the section, every link resolves. If the README already covered the same artifacts under a heading of its own, keep that heading only if it says something the generated section does not; otherwise remove it so the two never disagree.

4. **Never hand-edit inside the markers.** The next `--write` replaces everything between `<!-- epythet:agentic-readme:start -->` and `<!-- epythet:agentic-readme:end -->`. Wording lives in the snippets.

## Setting the local policy

The packaged default is to warn. To add sections on your machine, write `~/.config/epythet/config.toml` (or `$XDG_CONFIG_HOME/epythet/config.toml`; `$EPYTHET_CONFIG_DIR` overrides the folder):

```toml
[readme]
agentic_aspects = "add"   # "warn" | "add"
humor = true              # draw the "for humans" opener from the humour pool
agentic_first = true      # section right after the intro, before the first heading
```

Unknown keys are an error, so typos do not pass silently. The data side of epythet's local state (`epythet validate` observations) stays under `~/.local/share/epythet`; config and snippets live under `~/.config/epythet`.

## Changing the wording: snippets

Three snippets render the section. The user's copy in `<config dir>/snippets/<name>.md` wins over the packaged default in `epythet/data/snippets/`:

| Snippet | What it is |
|---|---|
| `agentic-readme-section` | the section template (`str.format` fields: `{marker_start}`, `{marker_end}`, `{heading}`, `{name}`, `{repo_stub}`, `{site_url}`, `{skills_block}`, `{subagents_block}`, `{instructions_block}`, `{docs_block}`, `{for_humans_intro}`, `{humans_link}`; literal braces doubled) |
| `agentic-readme-humor` | the pool of openers for the "for humans" sentence, one per line, `#` comments allowed |
| `agentic-readme-instruction` | what step 2 tells the agent when the policy is `add` |

```bash
epythet snippets list                 # every snippet: user or packaged, provenance, modified or not
epythet snippets show NAME            # the effective text
epythet snippets init                 # copy the packaged defaults out, once; never overwrites
epythet snippets diff [--name NAME]   # your copy against the current packaged default (exit 1 when different)
```

`init` writes a header recording the epythet version each copy came from, and a second `init` is a no-op (`--force` replaces, so run `diff` first). After upgrading epythet, `diff` shows what changed upstream; nothing is ever merged into your files for you. `epythet ai-readme-check . --draft` prints the section as it would be written, from the effective snippets and policy, without touching the README.

## What the check looks for

| Kind | Present when | Documented when the README has |
|---|---|---|
| `skills` | `epythet ai-artifacts` finds a `SKILL.md` | a `gh skill install` line or a skill name |
| `subagents` | an agent file under `<pkg>/data/agents` or `.claude/agents` | the word "subagent" or an agent name |
| `instruction_files` | `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, `.codex`, `.github/copilot-instructions.md` | the file name |
| `agent_docs` | `[tool.epythet] agent_outputs` is on | `llms.txt`, `<package>.md`, `objects.inv` or `ai-agents.html` |
| `section` | any of the above | epythet's markers, or a heading mentioning agents or LLMs |

Discovery is the same as the "For AI agents" site page (skill `epythet-ai-artifacts`), so the README and the site never disagree about what exists.

## Related, not done here

Where skills should live (package data or repository root) and how each host installs them is being decided in [thorwhalen/skill#8](https://github.com/thorwhalen/skill/issues/8); reusing skills as subagents in [thorwhalen/opsward#26](https://github.com/thorwhalen/opsward/issues/26). The section's install line follows whatever `epythet ai-artifacts` reports, so those decisions change the output without changing this skill.
