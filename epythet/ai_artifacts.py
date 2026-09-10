r"""Discover a repository's AI agent artifacts and render the "For AI agents" page.

A repository that ships tooling for coding agents does so by convention, not
registration: skills are folders holding a ``SKILL.md`` (the Agent Skills spec),
subagents are Markdown files with a frontmatter, and instruction files carry
fixed names. This module reads those conventions and, when anything is found,
renders one page for the documentation site that says what exists, where it
lives, how to install it, and which machine-readable outputs the site itself
publishes (``llms.txt``, the ``.md`` twins, the flat ``<package>.md``,
``objects.inv``).

Where epythet looks (relative to the project root; ``{pkg}`` is the package
directory):

=========================  ==========================================================
artifact                   locations, in order of preference
=========================  ==========================================================
skills                     ``{pkg}/data/skills/*/SKILL.md`` (shipped in the wheel,
                           ``gh skill``-installable), ``skills/*/SKILL.md``
                           (``gh skill``-installable), ``.claude/skills/*/SKILL.md``
subagents                  ``{pkg}/data/agents/*.md``, ``.claude/agents/*.md``
instruction files          ``CLAUDE.md``, ``.claude/CLAUDE.md``, ``AGENTS.md``,
                           ``.github/copilot-instructions.md``, ``.cursor/rules``,
                           ``.codex/``
=========================  ==========================================================

Symlinks are followed and duplicates removed, so the ``.claude/skills/`` bridge
that points into ``{pkg}/data/skills/`` yields one skill, attributed to its real
location. The page is a :class:`~epythet.scaffold.PageSpec` (``ai-agents.md``),
produced by :func:`ai_artifacts_page` and added to the scaffold by default when
``[tool.epythet] ai_artifacts`` is on (the default) and at least one artifact
exists. The default template is :data:`DEFAULT_TEMPLATE`; a project can point
``ai_artifacts_template`` at its own file, and a hand-written ``docsrc/ai-agents.md``
without the epythet marker is never overwritten.

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
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

from epythet import templates
from epythet.config import ConfigError

#: Skill folders relative to the project root; ``{pkg}`` is the package directory.
SKILL_LOCATIONS: tuple[str, ...] = ("{pkg}/data/skills", "skills", ".claude/skills")
#: Subagent definition folders (one Markdown file per agent).
AGENT_LOCATIONS: tuple[str, ...] = ("{pkg}/data/agents", ".claude/agents")
#: Instruction files and directories agents read, with the audience each serves.
INSTRUCTION_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("CLAUDE.md", "Claude Code"),
    (".claude/CLAUDE.md", "Claude Code"),
    ("AGENTS.md", "Codex, Copilot, Cursor and other agents"),
    (".github/copilot-instructions.md", "GitHub Copilot"),
    (".cursor/rules", "Cursor"),
    (".codex", "Codex"),
)
#: The generated page's filename under ``docsrc``.
PAGE_FILENAME = "ai-agents.md"
#: The agent host named in generated ``gh skill install`` lines.
DEFAULT_AGENT_HOST = "claude-code"
#: Environment variable that switches the page off for a whole fleet build
#: (``0`` / ``false`` / ``no`` / ``off``) without touching any ``pyproject.toml``.
DISABLE_ENV = "EPYTHET_AI_ARTIFACTS"
#: The machine-readable outputs every epythet site publishes, in display order.
AGENT_OUTPUT_KINDS = (
    "llms",
    "aggregate_md",
    "aggregate_pdf",
    "md_twins",
    "objects_inv",
)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Skill:
    """One skill folder: its ``name``, description, and where the real files live.

    ``source`` is the project-relative POSIX path of the folder that holds the
    files (a symlink in ``.claude/skills/`` is attributed to its target).
    ``shipped`` is true when that folder is under the package directory, so the
    skill is inside the wheel; ``installable`` when ``gh skill`` can see it (a
    non-hidden path).
    """

    name: str
    source: str
    description: str = ""
    audience: str = ""
    shipped: bool = False
    installable: bool = True

    def install_command(self, repo_stub: str, *, agent: str = DEFAULT_AGENT_HOST):
        """The ``gh skill install`` line, or ``None`` when ``gh skill`` cannot see it.

        >>> Skill("x", "pkg/data/skills/x").install_command("org/repo")
        'gh skill install org/repo x --agent claude-code'
        >>> Skill("x", ".claude/skills/x", installable=False).install_command("o/r")
        """
        if not (self.installable and repo_stub):
            return None
        return f"gh skill install {repo_stub} {self.name} --agent {agent}"


@dataclass(frozen=True)
class Subagent:
    """One subagent definition file (``name``, description, tools, source path)."""

    name: str
    source: str
    description: str = ""
    tools: str = ""
    shipped: bool = False


@dataclass(frozen=True)
class InstructionFile:
    """An instruction file or directory (``CLAUDE.md``, ``AGENTS.md``, ...)."""

    source: str
    audience: str
    is_dir: bool = False


@dataclass(frozen=True)
class AgentOutput:
    """A machine-readable output of the built site, with its URL when known."""

    kind: str
    filename: str
    description: str
    url: str = ""


@dataclass(frozen=True)
class AIArtifacts:
    """Everything :func:`discover_artifacts` found for one project."""

    project_dir: Path
    skills: tuple[Skill, ...] = ()
    subagents: tuple[Subagent, ...] = ()
    instruction_files: tuple[InstructionFile, ...] = ()

    def __bool__(self) -> bool:
        """True when at least one artifact of any kind was found."""
        return bool(self.skills or self.subagents or self.instruction_files)

    def to_dict(self) -> dict:
        """A JSON-ready view (paths relative to the project root)."""
        return {
            "project_dir": str(self.project_dir),
            "skills": [asdict(s) for s in self.skills],
            "subagents": [asdict(a) for a in self.subagents],
            "instruction_files": [asdict(f) for f in self.instruction_files],
        }


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def discover_artifacts(
    project_dir: str | Path, *, package_dir: str | Path | None = None
) -> AIArtifacts:
    """Find the skills, subagents and instruction files of a project by convention.

    :param project_dir: the repository root
    :param package_dir: the importable package directory, for ``{pkg}/data/...``
        (skipped when ``None``)
    """
    root = Path(project_dir).absolute()
    pkg = Path(package_dir).absolute() if package_dir else None
    return AIArtifacts(
        project_dir=root,
        skills=tuple(_discover_skills(root, pkg)),
        subagents=tuple(_discover_subagents(root, pkg)),
        instruction_files=tuple(_discover_instruction_files(root)),
    )


def _candidate_dirs(root: Path, pkg: Path | None, locations: Iterable[str]):
    for location in locations:
        if "{pkg}" in location:
            if pkg is None:
                continue
            yield pkg / location.replace("{pkg}/", "")
        else:
            yield root / location


def _discover_skills(root: Path, pkg: Path | None) -> Iterator[Skill]:
    seen: set[Path] = set()
    for folder in _candidate_dirs(root, pkg, SKILL_LOCATIONS):
        if not folder.is_dir():
            continue
        for entry in sorted(folder.iterdir()):
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                continue
            real = entry.resolve()
            if real in seen:
                continue
            seen.add(real)
            meta = _frontmatter_of(skill_md)
            metadata = meta.get("metadata")
            source = _relative_source(real, root, fallback=entry)
            yield Skill(
                name=_text(meta.get("name")) or entry.name,
                source=source,
                description=_text(meta.get("description")),
                audience=_text(metadata.get("audience"))
                if isinstance(metadata, dict)
                else "",
                shipped=_is_under(real, pkg),
                installable=not _is_hidden(source),
            )


def _discover_subagents(root: Path, pkg: Path | None) -> Iterator[Subagent]:
    seen: set[Path] = set()
    for folder in _candidate_dirs(root, pkg, AGENT_LOCATIONS):
        if not folder.is_dir():
            continue
        for entry in sorted(folder.glob("*.md")):
            real = entry.resolve()
            if real in seen or not real.is_file():
                continue
            seen.add(real)
            meta = _frontmatter_of(entry)
            yield Subagent(
                name=_text(meta.get("name")) or entry.stem,
                source=_relative_source(real, root, fallback=entry),
                description=_text(meta.get("description")),
                tools=_tools_string(meta.get("tools")),
                shipped=_is_under(real, pkg),
            )


def _discover_instruction_files(root: Path) -> Iterator[InstructionFile]:
    for relative, audience in INSTRUCTION_LOCATIONS:
        path = root / relative
        if path.is_file() or (path.is_dir() and any(path.iterdir())):
            yield InstructionFile(relative, audience, is_dir=path.is_dir())


def _frontmatter_of(path: Path) -> dict:
    """The frontmatter of a file, tolerating bad encodings and unreadable files."""
    try:
        return parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def _text(value) -> str:
    """A frontmatter scalar as one stripped string ('' for anything that is not text).

    >>> _text(" x "), _text(["a"]), _text(None), _text(3)
    ('x', '', '', '3')
    """
    if value is None or isinstance(value, (list, dict, bool)):
        return ""
    return str(value).strip()


def _relative_source(real: Path, root: Path, *, fallback: Path) -> str:
    for candidate in (real, fallback):
        try:
            return candidate.relative_to(root.resolve()).as_posix()
        except ValueError:
            try:
                return candidate.relative_to(root).as_posix()
            except ValueError:
                continue
    return fallback.as_posix()


def _is_under(path: Path, parent: Path | None) -> bool:
    if parent is None:
        return False
    try:
        path.relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_hidden(source: str) -> bool:
    return any(part.startswith(".") for part in source.split("/"))


def _tools_string(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------


def parse_frontmatter(text: str) -> dict:
    r"""The YAML frontmatter of a Markdown file as a dict (``{}`` when absent).

    Uses PyYAML when installed; otherwise, or when PyYAML rejects the block (an
    unquoted ``description: Use when x: y`` is a common slip), a small reader
    that understands the subset skills and agents use: ``key: value`` scalars,
    ``>``/``|`` block scalars, one level of nested mapping, ``[a, b]`` flow
    lists and trailing comments. A malformed frontmatter never raises.

    >>> parse_frontmatter("---\ndescription: Use when a: b\nname: x\n---\n")
    {'description': 'Use when a: b', 'name': 'x'}

    >>> parse_frontmatter("---\nname: x\nmetadata:\n  audience: users\n---\nbody")
    {'name': 'x', 'metadata': {'audience': 'users'}}
    >>> parse_frontmatter("no frontmatter")
    {}
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(block)
        return loaded if isinstance(loaded, dict) else {}
    except ImportError:
        return _parse_simple_yaml(block)
    except Exception:  # yaml.YAMLError: degrade to the tolerant reader
        return _parse_simple_yaml(block)


