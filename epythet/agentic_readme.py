"""Check that a README documents a project's agentic aspects; render and place the section.

A project that ships skills, subagents or instruction files, and whose site
publishes agent-readable documentation (``llms.txt``, ``<package>.md``), should
say so in its README: that is where an agent arriving at the repository looks
first. :func:`check_readme` reuses :func:`epythet.ai_artifacts.discover_artifacts`
to learn what exists and reads the README to see whether each kind is mentioned
(a ``gh skill install`` line, a skill or agent name, ``CLAUDE.md``, ``llms.txt``,
a heading about agents). The result is a :class:`ReadmeReport`: one
:class:`KindCheck` per kind, each ``ok``, ``warn`` or ``n/a``. The check is a
heuristic: a mention counts whatever the sentence around it says.

:func:`render_section` produces the README section from the effective snippets
(:mod:`epythet.userconfig`: the user's ``agentic-readme-section.md`` and
``agentic-readme-humor.md`` over the packaged defaults) and the effective
:class:`~epythet.userconfig.ReadmePolicy` (the user's ``config.toml``, with a
project's ``[tool.epythet.readme]`` keys on top so a committed README does not
depend on who ran the tool). :func:`place_section` puts it between two marker
comments so a later run updates it in place: before the first heading after the
title when ``agentic_first`` is on, at the end otherwise. The "for humans" line
links to the heading that follows the section.

>>> readme = "# pkg\\n\\nTagline.\\n\\n# Install\\n\\npip install pkg\\n"
>>> start, end, heading, level = place_section(readme, agentic_first=True)
>>> readme[start:end], heading.title, level
('', 'Install', 1)
>>> humans_link_for(heading)
'[Install](#install)'
"""

from __future__ import annotations

import json
import re
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from epythet.ai_artifacts import (
    DEFAULT_AGENT_HOST,
    AIArtifacts,
    agent_outputs_for,
    discover_artifacts,
    enabled_by_environment,
    repo_stub_for,
    site_url_for,
)
from epythet.config import ConfigError
from epythet.userconfig import (
    ReadmePolicy,
    UserConfig,
    load_user_config,
    pool_lines,
    snippet_text,
)

