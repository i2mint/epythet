# epythet.userconfig

User-level defaults and parametrizable text snippets.

epythet ships opinions (what a README section for agents should say, which
humour lines introduce the “for humans” pointer, whether a missing section is a
warning or something to add). A user who wants different opinions sets them
once, outside any repository, and every project on that machine picks them up.
Two things live under the user’s config directory:

- `config.toml`: policy. The `[readme]` table decides what the
  `epythet-agentic-readme` skill does (`agentic_aspects = "warn" | "add"`,
  `humor`, `agentic_first`); the `[snippets]` table can point `dir` at
  a different snippet folder.
- `snippets/<name>.md`: text overrides. A snippet is looked up in the user’s
  folder first, then in the packaged defaults (`epythet/data/snippets`).
  `epythet snippets init` copies the packaged defaults out **once**, with a
  header recording the epythet version they came from, and never overwrites a
  file that exists; `epythet snippets diff` shows how a user’s copy differs
  from the current packaged default, so upstream changes are visible without
  ever being applied silently.

The config directory is `$EPYTHET_CONFIG_DIR`, else `$XDG_CONFIG_HOME/epythet`,
else `~/.config/epythet`: the config-side twin of
`epythet.validation.ledger.user_data_dir()`, which holds mutable data
(ledger observations) under `~/.local/share/epythet`. Skills stay prose: they
call `epythet snippets show <name>` and `epythet ai-readme-check --format json`
and let this module do the resolving.

```pycon
>>> import os, tempfile
>>> _saved = os.environ.get("EPYTHET_CONFIG_DIR")
>>> os.environ["EPYTHET_CONFIG_DIR"] = tempfile.mkdtemp()
>>> load_user_config().readme
ReadmePolicy(agentic_aspects='warn', humor=False, agentic_first=False)
>>> snippet("agentic-readme-humor").source
'packaged'
>>> written = init_snippets()
>>> snippet("agentic-readme-humor").source
'user'
>>> init_snippets()          # a second init writes nothing
[]
>>> _ = os.environ.pop("EPYTHET_CONFIG_DIR") if _saved is None else os.environ.__setitem__("EPYTHET_CONFIG_DIR", _saved)
```

### Module Attributes