def _parse_simple_yaml(block: str) -> dict:
    result: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#") or line.startswith(" "):
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value in (">", ">-", "|", "|-"):
            folded, i = _block_scalar(lines, i)
            result[key] = (
                " ".join(folded) if value.startswith(">") else "\n".join(folded)
            )
        elif value == "":
            nested, i = _nested_mapping(lines, i)
            result[key] = nested
        else:
            result[key] = _scalar(value)
    return result


def _block_scalar(lines: list[str], i: int) -> tuple[list[str], int]:
    collected = []
    while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
        collected.append(lines[i].strip())
        i += 1
    return [c for c in collected if c], i


def _nested_mapping(lines: list[str], i: int) -> tuple[dict, int]:
    nested: dict = {}
    while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
        if lines[i].strip():
            key, _, value = lines[i].strip().partition(":")
            nested[key.strip()] = _scalar(value.strip())
        i += 1
    return nested, i


def _scalar(value: str):
    value = re.sub(r"\s+#.*$", "", value).strip()
    if value.startswith("[") and value.endswith("]"):
        return [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

#: The fields a page template may use.
TEMPLATE_FIELDS = frozenset(
    {
        "marker",
        "name",
        "display_name",
        "repo_stub",
        "site_url",
        "skills_section",
        "subagents_section",
        "instructions_section",
        "outputs_section",
    }
)

#: The default page template; ``str.format`` fields are the section renders.
DEFAULT_TEMPLATE = """\
{marker}

# For AI agents

`{name}` ships artifacts for coding agents alongside its code. This page lists
them, says where each lives in the repository, and points at the
machine-readable copies of this documentation.
{skills_section}{subagents_section}{instructions_section}{outputs_section}"""

SKILLS_HEADER = """

## Skills

Skills are folders holding a `SKILL.md` (the [Agent Skills](https://agentskills.io) format): a description that tells an agent when to use it and a body with the procedure. Install one into your agent with `gh skill` (any host: `--agent claude-code`, `copilot`, `cursor`, `codex`, `gemini`), or use the copy bundled in the wheel.
"""

SUBAGENTS_HEADER = """

## Subagents

Subagents are Markdown files with a frontmatter (`name`, `description`, `tools`) and a system prompt as the body. Copy one into your project's `.claude/agents/` (or your agent host's equivalent) to delegate the task it describes.
"""

INSTRUCTIONS_HEADER = """

## Instruction files

Files agents read before working in this repository.
"""

OUTPUTS_HEADER = """

## Machine-readable documentation

This site publishes the same documentation in forms that fit an agent's context window:
"""

#: Descriptions of the machine-readable outputs, keyed by kind.
AGENT_OUTPUT_DESCRIPTIONS = {
    "llms": "an index of every page with a one-line description ([llms.txt](https://llmstxt.org) format)",
    "aggregate_md": "the whole documentation as one Markdown file",
    "aggregate_pdf": "the whole documentation as one PDF, for reading",
    "md_twins": 'a rendered Markdown twin of every page, advertised from each page\'s `<head>` with `<link rel="alternate" type="text/markdown">`',
    "objects_inv": "the Sphinx inventory: a symbol-to-URL index (`sphobjinv convert plain objects.inv -`)",
}


def agent_outputs_for(config) -> list[AgentOutput]:
    """The machine-readable outputs a configuration produces, with URLs when known.

    >>> from epythet.config import DocsConfig
    >>> cfg = DocsConfig(project_dir="/tmp/x", name="x", repo_url="https://github.com/o/x")
    >>> [o.filename for o in agent_outputs_for(cfg)]
    ['llms.txt', 'x.md', '<page>.html.md', 'objects.inv']
    >>> agent_outputs_for(cfg)[0].url
    'https://o.github.io/x/llms.txt'
    """
    site = site_url_for(config.repo_url)
    outputs: list[AgentOutput] = []

    def add(kind, filename):
        url = f"{site}{filename}" if site and "<" not in filename else ""
        outputs.append(
            AgentOutput(kind, filename, AGENT_OUTPUT_DESCRIPTIONS[kind], url)
        )

    if config.agent_outputs:
        add("llms", "llms.txt")
        if "md" in config.aggregates:
            add("aggregate_md", f"{config.name}.md")
        if "pdf" in config.aggregates:
            add("aggregate_pdf", f"{config.name}.pdf")
        add("md_twins", "<page>.html.md")
    add("objects_inv", "objects.inv")
    return outputs


def site_url_for(repo_url: str) -> str:
    """The GitHub Pages URL a GitHub repository publishes to ('' when unknown).

    >>> site_url_for("https://github.com/i2mint/epythet")
    'https://i2mint.github.io/epythet/'
    >>> site_url_for("")
    ''
    """
    stub = repo_stub_for(repo_url)
    if not stub:
        return ""
    owner, repo = stub.split("/")
    return f"https://{owner}.github.io/{repo}/"


def repo_stub_for(repo_url: str) -> str:
    """``owner/repo`` from a GitHub URL ('' when it is not one).

    Deeper paths, fragments and queries are dropped, so an ``Issues`` URL in
    ``[project.urls]`` still names the repository.

    >>> repo_stub_for("https://github.com/i2mint/epythet.git")
    'i2mint/epythet'
    >>> repo_stub_for("https://github.com/i2mint/epythet/issues#readme")
    'i2mint/epythet'
    >>> repo_stub_for("git@github.com:i2mint/epythet.git")
    'i2mint/epythet'
    >>> repo_stub_for("https://gitlab.com/o/r")
    ''
    """
    match = re.search(
        r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?]|$)",
        repo_url or "",
    )
    return f"{match.group(1)}/{match.group(2)}" if match else ""


