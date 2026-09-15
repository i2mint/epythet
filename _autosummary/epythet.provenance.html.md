# epythet.provenance

Build provenance: which code, which version, which tools produced a site.

A documentation site is a snapshot. The reader wants to know whether it matches
the repository they are looking at and the package they installed; the
maintainer wants to know whether the latest push has been published yet
(issue #7). This module collects that diagnosis once per build and the rest of
epythet renders it in three places:

- a one-line footer on the landing page (`built <UTC time> from <commit>
  (<branch>) · <package> <version> · about this build`), appended to the
  rendered page by [`epythet.sphinx_ext`](epythet.sphinx_ext.html.md#module-epythet.sphinx_ext);
- `about-this-build.html`, an orphan page (reachable from the footer, absent
  from the navigation) with the full diagnosis, rendered from
  [`ABOUT_PAGE_TEMPLATE`](#epythet.provenance.ABOUT_PAGE_TEMPLATE) or the project’s `provenance_template`;
- `build_info.json` at the site root, the same data for machines, with
  stable keys and a `schema_version`; also listed in `llms.txt` and
  referenced at the top of the `<package>.md` aggregate.

The `[tool.epythet] provenance` key is the seam: `true` (default) renders
all three, `"minimal"` renders the footer line and the JSON but no page,
`false` renders nothing.

Collection never fails a build. No git, no `git` binary, no network, a
detached HEAD: every source degrades to `null` fields plus an entry in the
`warnings` list, and the build prints one warning. The record is published,
so nothing local goes into it: remote URLs lose any credentials, path-shaped
remotes are dropped, git’s error text is scrubbed of paths, and the reproduce
lines name the clone by its remote, not by the local folder.

`SOURCE_DATE_EPOCH` (the reproducible-builds convention Sphinx honours too)
fixes the build time when set.

```pycon
>>> from epythet.config import DocsConfig
>>> cfg = DocsConfig(project_dir="/nonexistent", name="pkg", version="1.0")
>>> info = collect_build_info(cfg, check_pypi=False)
>>> info["schema_version"], info["package"]["name"], info["git"]["available"]
(1, 'pkg', False)
>>> "about this build" in render_footer_line(info)
True
```

### Module Attributes

| [`SCHEMA_VERSION`](#epythet.provenance.SCHEMA_VERSION)         | Bumped when a key is renamed or removed; additions keep the version.                                                         |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [`BUILD_INFO_FILENAME`](#epythet.provenance.BUILD_INFO_FILENAME)    | File written at the site root.                                                                                               |
| [`ABOUT_PAGE_FILENAME`](#epythet.provenance.ABOUT_PAGE_FILENAME)    | Source file (in docsrc) and document name of the full-diagnosis page.                                                        |
| [`BUILD_INFO_ENV`](#epythet.provenance.BUILD_INFO_ENV)         | Environment variable carrying the collected JSON into the Sphinx process.                                                    |
| [`PYPI_CHECK_ENV`](#epythet.provenance.PYPI_CHECK_ENV)         | Set to `0` to skip the PyPI lookup (offline CI, tests).                                                                      |
| [`SOURCE_DATE_EPOCH_ENV`](#epythet.provenance.SOURCE_DATE_EPOCH_ENV)  | seconds since the epoch, fixes `built_at`.                                                                                   |
| [`DEFAULT_PYPI_TIMEOUT`](#epythet.provenance.DEFAULT_PYPI_TIMEOUT)   | Seconds allowed for the PyPI lookup, in total; the build never waits longer.                                                 |
| [`GIT_TIMEOUT`](#epythet.provenance.GIT_TIMEOUT)            | Seconds allowed for each git command.                                                                                        |
| [`SHORT_COMMIT_LENGTH`](#epythet.provenance.SHORT_COMMIT_LENGTH)    | Characters of a commit hash shown in the footer and the summary.                                                             |
| [`AGGREGATE_STAMP_PREFIX`](#epythet.provenance.AGGREGATE_STAMP_PREFIX) | First line of the stamp prepended to the `<package>.md` aggregate.                                                           |
| [`ABOUT_PAGE_TEMPLATE`](#epythet.provenance.ABOUT_PAGE_TEMPLATE)    | it is how epythet recognises its own file.                                                                                   |
| [`TEMPLATE_FIELDS`](#epythet.provenance.TEMPLATE_FIELDS)        | The fields [`render_about_page()`](#epythet.provenance.render_about_page) fills; a custom template may use any subset. |

### Functions

| [`about_page`](#epythet.provenance.about_page)(info, \*[, template])                  | The about page as a `PageSpec`.                                                                                                               |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| [`about_template`](#epythet.provenance.about_template)(config)                            | The about page's template: `[tool.epythet] provenance_template` or the default.                                                               |
| [`alignment`](#epythet.provenance.alignment)(info)                                   | Whether the docs can be trusted to match the repository and the package.                                                                      |
| [`build_time`](#epythet.provenance.build_time)([environ])                             | Now in UTC, or the instant `SOURCE_DATE_EPOCH` names when it is set.                                                                          |
| [`ci_info`](#epythet.provenance.ci_info)([environ])                                | The GitHub Actions context, when the build runs there (else `None` fields).                                                                   |
| [`clone_dirname`](#epythet.provenance.clone_dirname)(remote)                             | The directory `git clone <remote>` creates.                                                                                                   |
| [`collect_build_info`](#epythet.provenance.collect_build_info)(config, \*[, check_pypi, ...]) | The provenance record for one build of `config`'s project.                                                                                    |
| [`compare_versions`](#epythet.provenance.compare_versions)(ours, latest)                    | `same` / `behind` / `ahead` of `latest`, or `unknown` when unparsable.                                                                        |
| [`config_source`](#epythet.provenance.config_source)(project_dir)                        | Which file the package metadata came from: the rule of [`epythet.config`](epythet.config.html.md#module-epythet.config). |
| [`footer_text`](#epythet.provenance.footer_text)(info)                                 | The provenance line as plain text (no link).                                                                                                  |
| [`git_info`](#epythet.provenance.git_info)(project_dir, \*[, exclude])              | What git knows about `project_dir`: commit, branch, tags, dirty flag, remote.                                                                 |
| [`github_web_url`](#epythet.provenance.github_web_url)(remote)                            | The `https://github.com/owner/repo` form of a remote URL, or `None`.                                                                          |
| [`human_time`](#epythet.provenance.human_time)(iso)                                   | `2026-09-15T14:02:00Z` -> `2026-09-15 14:02 UTC`.                                                                                             |
| [`load_build_info`](#epythet.provenance.load_build_info)(raw)                              | Parse the JSON the build process hands over in `EPYTHET_BUILD_INFO`.                                                                          |
| [`prune_site`](#epythet.provenance.prune_site)(html_dir, \*, keep_page, keep_json)    | Remove provenance outputs a previous build left in `html_dir`.                                                                                |
| [`publishable_remote`](#epythet.provenance.publishable_remote)(url)                           | The form of a remote URL that may appear on a public site, or `None`.                                                                         |
| [`pypi_info`](#epythet.provenance.pypi_info)(name, version, \*[, timeout])           | The latest release of `name` on PyPI and how `version` relates to it.                                                                         |
| [`pypi_latest_version`](#epythet.provenance.pypi_latest_version)(name, \*[, timeout])          | The `info.version` of `https://pypi.org/pypi/<name>/json` (`None` on 404).                                                                    |
| [`reference_from_agent_outputs`](#epythet.provenance.reference_from_agent_outputs)(html_dir, info, ...) | List `build_info.json` in `llms.txt` and stamp the top of `<package>.md`.                                                                     |
| [`render_about_page`](#epythet.provenance.render_about_page)(info, \*[, template])           | The Markdown source of `about-this-build.md` for a collected `info`.                                                                          |
| [`render_footer_line`](#epythet.provenance.render_footer_line)(info, \*[, about_href])        | The landing-page footer as one small HTML paragraph.                                                                                          |
| [`reproduce_command`](#epythet.provenance.reproduce_command)(config, git)                    | The shell lines that rebuild this site from the same commit.                                                                                  |
| [`resolved_config`](#epythet.provenance.resolved_config)(config)                           | The documentation choices as the build resolved them (theme, accent, generator...).                                                           |
| [`scrub_paths`](#epythet.provenance.scrub_paths)(message)                              | Replace absolute paths in a diagnostic with `<path>`: the record is published.                                                                |
| [`short_commit`](#epythet.provenance.short_commit)(sha)                                 | The first [`SHORT_COMMIT_LENGTH`](#epythet.provenance.SHORT_COMMIT_LENGTH) characters of a commit hash.                                   |
| [`site_counts`](#epythet.provenance.site_counts)(env)                                  | Documented-module and documented-object counts from a Sphinx environment.                                                                     |
| [`strip_credentials`](#epythet.provenance.strip_credentials)(url)                            | A scheme URL without any `user:token@` part (scp-style remotes pass through).                                                                 |
| [`tool_versions`](#epythet.provenance.tool_versions)()                                   | Versions of epythet, Sphinx, docutils and Python in the build environment.                                                                    |
| [`with_front_matter_and_marker`](#epythet.provenance.with_front_matter_and_marker)(template)            | Make a page template an orphan (out of the toctree) that carries the marker.                                                                  |
| [`write_build_info`](#epythet.provenance.write_build_info)(html_dir, info)                  | Write `build_info.json` at the site root; returns its path.                                                                                   |

### epythet.provenance.ABOUT_PAGE_FILENAME *= 'about-this-build.md'*

Source file (in docsrc) and document name of the full-diagnosis page.

### epythet.provenance.ABOUT_PAGE_TEMPLATE *= '---\\norphan: true\\n---\\n{marker}\\n\\n# About this build\\n\\n{summary}\\n\\n{alignment_block}\\n\\n## Source\\n\\n| | |\\n|---|---|\\n| Commit | {commit_cell} |\\n| Branch | {branch} |\\n| Tags at this commit | {tags} |\\n| Working tree | {tree_state} |\\n| Remote | {remote} |\\n\\n## Continuous integration\\n\\n{ci_block}\\n\\n## Tools\\n\\n| | |\\n|---|---|\\n| epythet | {epythet_version} |\\n| Sphinx | {sphinx_version} |\\n| docutils | {docutils_version} |\\n| Python | {python_version} |\\n\\n## Configuration as resolved\\n\\n| | |\\n|---|---|\\n| theme | {theme} (Sphinx theme {html_theme}) |\\n| accent | {accent} |\\n| api_generator | {api_generator} |\\n| ignore | {ignore} |\\n| agent_outputs | {agent_outputs} |\\n| aggregates | {aggregates} |\\n| ai_artifacts | {ai_artifacts} |\\n\\n## Package on PyPI\\n\\n{pypi_block}\\n\\n## Reproduce\\n\\n\`\`\`bash\\n{reproduce}\\n\`\`\`\\n\\nThe same data, for machines: <a href="{build_info_filename}"><code>{build_info_filename}</code></a> (schema version {schema_version}).\\n'*

it is how
epythet recognises its own file. Literal braces are doubled. Every value
is already HTML-escaped ([`render_about_page()`](#epythet.provenance.render_about_page)), so a custom template
may place the fields anywhere.

* **Type:**
  The Markdown source of the about page. `{marker}` must stay

### epythet.provenance.AGGREGATE_STAMP_PREFIX *= '> built '*

First line of the stamp prepended to the `<package>.md` aggregate.

### epythet.provenance.BUILD_INFO_ENV *= 'EPYTHET_BUILD_INFO'*

Environment variable carrying the collected JSON into the Sphinx process.

### epythet.provenance.BUILD_INFO_FILENAME *= 'build_info.json'*

File written at the site root.

### epythet.provenance.DEFAULT_PYPI_TIMEOUT *= 3.0*

Seconds allowed for the PyPI lookup, in total; the build never waits longer.

### epythet.provenance.GIT_TIMEOUT *= 10*

Seconds allowed for each git command.

### epythet.provenance.PYPI_CHECK_ENV *= 'EPYTHET_PYPI_CHECK'*

Set to `0` to skip the PyPI lookup (offline CI, tests).

### epythet.provenance.SCHEMA_VERSION *= 1*

Bumped when a key is renamed or removed; additions keep the version.

### epythet.provenance.SHORT_COMMIT_LENGTH *= 7*

Characters of a commit hash shown in the footer and the summary.

### epythet.provenance.SOURCE_DATE_EPOCH_ENV *= 'SOURCE_DATE_EPOCH'*

seconds since the epoch, fixes `built_at`.

* **Type:**
  Reproducible-builds convention

### epythet.provenance.TEMPLATE_FIELDS *= frozenset({'accent', 'agent_outputs', 'aggregates', 'ai_artifacts', 'alignment_block', 'api_generator', 'branch', 'build_info_filename', 'ci_block', 'commit_cell', 'docutils_version', 'epythet_version', 'html_theme', 'ignore', 'marker', 'pypi_block', 'python_version', 'remote', 'reproduce', 'schema_version', 'sphinx_version', 'summary', 'tags', 'theme', 'tree_state'})*

The fields [`render_about_page()`](#epythet.provenance.render_about_page) fills; a custom template may use any subset.

### epythet.provenance.about_page(info, , template='---\\\\norphan: true\\\\n---\\\\n{marker}\\\\n\\\\n# About this build\\\\n\\\\n{summary}\\\\n\\\\n{alignment_block}\\\\n\\\\n## Source\\\\n\\\\n| | |\\\\n|---|---|\\\\n| Commit | {commit_cell} |\\\\n| Branch | {branch} |\\\\n| Tags at this commit | {tags} |\\\\n| Working tree | {tree_state} |\\\\n| Remote | {remote} |\\\\n\\\\n## Continuous integration\\\\n\\\\n{ci_block}\\\\n\\\\n## Tools\\\\n\\\\n| | |\\\\n|---|---|\\\\n| epythet | {epythet_version} |\\\\n| Sphinx | {sphinx_version} |\\\\n| docutils | {docutils_version} |\\\\n| Python | {python_version} |\\\\n\\\\n## Configuration as resolved\\\\n\\\\n| | |\\\\n|---|---|\\\\n| theme | {theme} (Sphinx theme {html_theme}) |\\\\n| accent | {accent} |\\\\n| api_generator | {api_generator} |\\\\n| ignore | {ignore} |\\\\n| agent_outputs | {agent_outputs} |\\\\n| aggregates | {aggregates} |\\\\n| ai_artifacts | {ai_artifacts} |\\\\n\\\\n## Package on PyPI\\\\n\\\\n{pypi_block}\\\\n\\\\n## Reproduce\\\\n\\\\n\`\`\`bash\\\\n{reproduce}\\\\n\`\`\`\\\\n\\\\nThe same data, for machines: <a href="{build_info_filename}"><code>{build_info_filename}</code></a> (schema version {schema_version}).\\\\n')

The about page as a `PageSpec`.

* **Raises:**
  [**ConfigError**](epythet.config.html.md#epythet.config.ConfigError) – when `template` names a field the renderer does not
  provide (literal braces must be doubled: `{{`).

### epythet.provenance.about_template(config)

The about page’s template: `[tool.epythet] provenance_template` or the default.

The key names a file relative to the project root, with the same contract
as `ai_artifacts_template`; the epythet marker is prepended when absent.

* **Raises:**
  [**ConfigError**](epythet.config.html.md#epythet.config.ConfigError) – when the file does not exist
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.provenance.alignment(info)

Whether the docs can be trusted to match the repository and the package.

`aligned` is `True` when nothing suggests otherwise, `False` when a
note says why they may differ, `None` when there is no git information to
judge by. `notes` are the plain-language reasons, in the order shown.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### epythet.provenance.build_time(environ=None)

Now in UTC, or the instant `SOURCE_DATE_EPOCH` names when it is set.

* **Return type:**
  [`datetime`](https://docs.python.org/3/library/datetime.html#datetime.datetime)

```pycon
>>> build_time({"SOURCE_DATE_EPOCH": "0"}).strftime("%Y-%m-%d")
'1970-01-01'
```

### epythet.provenance.ci_info(environ=None)

The GitHub Actions context, when the build runs there (else `None` fields).

`sha_in_history` says whether the event’s commit is in the built HEAD’s
history; the publish action fast-forwards to the branch tip before
building, so HEAD is normally a descendant of `GITHUB_SHA`, not equal to it.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

```pycon
>>> ci_info({"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "o/r",
...          "GITHUB_RUN_ID": "42", "GITHUB_SHA": "abc", "GITHUB_REF": "refs/heads/main",
...          "GITHUB_REF_NAME": "main"})["run_url"]
'https://github.com/o/r/actions/runs/42'
>>> ci_info({})["provider"] is None
True
```

### epythet.provenance.clone_dirname(remote)

The directory `git clone <remote>` creates.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> clone_dirname("https://github.com/org/demo.git"), clone_dirname("git@github.com:o/r")
('demo', 'r')
```

### epythet.provenance.collect_build_info(config, , check_pypi=None, pypi_timeout=3.0, dirty_exclude=None, environ=None, now=None)

The provenance record for one build of `config`’s project.

* **Parameters:**
  * **config** – a [`DocsConfig`](epythet.config.html.md#epythet.config.DocsConfig)
  * **check_pypi** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – query PyPI for the latest release; `None` means “unless
    the `EPYTHET_PYPI_CHECK` environment variable turns it off”
  * **pypi_timeout** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – seconds allowed for that query
  * **dirty_exclude** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – project-relative paths left out of the dirty check, on
    top of the docs dir; `None` means the directories the `github` /
    `gitlab` targets copy the site into (`epythet.build.COPY_TARGETS`)
  * **environ** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – the environment to read CI variables from (default: `os.environ`)
  * **now** ([`datetime`](https://docs.python.org/3/library/datetime.html#datetime.datetime) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – the build time (default: `SOURCE_DATE_EPOCH` if set, else now, UTC)
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  a JSON-serialisable dict; see the module docstring for the keys.
  `site` counts are `None` here and filled in by the Sphinx
  extension, which knows what was documented.

### epythet.provenance.compare_versions(ours, latest)

`same` / `behind` / `ahead` of `latest`, or `unknown` when unparsable.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> compare_versions("0.2.4", "0.2.5"), compare_versions("1.0", "1.0.0")
('behind', 'same')
>>> compare_versions("0.3.0.dev1", "0.2.5"), compare_versions("x", "1")
('ahead', 'unknown')
```

### epythet.provenance.config_source(project_dir)

Which file the package metadata came from: the rule of [`epythet.config`](epythet.config.html.md#module-epythet.config).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### epythet.provenance.footer_text(info)

The provenance line as plain text (no link).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> info = {"built_at": "2026-09-15T14:02:00Z", "package": {"name": "dol", "version": "0.3.1"},
...         "git": {"short_commit": "a1b2c3d", "branch": "master", "dirty": True}}
>>> footer_text(info)
'built 2026-09-15 14:02 UTC from a1b2c3d+dirty (master) · dol 0.3.1'
```

### epythet.provenance.git_info(project_dir, , exclude=())

What git knows about `project_dir`: commit, branch, tags, dirty flag, remote.

`exclude` names paths (relative to the project) left out of the dirty
check; the build rewrites a committed `docsrc/`, which must not count.
Everything is `None` with `available` false when the directory is not a
repository or `git` is not installed. A detached HEAD has `branch`
`None`. `remote_url` is the publishable form of `origin` (no
credentials, no local paths), see [`publishable_remote()`](#epythet.provenance.publishable_remote).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### epythet.provenance.github_web_url(remote)

The `https://github.com/owner/repo` form of a remote URL, or `None`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> github_web_url("git@github.com:i2mint/epythet.git")
'https://github.com/i2mint/epythet'
>>> github_web_url("https://github.com/i2mint/epythet/")
'https://github.com/i2mint/epythet'
>>> github_web_url("https://gitlab.com/x/y.git") is None
True
```

### epythet.provenance.human_time(iso)

`2026-09-15T14:02:00Z` -> `2026-09-15 14:02 UTC`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> human_time("2026-09-15T14:02:00Z")
'2026-09-15 14:02 UTC'
```

### epythet.provenance.load_build_info(raw)

Parse the JSON the build process hands over in `EPYTHET_BUILD_INFO`.

Anything that is not a record of this module’s schema is ignored, so a
stale or foreign value in the environment never breaks a build.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> load_build_info('{"schema_version": 1, "git": {}}')["schema_version"]
1
>>> load_build_info('"str"') is None and load_build_info("{") is None
True
```

### epythet.provenance.prune_site(html_dir, , keep_page, keep_json)

Remove provenance outputs a previous build left in `html_dir`.

Sphinx never cleans its output directory, so a project that turned
`provenance` off (or down to `"minimal"`) would otherwise keep
publishing a stale page or JSON. Returns the paths removed.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

### epythet.provenance.publishable_remote(url)

The form of a remote URL that may appear on a public site, or `None`.

Credentials are dropped from scheme URLs, the user part from scp-style
remotes, and path-shaped remotes (a local or `file://` clone) are not
published at all.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> publishable_remote("https://me:ghp_secret@github.com/o/r.git")
'https://github.com/o/r.git'
>>> publishable_remote("thor@myserver.local:repos/demo.git")
'myserver.local:repos/demo.git'
>>> publishable_remote("git@github.com:o/r.git")
'git@github.com:o/r.git'
>>> publishable_remote("/Users/me/bare/demo.git") is None
True
>>> publishable_remote("D:/repos/x.git") is None
True
>>> publishable_remote("file:///srv/git/demo.git") is None
True
```

### epythet.provenance.pypi_info(name, version, , timeout=3.0)

The latest release of `name` on PyPI and how `version` relates to it.

`relation` is `same`, `behind`, `ahead` or `unknown` (not on
PyPI, unreachable, or unparsable versions). Any failure, including the
`timeout` elapsing, is recorded in `error` and never raised.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### epythet.provenance.pypi_latest_version(name, , timeout=3.0)

The `info.version` of `https://pypi.org/pypi/<name>/json` (`None` on 404).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### epythet.provenance.reference_from_agent_outputs(html_dir, info, , package_name)

List `build_info.json` in `llms.txt` and stamp the top of `<package>.md`.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### epythet.provenance.render_about_page(info, , template='---\\\\norphan: true\\\\n---\\\\n{marker}\\\\n\\\\n# About this build\\\\n\\\\n{summary}\\\\n\\\\n{alignment_block}\\\\n\\\\n## Source\\\\n\\\\n| | |\\\\n|---|---|\\\\n| Commit | {commit_cell} |\\\\n| Branch | {branch} |\\\\n| Tags at this commit | {tags} |\\\\n| Working tree | {tree_state} |\\\\n| Remote | {remote} |\\\\n\\\\n## Continuous integration\\\\n\\\\n{ci_block}\\\\n\\\\n## Tools\\\\n\\\\n| | |\\\\n|---|---|\\\\n| epythet | {epythet_version} |\\\\n| Sphinx | {sphinx_version} |\\\\n| docutils | {docutils_version} |\\\\n| Python | {python_version} |\\\\n\\\\n## Configuration as resolved\\\\n\\\\n| | |\\\\n|---|---|\\\\n| theme | {theme} (Sphinx theme {html_theme}) |\\\\n| accent | {accent} |\\\\n| api_generator | {api_generator} |\\\\n| ignore | {ignore} |\\\\n| agent_outputs | {agent_outputs} |\\\\n| aggregates | {aggregates} |\\\\n| ai_artifacts | {ai_artifacts} |\\\\n\\\\n## Package on PyPI\\\\n\\\\n{pypi_block}\\\\n\\\\n## Reproduce\\\\n\\\\n\`\`\`bash\\\\n{reproduce}\\\\n\`\`\`\\\\n\\\\nThe same data, for machines: <a href="{build_info_filename}"><code>{build_info_filename}</code></a> (schema version {schema_version}).\\\\n')

The Markdown source of `about-this-build.md` for a collected `info`.

Values from the repository (branch, tags, remote, versions) are rendered
as escaped inline HTML, never as Markdown: a ref name is user input.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.provenance.render_footer_line(info, , about_href='about-this-build.html')

The landing-page footer as one small HTML paragraph.

The commit links to GitHub when the remote is known; `about_href` is the
“about this build” link target (`None` to omit the link, as `minimal` does
without a page: the JSON is linked instead). The style is inline on purpose:
it must hold in every theme without a stylesheet of its own.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.provenance.reproduce_command(config, git)

The shell lines that rebuild this site from the same commit.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.provenance.resolved_config(config)

The documentation choices as the build resolved them (theme, accent, generator…).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### epythet.provenance.scrub_paths(message)

Replace absolute paths in a diagnostic with `<path>`: the record is published.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> scrub_paths("fatal: detected dubious ownership in repository at '/home/me/x'")
"fatal: detected dubious ownership in repository at '<path>'"
>>> scrub_paths("fatal: not a git repository (or any of the parent directories): .git")
'fatal: not a git repository (or any of the parent directories): .git'
```

### epythet.provenance.short_commit(sha)

The first [`SHORT_COMMIT_LENGTH`](#epythet.provenance.SHORT_COMMIT_LENGTH) characters of a commit hash.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.provenance.site_counts(env)

Documented-module and documented-object counts from a Sphinx environment.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### epythet.provenance.strip_credentials(url)

A scheme URL without any `user:token@` part (scp-style remotes pass through).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> strip_credentials("https://me:ghp_secret@github.com/o/r.git")
'https://github.com/o/r.git'
```

### epythet.provenance.tool_versions()

Versions of epythet, Sphinx, docutils and Python in the build environment.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### epythet.provenance.with_front_matter_and_marker(template)

Make a page template an orphan (out of the toctree) that carries the marker.

YAML front matter must be the very first thing in the file, so the marker
goes after it; `orphan: true` is added when the front matter lacks it,
and front matter is created when there is none.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> print(with_front_matter_and_marker("# Build\n"))
---
orphan: true
---
{marker}

# Build

>>> print(with_front_matter_and_marker("---\ntitle: x\n---\n{marker}\n# B\n"))
---
title: x
orphan: true
---
{marker}
# B
```

### epythet.provenance.write_build_info(html_dir, info)

Write `build_info.json` at the site root; returns its path.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