#: The comments that delimit the generated section in a README (each on its own line).
MARKER_START = "<!-- epythet:agentic-readme:start -->"
MARKER_END = "<!-- epythet:agentic-readme:end -->"
#: README filenames, in order of preference.
README_NAMES = (
    "README.md",
    "readme.md",
    "README.markdown",
    "README.rst",
    "README.txt",
    "README",
)
#: The kinds a check reports on, in display order.
KINDS = ("skills", "subagents", "instruction_files", "agent_docs", "section")
#: The snippet names the section is rendered from. A project whose only agentic
#: aspect is its agent-readable documentation gets the shorter docs-only variant:
#: it ships no tooling, so the section must not say it does.
SECTION_SNIPPET = "agentic-readme-section"
DOCS_ONLY_SECTION_SNIPPET = "agentic-readme-section-docs-only"
HUMOR_SNIPPET = "agentic-readme-humor"
INSTRUCTION_SNIPPET = "agentic-readme-instruction"
#: The opener used when ``humor`` is off.
NEUTRAL_INTRO = "If you are a human"
#: Longest blurb (first sentence of a description) shown per skill or agent.
MAX_BLURB = 140
#: Skill name suffixes that make a skill the one named in the install line.
HEADLINE_SUFFIXES = ("-setup", "-quickstart", "-start")
#: The fields a section snippet may use.
SECTION_FIELDS = frozenset(
    {
        "marker_start",
        "marker_end",
        "heading",
        "name",
        "repo_stub",
        "site_url",
        "skills_block",
        "subagents_block",
        "instructions_block",
        "docs_block",
        "for_humans_intro",
        "humans_link",
    }
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_AGENT_HEADING_RE = re.compile(r"\bagents?\b|\bagentic\b|\bllms?\b", re.IGNORECASE)


class SectionError(ValueError):
    """The README or a snippet is in a state the tool will not write over.

    Raised for unpaired or repeated markers, a README that is not UTF-8 or not
    Markdown, and a section snippet that fails to format or drops the markers.
    """


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class KindCheck:
    """One artifact kind: whether the project has it and whether the README covers it."""

    kind: str
    present: bool
    documented: bool
    items: tuple[str, ...] = ()
    evidence: str = ""

    @property
    def status(self) -> str:
        """``n/a`` when absent from the project, else ``ok`` or ``warn``."""
        if not self.present:
            return "n/a"
        return "ok" if self.documented else "warn"


@dataclass(frozen=True)
class ReadmeReport:
    """The outcome of :func:`check_readme` for one project.

    ``policy`` is the effective :class:`ReadmePolicy`; ``user_config`` and
    ``project_overrides`` are where it came from.
    """

    project_dir: Path
    readme: Path | None
    checks: tuple[KindCheck, ...]
    policy: ReadmePolicy
    user_config: UserConfig
    project_overrides: Mapping[str, Any]

    @property
    def warnings(self) -> tuple[KindCheck, ...]:
        """The kinds present in the project but missing from the README."""
        return tuple(c for c in self.checks if c.status == "warn")

    @property
    def status(self) -> str:
        """``warn`` when anything present is undocumented, else ``ok``."""
        return "warn" if self.warnings else "ok"

    def to_dict(self) -> dict:
        """A JSON-ready view (``--format json``)."""
        return {
            "project_dir": str(self.project_dir),
            "readme": str(self.readme) if self.readme else None,
            "status": self.status,
            "policy": self.user_config.to_dict(self.project_overrides),
            "checks": [{**asdict(c), "status": c.status} for c in self.checks],
        }

    def table(self) -> str:
        """The plain-text listing (the default CLI output)."""
        lines = [f"Agentic aspects of {self.project_dir}"]
        lines.append(f"README: {self.readme.name if self.readme else 'none found'}")
        source = (
            f"  ({self.user_config.path})"
            if self.user_config.path
            else "  (packaged defaults)"
        ) + ("  + [tool.epythet.readme]" if self.project_overrides else "")
        lines.append(
            f"policy: agentic_aspects={self.policy.agentic_aspects} humor={self.policy.humor} "
            f"agentic_first={self.policy.agentic_first}{source}"
        )
        lines.append("")
        lines.append(f"{'kind':<18} {'status':<6} {'in project':<28} evidence")
        for check in self.checks:
            items = (
                ", ".join(check.items)
                if check.items
                else ("yes" if check.present else "-")
            )
            lines.append(
                f"{check.kind:<18} {check.status:<6} {_shorten(items, 28):<28} {check.evidence}"
            )
        lines.append("")
        if self.warnings:
            kinds = ", ".join(c.kind for c in self.warnings)
            lines.append(f"warn: the README does not document: {kinds}")
        else:
            lines.append("ok: every agentic aspect present is documented in the README")
        return "\n".join(lines)


def _shorten(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


# --------------------------------------------------------------------------
# The project: README, config, artifacts, effective policy
# --------------------------------------------------------------------------


def find_readme(project_dir: str | Path) -> Path | None:
    """The project's README, by the usual names (``None`` when there is none)."""
    root = Path(project_dir)
    for name in README_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def read_readme(path: Path) -> tuple[str, str]:
    """``(text, newline)``: the README with ``\\n`` line ends, and the style to write back.

    :raises SectionError: when the file is not UTF-8
    """
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as e:
        raise SectionError(
            f"{path.name} is not UTF-8 ({e}); only UTF-8 READMEs are edited"
        ) from e
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), newline


def load_project(project_dir: str | Path):
    """``(config, artifacts)`` for a project; ``config`` is ``None`` for a non-Python tree.

    A tree without ``pyproject.toml`` or ``setup.cfg`` is inspected without a
    config. A tree that has one but cannot be loaded raises
    :class:`~epythet.config.ConfigError`: a broken ``[tool.epythet]`` must not
    silently change what gets written.
    """
    from epythet.config import load_config

    root = Path(project_dir)
    if not (root / "pyproject.toml").is_file() and not (root / "setup.cfg").is_file():
        return None, discover_artifacts(root, package_dir=None)
    config = load_config(root)
    return config, discover_artifacts(root, package_dir=config.package_dir)


@dataclass(frozen=True)
class Project:
    """What every entry point needs once: config, artifacts, README, effective policy."""

    root: Path
    config: Any
    artifacts: AIArtifacts
    readme: Path | None
    user_config: UserConfig
    policy: ReadmePolicy
    project_overrides: Mapping[str, Any]


def load(
    project_dir: str | Path,
    *,
    config=None,
    artifacts: AIArtifacts | None = None,
    user_config: UserConfig | None = None,
) -> Project:
    """Resolve a project once; each argument given is used instead of being loaded."""
    root = Path(project_dir).absolute()
    if artifacts is None or config is None:
        loaded_config, loaded_artifacts = load_project(root)
        config = config if config is not None else loaded_config
        artifacts = artifacts if artifacts is not None else loaded_artifacts
    user_config = user_config if user_config is not None else load_user_config()
    overrides = (
        dict(getattr(config, "readme", None) or {}) if config is not None else {}
    )
    return Project(
        root,
        config,
        artifacts,
        find_readme(root),
        user_config,
        user_config.readme_for(overrides),
        overrides,
    )


# --------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------


def check_readme(
    project_dir: str | Path,
    *,
    config=None,
    artifacts: AIArtifacts | None = None,
    user_config: UserConfig | None = None,
) -> ReadmeReport:
    """Which agentic aspects the project has, and whether its README mentions each.

    :param config: the :class:`~epythet.config.DocsConfig` (loaded when omitted)
    :param artifacts: discovery result (computed when omitted)
    :param user_config: the user's policy (read from the config dir when omitted)
    """
    project = load(
        project_dir, config=config, artifacts=artifacts, user_config=user_config
    )
    text = (
        project.readme.read_text(encoding="utf-8", errors="replace")
        if project.readme
        else ""
    )
    return ReadmeReport(
        project.root,
        project.readme,
        tuple(_checks_for(project.artifacts, project.config, text)),
        project.policy,
        project.user_config,
        project.project_overrides,
    )


def _mentioned(text: str, needle: str) -> bool:
    """``needle`` in ``text`` as a whole token (not inside a longer word or name).

    >>> _mentioned("use pages-tool", "pages"), _mentioned("the pages skill", "pages")
    (False, True)
    """
    return bool(
        re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", text, re.IGNORECASE)
    )


def _checks_for(artifacts, config, text) -> Iterator[KindCheck]:
    headings = [h.title for h in headings_of(text)]
    agent_headings = [h for h in headings if _AGENT_HEADING_RE.search(h)]

    def mentions(*needles) -> list[str]:
        return [n for n in needles if n and _mentioned(text, n)]

    skills = artifacts.skills
    hits = mentions("gh skill install", *(s.name for s in skills))
    yield KindCheck(
        "skills",
        bool(skills),
        bool(hits),
        tuple(s.name for s in skills),
        _evidence(hits, "no `gh skill install` line and no skill name"),
    )
    agents = artifacts.subagents
    hits = mentions(
        "subagent", "subagents", "sub-agent", "sub-agents", *(a.name for a in agents)
    )
    yield KindCheck(
        "subagents",
        bool(agents),
        bool(hits),
        tuple(a.name for a in agents),
        _evidence(hits, "no subagent name"),
    )
    files = artifacts.instruction_files
    names = tuple(f.source for f in files)
    hits = mentions(*(f.source if f.is_dir else Path(f.source).name for f in files))
    yield KindCheck(
        "instruction_files",
        bool(files),
        bool(hits),
        names,
        _evidence(hits, "no instruction file named"),
    )
    agent_docs = [
        o.filename for o in _published_outputs(config) if o.kind != "objects_inv"
    ]
    hits = mentions(*agent_docs, "objects.inv", ".md twin", "ai-agents.html")
    yield KindCheck(
        "agent_docs",
        bool(agent_docs),
        bool(hits),
        tuple(agent_docs),
        _evidence(hits, "no `llms.txt`, `<package>.md` or `objects.inv` mention"),
    )
    anything = bool(skills or agents or files or agent_docs)
    if marker_span(text, strict=False) is not None:
        evidence, documented = "epythet section markers", True
    elif agent_headings:
        evidence, documented = f"heading {agent_headings[0]!r}", True
    else:
        evidence, documented = "no heading about agents", False
    yield KindCheck("section", anything, documented, (), evidence)


def _published_outputs(config) -> list:
    """The agent-readable outputs the project publishes at a known URL (else none).

    Without a GitHub URL there is no site to point at, so the outputs are not
    an aspect the README can be asked to document.
    """
    if config is None or not site_url_for(config.repo_url):
        return []
    return agent_outputs_for(config)


def _evidence(hits: list[str], missing: str) -> str:
    return "mentions " + ", ".join(f"`{h}`" for h in hits[:4]) if hits else missing


# --------------------------------------------------------------------------
# README structure: headings and markers outside fences, placement, anchors
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Heading:
    """A Markdown ATX heading: its line index, level and title text."""

    line: int
    level: int
    title: str


def _lines_outside_fences(lines: list[str]) -> Iterator[tuple[int, str]]:
    fence = None
    for index, line in enumerate(lines):
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is None:
            yield index, line


def headings_of(text: str) -> list[Heading]:
    """Every ATX heading outside fenced code blocks.

    >>> [h.title for h in headings_of("# A\\n```\\n# not one\\n```\\n## B\\n")]
    ['A', 'B']
    """
    found = []
    for index, line in _lines_outside_fences(text.splitlines()):
        match = _HEADING_RE.match(line)
        if match:
            found.append(Heading(index, len(match.group(1)), match.group(2).strip()))
    return found


def marker_span(text: str, *, strict: bool = True) -> tuple[int, int] | None:
    """The character span of the marked section (``None`` when there is none).

    Markers count only on their own line outside fenced code, so a README that
    shows them in an example is not mistaken for one that has the section.

    :param strict: raise :class:`SectionError` on an unpaired or repeated marker
        (``False``: report such a README as having no section)
    """
    lines = text.splitlines(keepends=True)
    offsets = _line_offsets(lines)
    starts, ends = [], []
    for index, line in _lines_outside_fences(lines):
        stripped = line.strip()
        if stripped == MARKER_START:
            starts.append(index)
        elif stripped == MARKER_END:
            ends.append(index)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        if not strict:
            return None
        raise SectionError(
            f"the README has unpaired or repeated epythet markers ({len(starts)} start, "
            f"{len(ends)} end); fix them by hand before writing the section"
        )
    return offsets[starts[0]], offsets[ends[0] + 1]


def github_anchor(title: str) -> str:
    """GitHub's anchor for a heading title.

    >>> github_anchor("For AI agents"), github_anchor("What it *fixes*: `x`")
    ('for-ai-agents', 'what-it-fixes-x')
    >>> github_anchor("my_function and [links](https://x)")
    'my_function-and-links'
    """
    cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)
    cleaned = re.sub(r"[`*]", "", cleaned).strip().lower()
    cleaned = re.sub(r"[^\w\- ]", "", cleaned)
    return cleaned.replace(" ", "-")