def render_ai_artifacts_page(
    artifacts: AIArtifacts,
    config,
    *,
    template: str = DEFAULT_TEMPLATE,
    agent: str = DEFAULT_AGENT_HOST,
) -> str:
    """Render the "For AI agents" page for ``artifacts`` and a :class:`DocsConfig`.

    :param template: a ``str.format`` template with the fields ``marker``,
        ``name``, ``display_name``, ``repo_stub``, ``site_url``, ``skills_section``,
        ``subagents_section``, ``instructions_section``, ``outputs_section``
    :param agent: the host named in the ``gh skill install`` lines
    """
    repo_stub = repo_stub_for(config.repo_url)
    source_base = f"https://github.com/{repo_stub}/tree/HEAD/" if repo_stub else ""
    return template.format(
        marker=templates.INDEX_MARKER,
        name=config.name,
        display_name=config.display_name,
        repo_stub=repo_stub,
        site_url=site_url_for(config.repo_url),
        skills_section=_render_skills(
            artifacts.skills, repo_stub, source_base, config.name, agent
        ),
        subagents_section=_render_subagents(artifacts.subagents, source_base),
        instructions_section=_render_instructions(
            artifacts.instruction_files, source_base
        ),
        outputs_section=_render_outputs(agent_outputs_for(config)),
    )


