"""Command line access to epythet.

``epythet quickstart PROJECT_DIR [--ignore ...]`` is the command the
``publish-github-pages`` action runs: it scaffolds ``docsrc``, builds the HTML
and writes it to ``PROJECT_DIR/docsrc/_build/html``.
"""

import cw

from epythet.build import build, make
from epythet.config import load_config, split_ignore
from epythet.scaffold import make_autodocs, make_docsrc, scaffold
from epythet.validation.cli import validate


def quickstart(project_dir, *, ignore: list[str] = None):
    """Scaffold docsrc and build the HTML documentation in one go.

    Equivalent to ``make-docsrc`` then ``make html``, with ``ignore`` applied
    to the API generator. An empty ``ignore`` (the action passes ``--ignore``
    with no values when its input is unset, or ``""``) means "use the configured
    default"; each value may itself be comma-separated.

    :param project_dir: Path to root project directory (pyproject.toml or setup.cfg)
    :param ignore: skip file if path contains any ignore strings
    """
    # No values (the action's unset input) or only empty strings: keep the default.
    ignore = split_ignore(ignore or ())
    overrides = {"ignore": list(ignore)} if ignore else {}
    config = load_config(project_dir, **overrides)
    scaffold(config, verbose=True)
    return build(config, "html", overrides=overrides)


def check_pages(repo, *, no_url_check: bool = False):
    """Diagnose GitHub Pages setup for a repo.

    :param repo: GitHub repo as 'owner/repo', or path to a local git checkout.
    :param no_url_check: Skip checking if the docs URL actually responds.
    """
    from epythet.tools.published_docs import check_pages_setup

    repo_stub = _resolve_repo_stub(repo)
    result = check_pages_setup(repo_stub, check_url=not no_url_check)
    print(result["diagnosis"])
    for key in (
        "gh_pages_branch_exists",
        "pages_enabled",
        "source_branch",
        "source_path",
        "correctly_configured",
        "docs_url",
        "docs_url_responding",
    ):
        print(f"  {key}: {result[key]}")


def configure_pages(repo, *, branch: str = "gh-pages", path: str = "/"):
    """Enable or fix GitHub Pages for a repo. Requires gh CLI or GITHUB_TOKEN.

    :param repo: GitHub repo as 'owner/repo', or path to a local git checkout.
    :param branch: Branch to serve Pages from (default: gh-pages).
    :param path: Folder within the branch (default: /).
    """
    from epythet.tools.published_docs import enable_pages

    repo_stub = _resolve_repo_stub(repo)
    result = enable_pages(repo_stub, branch=branch, path=path)
    if result is not None:
        org = repo_stub.split("/")[0]
        repo_name = repo_stub.split("/")[1]
        print(f"Pages enabled for {repo_stub}.")
        print(f"  URL: https://{org}.github.io/{repo_name}")
    else:
        print(f"Failed to enable Pages for {repo_stub}.")


def ai_artifacts(project_dir, *, format: str = "table"):
    """List the AI agent artifacts a project ships (skills, subagents, instruction files).

    Looks where agents and ``gh skill`` look: ``<pkg>/data/skills``, ``skills/``,
    ``.claude/skills``, ``<pkg>/data/agents``, ``.claude/agents``, ``CLAUDE.md``,
    ``AGENTS.md``, ``.cursor/rules``, ``.codex``. The same discovery feeds the
    generated "For AI agents" documentation page.

    :param project_dir: the project root
    :param format: table (human) or json
    """
    from epythet.ai_artifacts import (
        artifacts_json,
        artifacts_table,
        discover_artifacts,
        repo_stub_for,
    )

    if format not in ("table", "json"):
        raise cw.CommandError("--format must be table or json", code=2)
    try:
        config = load_config(project_dir)
        package_dir, repo_stub = config.package_dir, repo_stub_for(config.repo_url)
    except Exception:  # not a Python project: still list what is there
        package_dir, repo_stub = None, ""
    found = discover_artifacts(project_dir, package_dir=package_dir)
    if format == "json":
        print(artifacts_json(found))
    else:
        print(artifacts_table(found, repo_stub=repo_stub))


def _resolve_repo_stub(repo):
    """Resolve a repo argument to an owner/repo slug."""
    if "/" in repo and not repo.startswith("/") and not repo.startswith("."):
        # Looks like owner/repo already
        return repo
    # Try as a local directory
    from epythet.tools.published_docs import repo_stub_from_local_dir

    stub = repo_stub_from_local_dir(repo)
    if stub is None:
        raise ValueError(
            f"Could not determine GitHub repo from '{repo}'. "
            "Pass 'owner/repo' directly or point to a local git checkout."
        )
    return stub


#: The commands ``epythet`` exposes, in the order they appear in ``--help``.
COMMANDS = [
    make_docsrc,
    make_autodocs,
    make,
    quickstart,
    check_pages,
    configure_pages,
    validate,
    ai_artifacts,
]


def epythet_cli():
    """Entry point for the ``epythet`` console script."""
    raise SystemExit(cw.dispatch(COMMANDS))


if __name__ == "__main__":
    epythet_cli()
