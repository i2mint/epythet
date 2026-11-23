"""Point repo-relative README links at the repository, so they work on the site.

The landing page is the project README included verbatim. A README written for
GitHub links to repo files that are not site pages (``misc/docs/design.md``,
``LICENSE``, ``examples/``); on the built site such a link is a dead relative
URL. :func:`resolve_repo_link` turns one into a ``blob``/``tree`` URL on the
project's repository, and the ``doctree-resolved`` hook in
:mod:`epythet.sphinx_ext` applies it to the landing page.

>>> resolve_repo_link("misc/docs/a.md", ["misc/docs/a.md"], "https://github.com/o/r")
'https://github.com/o/r/blob/HEAD/misc/docs/a.md'
>>> resolve_repo_link("https://x.org/a", [], "https://github.com/o/r") is None
True
"""

from __future__ import annotations

from collections.abc import Container
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit

#: The ref used in generated URLs: GitHub resolves ``HEAD`` to the default branch.
DEFAULT_REF = "HEAD"


def resolve_repo_link(
    refuri: str,
    repo_paths: Container[str],
    repo_url: str,
    *,
    ref: str = DEFAULT_REF,
) -> str | None:
    """The repository URL for a repo-relative ``refuri``, or ``None`` to leave it alone.

    :param refuri: the link target as written in the README
    :param repo_paths: the posix paths (files and directories, relative to the
        project root) that exist; a link is rewritten only when it names one
    :param repo_url: the repository's web URL (``https://github.com/owner/repo``)
    :param ref: the git ref the URL points at
    """
    if not repo_url or not refuri:
        return None
    parts = urlsplit(refuri)
    if parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
        return None  # absolute URL, mailto:, or an in-page / root-relative link
    path = PurePosixPath(parts.path).as_posix().removeprefix("./")
    key = path.rstrip("/")
    if key not in repo_paths:
        return None
    kind = "tree" if (parts.path.endswith("/") or f"{key}/" in repo_paths) else "blob"
    url = f"{repo_url.rstrip('/')}/{kind}/{ref}/{quote(key)}"
    return url + (f"#{parts.fragment}" if parts.fragment else "")