def _source_link(source: str, base: str) -> str:
    return f"[`{source}`]({base}{source})" if base else f"`{source}`"


def _render_skills(skills, repo_stub, source_base, package_name, agent) -> str:
    if not skills:
        return ""
    parts = [SKILLS_HEADER]
    shipped_any = any(s.shipped for s in skills)
    for skill in skills:
        parts.append(f"\n### `{skill.name}`\n")
        if skill.description:
            parts.append(f"\n{skill.description}\n")
        command = skill.install_command(repo_stub, agent=agent)
        if command:
            parts.append(f"\n```bash\n{command}\n```\n")
        where = _source_link(skill.source, source_base)
        note = " (bundled with the pip package)" if skill.shipped else ""
        parts.append(f"\nSource: {where}{note}.\n")
    if shipped_any:
        parts.append(
            f"\nThe bundled skills are also on disk after `pip install {package_name}`,"
            f" under the package's `data/skills/` directory; link them into an agent"
            f" without network access with `skill link-skills <that directory>`.\n"
        )
    return "".join(parts)


def _render_subagents(subagents, source_base) -> str:
    if not subagents:
        return ""
    parts = [SUBAGENTS_HEADER]
    for agent in subagents:
        parts.append(f"\n### `{agent.name}`\n")
        if agent.description:
            parts.append(f"\n{agent.description}\n")
        details = [f"Source: {_source_link(agent.source, source_base)}"]
        if agent.tools:
            details.append(f"tools: `{agent.tools}`")
        parts.append("\n" + "; ".join(details) + ".\n")
    return "".join(parts)