def humans_link_for(heading: Heading | None) -> str:
    """``[Title](#anchor)`` for the heading after the section, or a plain fallback."""
    if heading is None:
        return "the top of the page"
    return f"[{heading.title}](#{github_anchor(heading.title)})"


def place_section(
    text: str, *, agentic_first: bool
) -> tuple[int, int, Heading | None, int]:
    """Where the section goes in ``text``: ``(start, end, next_heading, level)``.

    ``text[start:end]`` is the span to replace: the existing marked section when
    there is one (its position is kept, wherever the author moved it), else an
    empty span right before the first heading after the title (``agentic_first``)
    or at the end of the file. ``next_heading`` is the heading that follows the
    span (the "for humans" target) and ``level`` the heading level the section
    should use to sit among its siblings. Headings inside the existing section
    are ignored, so rewriting never changes the level.

    :raises SectionError: on unpaired markers
    """
    offsets = _line_offsets(text.splitlines(keepends=True))
    span = marker_span(text)
    if span is not None:
        start, end = span
        outside = [h for h in headings_of(text) if not start <= offsets[h.line] < end]
        next_heading = next((h for h in outside if offsets[h.line] >= end), None)
        return start, end, next_heading, _section_level(outside, next_heading)
    headings = headings_of(text)
    if agentic_first and len(headings) >= 2:
        target = headings[1]
        return (
            offsets[target.line],
            offsets[target.line],
            target,
            _section_level(headings, target),
        )
    return len(text), len(text), None, _section_level(headings, None)


