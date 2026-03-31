"""Command line access to epythet

More info in the main epythet documentation page
"""

from typing import List
from pathlib import Path

_STATIC_FILES = Path(__file__).absolute().parent / "_static"

from epythet.autogen import make_autodocs
from epythet.setup_docsrc import make_docsrc
from epythet.call_make import make

import argh


@argh.arg("--ignore", nargs="*")
def quickstart(project_dir, *, ignore: list[str] = None):
    """Quickstart will run through the three steps

    1. epythet make_docsrc project_dir
    2. epythet make_autodocs project_dir
    3. epythet make project_dir html

    :param project_dir: Path to root project directory containing docsrc folder
    :param ignore: skip file if path contains any ignore strings
    """
    make_docsrc(project_dir, verbose=True)
    make_autodocs(project_dir, skip_existing=False, ignore=ignore)
    make(project_dir, "html")


def check_pages(repo, *, no_url_check: bool = False):
    """Diagnose GitHub Pages setup for a repo.

    :param repo: GitHub repo as 'owner/repo', or path to a local git checkout.
    :param no_url_check: Skip checking if the docs URL actually responds.
    """
    from epythet.tools.published_docs import (
        check_pages_setup,
        repo_stub_from_local_dir,
    )

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


argh_kwargs = {
    "namespace": "epythet",
    "functions": [
        make_docsrc,
        make_autodocs,
        make,
        quickstart,
        check_pages,
        configure_pages,
    ],
    "namespace_kwargs": {
        "title": "Documentation Generator",
        "description": "Setup and generate Sphinx docs effortlessly",
    },
}


def epythet_cli():
    import argh  # pip install argh

    argh.dispatch_commands(argh_kwargs.get("functions", None))


if __name__ == "__main__":
    epythet_cli()