def _render_instructions(files, source_base) -> str:
    if not files:
        return ""
    lines = [INSTRUCTIONS_HEADER, "\n"]
    for item in files:
        suffix = "/" if item.is_dir and not item.source.endswith("/") else ""
        lines.append(
            f"- {_source_link(item.source + suffix, source_base)}: read by {item.audience}\n"
        )
    return "".join(lines)


def _render_outputs(outputs) -> str:
    if not outputs:
        return ""
    lines = [OUTPUTS_HEADER, "\n"]
    for output in outputs:
        if output.url:
            target = f"[`{output.filename}`]({output.url})"
        elif "<" in output.filename:
            target = f"`{output.filename}`"
        else:
            # Raw HTML: MyST would read a relative .md/.txt link as a missing page.
            target = f'<a href="{output.filename}"><code>{output.filename}</code></a>'
        lines.append(f"- {target}: {output.description}\n")
    return "".join(lines)


# --------------------------------------------------------------------------
# The PageSpec seam
# --------------------------------------------------------------------------


def ai_artifacts_page(config, *, artifacts: AIArtifacts | None = None):
    """The "For AI agents" :class:`~epythet.scaffold.PageSpec` for a project, or ``None``.

    ``None`` when ``config.ai_artifacts`` is off, when the ``EPYTHET_AI_ARTIFACTS``
    environment variable is ``0``/``false`` (the fleet-wide switch), or when no
    artifact was found. The template is ``config.ai_artifacts_template`` (a
    file, relative to the project root) when set, else :data:`DEFAULT_TEMPLATE`.

    :raises ConfigError: when the template file is missing or has a field the
        renderer does not provide (literal braces must be doubled: ``{{``).
    """
    from epythet.scaffold import PageSpec

    if not getattr(config, "ai_artifacts", True) or not enabled_by_environment():
        return None
    if artifacts is None:
        artifacts = discover_artifacts(
            config.project_dir, package_dir=config.package_dir
        )
    if not artifacts:
        return None
    template = DEFAULT_TEMPLATE
    template_path = getattr(config, "ai_artifacts_template", "")
    if template_path:
        path = config.project_dir / template_path
        if not path.is_file():
            raise ConfigError(
                f"[tool.epythet] ai_artifacts_template points at {path}, "
                "which does not exist"
            )
        template = path.read_text(encoding="utf-8")
        if templates.INDEX_MARKER not in template and "{marker}" not in template:
            template = "{marker}\n\n" + template
    try:
        content = render_ai_artifacts_page(artifacts, config, template=template)
    except (KeyError, IndexError, ValueError) as e:
        raise ConfigError(
            f"ai_artifacts_template {template_path or '(default)'}: unknown field "
            f"{e}; the fields are {sorted(TEMPLATE_FIELDS)} and literal braces "
            "must be doubled ({{ and }})"
        ) from e
    return PageSpec(PAGE_FILENAME, content, marker=templates.INDEX_MARKER)