def _line_offsets(lines: list[str]) -> list[int]:
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line)
    offsets.append(total)
    return offsets


def _section_level(headings: list[Heading], next_heading: Heading | None) -> int:
    if next_heading is not None:
        return next_heading.level
    if len(headings) >= 2:
        return headings[1].level
    if headings:
        return min(headings[0].level + 1, 6)
    return 1


def splice_section(text: str, section: str, *, start: int, end: int) -> str:
    """``text`` with ``section`` in place of ``text[start:end]``, blank lines kept sane."""
    before, after = text[:start], text[end:]
    if before and not before.endswith("\n"):
        before += "\n"
    if before and not before.endswith("\n\n"):
        before += "\n"
    block = section.strip("\n") + "\n"
    if after and not after.startswith("\n"):
        block += "\n"
    return before + block + after


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_section(
    artifacts: AIArtifacts,
    config,
    *,
    policy: ReadmePolicy,
    level: int = 1,
    humans_link: str = "the top of the page",
    snippets: Callable[[str], str] = snippet_text,
    agent: str = DEFAULT_AGENT_HOST,
) -> str:
    """The README section for ``artifacts``, from the effective snippets and ``policy``.

    :param level: heading level (``1`` renders ``# For AI agents``)
    :param humans_link: what the "for humans" sentence points at
    :param snippets: ``name -> text`` resolver (the seam tests use to inject text)
    :param agent: the host named in the ``gh skill install`` line
    :raises SectionError: when the section snippet fails to format or drops a marker
    """
    name = config.name if config is not None else artifacts.project_dir.name
    repo_stub = repo_stub_for(config.repo_url) if config is not None else ""
    site_url = site_url_for(config.repo_url) if config is not None else ""
    snippet_name = section_snippet_for(artifacts)
    template = snippets(snippet_name)
    fields = dict(
        marker_start=MARKER_START,
        marker_end=MARKER_END,
        heading="#" * max(1, min(level, 6)),
        name=name,
        repo_stub=repo_stub,
        site_url=site_url,
        skills_block=_skills_block(artifacts, repo_stub, agent),
        subagents_block=_subagents_block(artifacts),
        instructions_block=_instructions_block(artifacts),
        docs_block=_docs_block(config, artifacts, site_url),
        for_humans_intro=_for_humans_intro(name, policy, snippets(HUMOR_SNIPPET)),
        humans_link=humans_link,
    )
    try:
        rendered = template.format(**fields)
    except Exception as e:  # str.format raises Key/Index/Value/Attribute/TypeError
        raise SectionError(
            f"snippet {snippet_name!r} does not format: {e!r}; the fields are "
            f"{sorted(SECTION_FIELDS)} and literal braces must be doubled ({{{{ and }}}})"
        ) from e
    rendered = rendered.strip("\n") + "\n"
    if marker_span(rendered, strict=False) != (0, len(rendered)):
        raise SectionError(
            f"snippet {snippet_name!r} must start with {{marker_start}} and end with "
            "{marker_end}, each on its own line, or the section cannot be updated in place"
        )
    return rendered


