# epythet.repo_links

Point repo-relative README links at the repository, so they work on the site.

The landing page is the project README included verbatim. A README written for
GitHub links to repo files that are not site pages (`misc/docs/design.md`,
`LICENSE`, `examples/`); on the built site such a link is a dead relative
URL. [`resolve_repo_link()`](#epythet.repo_links.resolve_repo_link) turns one into a `blob`/`tree` URL on the
project’s repository, and the `doctree-resolved` hook in
[`epythet.sphinx_ext`](epythet.sphinx_ext.html.md#module-epythet.sphinx_ext) applies it to the landing page.

```pycon
>>> resolve_repo_link("misc/docs/a.md", ["misc/docs/a.md"], "https://github.com/o/r")
'https://github.com/o/r/blob/HEAD/misc/docs/a.md'
>>> resolve_repo_link("https://x.org/a", [], "https://github.com/o/r") is None
True
```

### Module Attributes

| [`DEFAULT_REF`](#epythet.repo_links.DEFAULT_REF)   | GitHub resolves `HEAD` to the default branch.   |
|----------------------------------------------------------------|-------------------------------------------------|

### Functions

| [`resolve_repo_link`](#epythet.repo_links.resolve_repo_link)(refuri, repo_paths, ...[, ref])   | The repository URL for a repo-relative `refuri`, or `None` to leave it alone.   |
|------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|

### epythet.repo_links.DEFAULT_REF *= 'HEAD'*

GitHub resolves `HEAD` to the default branch.

* **Type:**
  The ref used in generated URLs

### epythet.repo_links.resolve_repo_link(refuri, repo_paths, repo_url, , ref='HEAD')

The repository URL for a repo-relative `refuri`, or `None` to leave it alone.

* **Parameters:**
  * **refuri** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the link target as written in the README
  * **repo_paths** ([`Container`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Container)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – the posix paths (files and directories, relative to the
    project root) that exist; a link is rewritten only when it names one
  * **repo_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the repository’s web URL (`https://github.com/owner/repo`)
  * **ref** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the git ref the URL points at
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)