def enabled_by_environment() -> bool:
    """False when ``EPYTHET_AI_ARTIFACTS`` is set to ``0``, ``false``, ``no`` or ``off``.

    >>> os.environ[DISABLE_ENV] = "0"; enabled_by_environment()
    False
    >>> del os.environ[DISABLE_ENV]; enabled_by_environment()
    True
    """
    return os.environ.get(DISABLE_ENV, "").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def default_pages(config) -> list:
    """The generated pages a scaffold gets when the caller passes none."""
    page = ai_artifacts_page(config)
    return [page] if page is not None else []


def artifacts_json(artifacts: AIArtifacts) -> str:
    """``artifacts`` as indented JSON (the ``--format json`` CLI output)."""
    return json.dumps(artifacts.to_dict(), indent=2)


def artifacts_table(artifacts: AIArtifacts, *, repo_stub: str = "") -> str:
    """A plain-text listing of ``artifacts`` (the default CLI output)."""
    lines = [f"AI artifacts under {artifacts.project_dir}"]
    lines.append(f"\nSkills ({len(artifacts.skills)})")
    for skill in artifacts.skills:
        flags = ", ".join(
            f
            for f, on in (("shipped", skill.shipped), ("gh skill", skill.installable))
            if on
        )
        lines.append(f"  {skill.name:<32} {skill.source}  [{flags}]")
        command = skill.install_command(repo_stub)
        if command:
            lines.append(f"  {'':<32} {command}")
    lines.append(f"\nSubagents ({len(artifacts.subagents)})")
    for agent in artifacts.subagents:
        lines.append(f"  {agent.name:<32} {agent.source}")
    lines.append(f"\nInstruction files ({len(artifacts.instruction_files)})")
    for item in artifacts.instruction_files:
        lines.append(f"  {item.source:<32} {item.audience}")
    return "\n".join(lines)