def ships_tooling(artifacts: AIArtifacts) -> bool:
    """Whether the project ships anything an agent installs or reads as instructions.

    Skills, subagents and instruction files count; published agent-readable
    documentation (``llms.txt``, ``<package>.md``) does not, because it is a
    view of the docs rather than tooling.
    """
    return bool(artifacts.skills or artifacts.subagents or artifacts.instruction_files)


def section_snippet_for(artifacts: AIArtifacts) -> str:
    """The name of the section snippet ``artifacts`` calls for.

    :data:`SECTION_SNIPPET` when the project ships tooling, else the shorter
    :data:`DOCS_ONLY_SECTION_SNIPPET`, which makes no "ships tooling" claim.
    """
    return SECTION_SNIPPET if ships_tooling(artifacts) else DOCS_ONLY_SECTION_SNIPPET


def _for_humans_intro(name: str, policy: ReadmePolicy, pool_text: str) -> str:
    """The opener: a stable pick from the humour pool when ``humor`` is on, else neutral."""
    lines = pool_lines(pool_text) if policy.humor else []
    if not lines:
        return NEUTRAL_INTRO
    return lines[zlib.crc32(name.encode("utf-8")) % len(lines)].rstrip(",.;: ")


def blurb(description: str, *, max_length: int = MAX_BLURB) -> str:
    """The first sentence of a skill or agent description, short enough for a table cell.

    >>> blurb("Find and fix things. Use when asked to fix.")
    'find and fix things'
    >>> blurb("Do the thing and then some: a, b, c, " + "and more " * 30)
    'do the thing and then some'
    """
    text = " ".join(description.split())
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].rstrip(".!?")
    if len(first) > max_length:
        first = _first_clause(first, max_length)
    if first[:1].isupper() and not first[:2].isupper():
        first = first[:1].lower() + first[1:]
    return first