| [`CONFIG_DIR_ENV`](#epythet.userconfig.CONFIG_DIR_ENV)           | Environment variable overriding the whole config directory.                              |
|---------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`CONFIG_FILENAME`](#epythet.userconfig.CONFIG_FILENAME)          | The policy file inside the config directory.                                             |
| [`SNIPPETS_DIRNAME`](#epythet.userconfig.SNIPPETS_DIRNAME)         | The snippet folder inside the config directory (unless `[snippets] dir` says otherwise). |
| [`PACKAGED_SNIPPETS_DIR`](#epythet.userconfig.PACKAGED_SNIPPETS_DIR)    | Where the packaged default snippets live.                                                |
| [`AGENTIC_ASPECTS_POLICIES`](#epythet.userconfig.AGENTIC_ASPECTS_POLICIES) | What `agentic_aspects` may be.                                                           |
| [`SNIPPET_COMMANDS`](#epythet.userconfig.SNIPPET_COMMANDS)         | The `epythet snippets` group, by command-line name.                                      |

### Functions

| [`config_dir`](#epythet.userconfig.config_dir)()                                | `$EPYTHET_CONFIG_DIR`, else `$XDG_CONFIG_HOME/epythet`, else `~/.config/epythet`.                                            |
|----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [`config_path`](#epythet.userconfig.config_path)()                               | The policy file: `<config dir>/config.toml`.                                                                                 |
| [`diff_snippet`](#epythet.userconfig.diff_snippet)(name, \*[, user_dir])          | A unified diff from the current packaged default to the user's copy (`""` when equal).                                       |
| [`epythet_version`](#epythet.userconfig.epythet_version)()                           | epythet's version: the checkout's `pyproject.toml` when running from source, else the installed metadata.                    |
| [`header_version`](#epythet.userconfig.header_version)(text)                        | The epythet version recorded in a user copy's header (`""` when absent).                                                     |
| [`init_snippets`](#epythet.userconfig.init_snippets)(\*[, user_dir, force, names]) | Copy the packaged defaults into the user snippet folder; returns the paths written.                                          |
| [`iter_snippets`](#epythet.userconfig.iter_snippets)(\*[, user_dir])               | Every available snippet, resolved, in name order.                                                                            |
| [`load_user_config`](#epythet.userconfig.load_user_config)([path])                    | Read `config.toml` (default: [`config_path()`](#epythet.userconfig.config_path)); a missing file means defaults. |
| [`packaged_snippet_names`](#epythet.userconfig.packaged_snippet_names)()                    | The names of the snippets epythet ships, sorted.                                                                             |
| [`pool_lines`](#epythet.userconfig.pool_lines)(text)                            | The non-empty, non-comment lines of a pool snippet (one candidate per line).                                                 |
| [`snippet`](#epythet.userconfig.snippet)(name, \*[, user_dir])               | Resolve `name`: the user's `<name>.md` wins over the packaged default.                                                       |
| [`snippet_header`](#epythet.userconfig.snippet_header)(name, version)               | The provenance line `init` writes at the top of a user copy.                                                                 |
| [`snippet_names`](#epythet.userconfig.snippet_names)(\*[, user_dir])               | Every snippet name available: packaged plus user-only files, sorted.                                                         |
| [`snippet_text`](#epythet.userconfig.snippet_text)(name, \*[, user_dir])          | The effective body of `name` (header stripped).                                                                              |
| [`snippets_diff`](#epythet.userconfig.snippets_diff)([name])                       | Show how the user's copy of a snippet differs from the current packaged default.                                             |
| [`snippets_dir`](#epythet.userconfig.snippets_dir)([config])                      | Where user snippets are read: `[snippets] dir` if set, else `<config dir>/snippets`.                                         |
| [`snippets_init`](#epythet.userconfig.snippets_init)(\*[, force])                  | Copy the packaged default snippets into the user snippet folder, once.                                                       |
| [`snippets_list`](#epythet.userconfig.snippets_list)()                             | List every snippet with its source (user or packaged), provenance and status.                                                |
| [`snippets_show`](#epythet.userconfig.snippets_show)(name)                         | Print the effective text of a snippet: the user's copy if it exists, else the packaged default.                              |
| [`snippets_table`](#epythet.userconfig.snippets_table)(\*[, user_dir])              | The `epythet snippets list` output: name, source, provenance, whether modified.                                              |
| [`strip_header`](#epythet.userconfig.strip_header)(text)                          | `text` without the provenance header, if it has one.                                                                         |

### Classes

| [`ReadmePolicy`](#epythet.userconfig.ReadmePolicy)([agentic_aspects, humor, ...])      | The `[readme]` table: what to do about agentic aspects missing from a README.   |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`Snippet`](#epythet.userconfig.Snippet)(name, path, source, text[, copied_from]) | One resolved snippet: its text and where it came from.                          |
| [`SnippetsConfig`](#epythet.userconfig.SnippetsConfig)([dir])                            | The `[snippets]` table: `dir` overrides where user snippets are read.           |
| [`UserConfig`](#epythet.userconfig.UserConfig)([readme, snippets, path])             | Everything `config.toml` can say, with defaults for what it does not.           |

### Exceptions

| [`UserConfigError`](#epythet.userconfig.UserConfigError)   | `config.toml` has a key epythet does not know or a value it cannot use.   |
|--------------------------------------------------------------------|---------------------------------------------------------------------------|

### epythet.userconfig.AGENTIC_ASPECTS_POLICIES *= ('warn', 'add')*

What `agentic_aspects` may be.

### epythet.userconfig.CONFIG_DIR_ENV *= 'EPYTHET_CONFIG_DIR'*

Environment variable overriding the whole config directory.

### epythet.userconfig.CONFIG_FILENAME *= 'config.toml'*

The policy file inside the config directory.

### epythet.userconfig.PACKAGED_SNIPPETS_DIR *= PosixPath('/home/runner/work/epythet/epythet/epythet/data/snippets')*

Where the packaged default snippets live.

### *class* epythet.userconfig.ReadmePolicy(agentic_aspects='warn', humor=False, agentic_first=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The `[readme]` table: what to do about agentic aspects missing from a README.

`agentic_aspects` is `"warn"` (report only; the packaged default) or
`"add"` (write or update the section). `humor` draws the “for humans”
line from the humour pool; `agentic_first` places the section right after
the README’s intro rather than at the end.

### epythet.userconfig.SNIPPETS_DIRNAME *= 'snippets'*

The snippet folder inside the config directory (unless `[snippets] dir` says otherwise).

### epythet.userconfig.SNIPPET_COMMANDS *= {'diff': <function snippets_diff>, 'init': <function snippets_init>, 'list': <function snippets_list>, 'show': <function snippets_show>}*

The `epythet snippets` group, by command-line name.

### *class* epythet.userconfig.Snippet(name, path, source, text, copied_from='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One resolved snippet: its text and where it came from.

`source` is `"user"` or `"packaged"`; `copied_from` is the epythet
version recorded in a user copy’s header (`""` for a packaged snippet or
a user file written by hand).

#### *property* body *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The text without the provenance header (what templates and pools use).

### *class* epythet.userconfig.SnippetsConfig(dir='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The `[snippets]` table: `dir` overrides where user snippets are read.

A relative `dir` is taken relative to the config directory, so the same
`config.toml` means the same folder from any shell.

### *class* epythet.userconfig.UserConfig(readme=<factory>, snippets=<factory>, path=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything `config.toml` can say, with defaults for what it does not.

#### readme_for(project_overrides=None)

The effective policy for one project: `[tool.epythet.readme]` keys override the user’s.

Committed READMEs should not depend on who ran the tool, so a project
can pin what matters for its text (`humor`, `agentic_first`) in its
`pyproject.toml`; `agentic_aspects` may be pinned too.

* **Return type:**
  [`ReadmePolicy`](#epythet.userconfig.ReadmePolicy)

```pycon
>>> UserConfig().readme_for({"humor": True}).humor
True
>>> UserConfig().readme_for({"humour": True})
Traceback (most recent call last):
...
UserConfigError: unknown key(s) ['humour'] in [tool.epythet.readme]
```

#### to_dict(project_overrides=None)

A JSON-ready view (the `policy` block of `ai-readme-check --format json`).

`readme` is the effective policy after `project_overrides`; `user`
the user’s own table, `project` the overrides, `path` the config file.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### *exception* epythet.userconfig.UserConfigError

Bases: [`ConfigError`](epythet.config.html.md#epythet.config.ConfigError)

`config.toml` has a key epythet does not know or a value it cannot use.

### epythet.userconfig.config_dir()

`$EPYTHET_CONFIG_DIR`, else `$XDG_CONFIG_HOME/epythet`, else `~/.config/epythet`.

XDG-style on every platform, like `epythet.validation.ledger.user_data_dir()`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> _saved = os.environ.get(CONFIG_DIR_ENV)
>>> os.environ[CONFIG_DIR_ENV] = "/tmp/x"; config_dir().as_posix()
'/tmp/x'
>>> _ = os.environ.pop(CONFIG_DIR_ENV) if _saved is None else os.environ.__setitem__(CONFIG_DIR_ENV, _saved)
```

### epythet.userconfig.config_path()

The policy file: `<config dir>/config.toml`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### epythet.userconfig.diff_snippet(name, , user_dir=None)

A unified diff from the current packaged default to the user’s copy (`""` when equal).

Headers are ignored, so a freshly `init`-ed copy has no diff. A user-only
snippet (no packaged default) diffs against nothing, so every line is an
addition.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.userconfig.epythet_version()

epythet’s version: the checkout’s `pyproject.toml` when running from source, else the installed metadata.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.userconfig.header_version(text)

The epythet version recorded in a user copy’s header (`""` when absent).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> header_version(snippet_header("x", "0.2.5") + "body")
'0.2.5'
>>> header_version("no header")
''
```

### epythet.userconfig.init_snippets(, user_dir=None, force=False, names=None)

Copy the packaged defaults into the user snippet folder; returns the paths written.

A file that already exists is left alone unless `force` is true (then it
is replaced; `epythet snippets diff` first is the way to see what you lose).

* **Parameters:**
  **names** – which snippets to copy (default: all packaged)
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]

### epythet.userconfig.iter_snippets(, user_dir=None)

Every available snippet, resolved, in name order.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Snippet`](#epythet.userconfig.Snippet)]

### epythet.userconfig.load_user_config(path=None)

Read `config.toml` (default: [`config_path()`](#epythet.userconfig.config_path)); a missing file means defaults.

* **Raises:**
  [**UserConfigError**](#epythet.userconfig.UserConfigError) – on an unknown table or key, or an invalid value
* **Return type:**
  [`UserConfig`](#epythet.userconfig.UserConfig)

### epythet.userconfig.packaged_snippet_names()

The names of the snippets epythet ships, sorted.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### epythet.userconfig.pool_lines(text)

The non-empty, non-comment lines of a pool snippet (one candidate per line).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> pool_lines("# a comment\n\nIf you are a control freak\n  If you like it \n")
['If you are a control freak', 'If you like it']
```

### epythet.userconfig.snippet(name, , user_dir=None)

Resolve `name`: the user’s `<name>.md` wins over the packaged default.

* **Raises:**
  [**KeyError**](https://docs.python.org/3/builtins/exceptions.html#KeyError) – when neither exists
* **Return type:**
  [`Snippet`](#epythet.userconfig.Snippet)

### epythet.userconfig.snippet_header(name, version)

The provenance line `init` writes at the top of a user copy.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.userconfig.snippet_names(, user_dir=None)

Every snippet name available: packaged plus user-only files, sorted.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### epythet.userconfig.snippet_text(name, , user_dir=None)

The effective body of `name` (header stripped).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.userconfig.snippets_diff(name='')

Show how the user’s copy of a snippet differs from the current packaged default.

Without `--name`, every user copy that differs is shown. Exit code 1 when any
difference exists, like `diff`, so scripts can tell.

* **Parameters:**
  **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one snippet, or omitted for all

### epythet.userconfig.snippets_dir(config=None)

Where user snippets are read: `[snippets] dir` if set, else `<config dir>/snippets`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### epythet.userconfig.snippets_init(, force=False)

Copy the packaged default snippets into the user snippet folder, once.

Each copy starts with a header recording the epythet version it came from.
Existing files are never overwritten unless `--force` is given.

* **Parameters:**
  **force** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – replace existing user copies (run `diff` first to see what you lose)

### epythet.userconfig.snippets_list()

List every snippet with its source (user or packaged), provenance and status.

### epythet.userconfig.snippets_show(name)

Print the effective text of a snippet: the user’s copy if it exists, else the packaged default.

* **Parameters:**
  **name** – the snippet name (`epythet snippets list` shows them)

### epythet.userconfig.snippets_table(, user_dir=None)

The `epythet snippets list` output: name, source, provenance, whether modified.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### epythet.userconfig.strip_header(text)

`text` without the provenance header, if it has one.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