def _first_clause(text: str, max_length: int) -> str:
    """Cut at the first clause boundary (colon, semicolon, comma, parenthesis) past 20 characters, else at a word."""
    boundaries = [m.start() for m in re.finditer(r"[:;,]| \(", text) if m.start() >= 20]
    if boundaries and boundaries[0] < max_length:
        return text[: boundaries[0]]
    cut = text.rfind(" ", 0, max_length)
    return text[: cut if cut > 0 else max_length].rstrip(",;: ") + "…"


def headline_skill(skills):
    """The skill named in the install line: a ``*-setup``-like one if any, else the first installable."""
    installable = [s for s in skills if s.installable]
    for suffix in HEADLINE_SUFFIXES:
        for skill in installable:
            if skill.name.endswith(suffix):
                return skill
    return installable[0] if installable else None


def _skills_block(artifacts: AIArtifacts, repo_stub: str, agent: str) -> str:
    skills = artifacts.skills
    if not skills:
        return ""
    parts = [
        "\n**Skills** ([Agent Skills](https://agentskills.io) format), for any agent host."
    ]
    headline = headline_skill(skills)
    command = headline.install_command(repo_stub, agent=agent) if headline else None
    if command:
        parts[0] += " Install one with `gh skill`:"
        parts.append(
            f"\n```bash\n{command}   # or copilot, cursor, codex, gemini\n```\n"
        )
    else:
        parts[0] += "\n"
    parts.append("\n| Skill | Use it to |\n|---|---|\n")
    for skill in skills:
        parts.append(
            f"| `{skill.name}` | {blurb(skill.description) or skill.source} |\n"
        )
    if any(s.shipped for s in skills):
        folder = Path(next(s.source for s in skills if s.shipped)).parent.as_posix()
        parts.append(f"\nThe same skills are inside the wheel, under `{folder}/`.\n")
    return "".join(parts)


def _subagents_block(artifacts: AIArtifacts) -> str:
    agents = artifacts.subagents
    if not agents:
        return ""
    described = ", ".join(
        f"`{a.name}`" + (f" ({blurb(a.description)})" if a.description else "")
        for a in agents
    )
    folder = Path(agents[0].source).parent.as_posix()
    return (
        f"\n**Subagents**: {described}, in `{folder}/`. Copy one into your project's "
        "`.claude/agents/` (or your host's equivalent).\n"
    )


def _instructions_block(artifacts: AIArtifacts) -> str:
    files = artifacts.instruction_files
    if not files:
        return ""
    listed = ", ".join(f"`{f.source}` ({f.audience})" for f in files)
    return f"\n**Instruction files**: {listed}.\n"


def _docs_block(config, artifacts: AIArtifacts, site_url: str) -> str:
    outputs = {o.kind: o for o in _published_outputs(config)}
    if "llms" not in outputs:
        return ""

    def link(kind):
        output = outputs[kind]
        return (
            f"[`{output.filename}`]({output.url})"
            if output.url
            else f"`{output.filename}`"
        )

    parts = [
        f"\n**The documentation, machine-readable**: {link('llms')} indexes every page"
    ]
    if "aggregate_md" in outputs:
        parts.append(f"; {link('aggregate_md')} is the whole documentation in one file")
    parts.append("; every page has a `.md` twin")
    if "objects_inv" in outputs:
        parts.append(f"; {link('objects_inv')} maps symbols to URLs")
    parts.append(".")
    page_on = getattr(config, "ai_artifacts", True) and enabled_by_environment()
    if site_url and page_on and artifacts:
        parts.append(
            f" The full list, with install lines, is on the site's "
            f"[For AI agents]({site_url}ai-agents.html) page."
        )
    return "".join(parts) + "\n"


def instruction_text(*, snippets: Callable[[str], str] = snippet_text) -> str:
    """The instruction the skill hands an agent when the policy is ``add``."""
    return snippets(INSTRUCTION_SNIPPET)


# --------------------------------------------------------------------------
# Draft and write
# --------------------------------------------------------------------------


def draft_section(
    project_dir: str | Path,
    *,
    user_config: UserConfig | None = None,
    config=None,
    artifacts: AIArtifacts | None = None,
) -> tuple[str, str, int, int]:
    """Render the section for a project as it would be placed: ``(section, readme_text, start, end)``.

    ``readme_text`` is the current README (``""`` when none exists); ``start``
    and ``end`` delimit the span the section replaces.

    :raises SectionError: on unpaired markers, a non-UTF-8 README, or a broken snippet
    """
    project = load(
        project_dir, config=config, artifacts=artifacts, user_config=user_config
    )
    text = read_readme(project.readme)[0] if project.readme else ""
    start, end, next_heading, level = place_section(
        text, agentic_first=project.policy.agentic_first
    )
    section = render_section(
        project.artifacts,
        project.config,
        policy=project.policy,
        level=level,
        humans_link=humans_link_for(next_heading),
    )
    return section, text, start, end


def write_section(
    project_dir: str | Path, *, user_config: UserConfig | None = None
) -> tuple[Path, str]:
    """Add or update the marked section in the project's README; returns ``(path, outcome)``.

    ``outcome`` is ``added``, ``updated`` or ``unchanged``. The README must be
    Markdown (``README.md``); a missing README is created with the section alone.
    Line endings are kept as found (CRLF stays CRLF).

    :raises SectionError: when there is nothing agentic to document, the README is
        not Markdown or not UTF-8, it has unpaired markers, or the snippet is broken
    """
    root = Path(project_dir).absolute()
    readme = find_readme(root)
    if readme is not None and readme.suffix.lower() not in (".md", ".markdown"):
        raise SectionError(f"{readme.name} is not Markdown; only README.md is edited")
    project = load(root, user_config=user_config)
    if not project.artifacts and not _published_outputs(project.config):
        raise SectionError(
            "nothing agentic to document: no skills, subagents, instruction files, "
            "or published agent-readable docs (a GitHub URL is needed for the latter)"
        )
    section, text, start, end = draft_section(
        root,
        user_config=project.user_config,
        config=project.config,
        artifacts=project.artifacts,
    )
    newline = read_readme(readme)[1] if readme is not None else "\n"
    new_text = splice_section(text, section, start=start, end=end)
    target = readme or root / "README.md"
    if readme is not None and new_text == text:
        return target, "unchanged"
    target.write_bytes(new_text.replace("\n", newline).encode("utf-8"))
    return target, "updated" if marker_span(text, strict=False) else "added"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def ai_readme_check(
    project_dir,
    *,
    format: str = "table",
    fail_on: str = "",
    draft: bool = False,
    write: bool = False,
):
    """Report whether the README documents the project's agentic aspects; draft or write the section.

    Reuses ``epythet ai-artifacts`` discovery (skills, subagents, instruction
    files) plus the agent-readable outputs the site publishes, and looks for
    each in the README: a ``gh skill install`` line or skill name, a subagent
    name, ``CLAUDE.md`` / ``AGENTS.md``, ``llms.txt`` / ``<package>.md``, and a
    heading about agents (or epythet's own section markers). The effective
    policy (``~/.config/epythet/config.toml`` ``[readme]``, overridden by the
    project's ``[tool.epythet.readme]``) is part of the output so a skill can
    read it. ``--write`` is explicit: it writes whatever the policy says.

    :param project_dir: the project root
    :param format: table (human) or json
    :param fail_on: ``warn`` to exit 1 when anything present is undocumented (default: exit 0)
    :param draft: print the README section rendered from the effective snippets and policy, without writing
    :param write: add or update the section in ``README.md`` between epythet's markers
    """
    import cw

    if format not in ("table", "json"):
        raise cw.CommandError("--format must be table or json", code=2)
    if fail_on not in ("", "warn"):
        raise cw.CommandError("--fail-on must be warn (or omitted)", code=2)
    if draft and write:
        raise cw.CommandError("--draft and --write are exclusive", code=2)
    if not Path(project_dir).is_dir():
        raise cw.CommandError(f"not a directory: {project_dir}", code=2)
    try:
        user_config = load_user_config()
        if draft:
            section, _, _, _ = draft_section(project_dir, user_config=user_config)
            print(section, end="")
            return
        written = write_section(project_dir, user_config=user_config) if write else None
        report = check_readme(project_dir, user_config=user_config)
    except (SectionError, ConfigError, KeyError, OSError) as e:
        raise cw.CommandError(str(e.args[0] if e.args else e), code=2) from e
    if format == "json":
        data = report.to_dict()
        if written:
            data["write"] = {"path": str(written[0]), "outcome": written[1]}
        print(json.dumps(data, indent=2))
    else:
        if written:
            print(f"{written[1]}: {written[0]}")
        print(report.table())
    if fail_on == "warn" and report.warnings:
        raise cw.CommandError(
            f"undocumented agentic aspects: {', '.join(c.kind for c in report.warnings)}",
            code=1,
        )
