# epythet.validation.build

Level 1: run the documentation build and turn its warning stream into findings.

This is the `backend=` seam of `epythet validate`. Levels 0 and 0.5 read
Python source and docutils doctrees and are backend-independent by
construction; only this level (and level 2, owned by WP3) touches Sphinx. A
future MkDocs backend implements the same two methods, [`SphinxBackend.versions()`](#epythet.validation.build.SphinxBackend.versions)
and [`SphinxBackend.build_warnings()`](#epythet.validation.build.SphinxBackend.build_warnings), and inherits the whole ledger.

Two Sphinx facts shape the invocation. Since Sphinx 8.1 `-W` runs the whole
build and exits 1 if any warning occurred; `--keep-going` is still passed
because epythet’s Sphinx floor predates 8.1, where `-W` alone stops at the
first warning (it is a no-op on newer versions). Since Sphinx 8.0
`show_warning_types` defaults on, which suffixes every warning with
`[docutils]`-style types; that suffix is what the ledger’s `build-warning`
rules match on, because Sphinx still has no structured warning output.

### Module Attributes

| [`NO_DOCSRC`](#epythet.validation.build.NO_DOCSRC)          | `BuildResult.returncode` when there is no Sphinx source directory to build.                                                          |
|---------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| [`WARNINGS_ONLY_EXIT`](#epythet.validation.build.WARNINGS_ONLY_EXIT) | Sphinx's exit status when the only problem was warnings under `-W`.                                                                  |
| [`WARNING_LINE_RE`](#epythet.validation.build.WARNING_LINE_RE)    | `path:docstring of obj:3: WARNING: message [type]` and the simpler `path:12: WARNING: message [type]` and `WARNING: message` shapes. |
| [`RENDER_BUILDERS`](#epythet.validation.build.RENDER_BUILDERS)    | HTML for links and images, text for snapshots, XML for structure (research §5.4: text and xml are complementary).                    |

### Functions

| [`classify_warning`](#epythet.validation.build.classify_warning)(warning, ledger)                 | The first build-warning rule that matches, most specific first.                           |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| [`default_sphinx_build`](#epythet.validation.build.default_sphinx_build)()                            | `python -m sphinx` when Sphinx is importable here, else `sphinx-build` on PATH.           |
| [`parse_warning_line`](#epythet.validation.build.parse_warning_line)(line, \*[, project_dir])       | Parse one warning line; `None` when the line is not a warning.                            |
| [`parse_warning_stream`](#epythet.validation.build.parse_warning_stream)(text, \*[, project_dir])     | Every warning in a `-w` warnings file or a build log.                                     |
| [`run_build_level`](#epythet.validation.build.run_build_level)(project_dir, ledger, \*, backend) | Level 1: build, classify warnings, and report a crashed build as a finding.               |
| [`warnings_to_findings`](#epythet.validation.build.warnings_to_findings)(warnings, ledger)            | Map each warning to a ledger finding (unclassified warnings keep their type as the rule). |

### Classes

| [`BuildBackend`](#epythet.validation.build.BuildBackend)(\*args, \*\*kwargs)              | What the `backend=` seam requires: a name, versions, and the warning stream.     |
|------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`BuildResult`](#epythet.validation.build.BuildResult)(returncode[, warnings, log, ...]) | What one build produced: exit status, parsed warnings, and the raw log.          |
| [`BuildWarning`](#epythet.validation.build.BuildWarning)(severity, message[, type, ...])  | One parsed line of the Sphinx warning stream.                                    |
| [`RenderBackend`](#epythet.validation.build.RenderBackend)(\*args, \*\*kwargs)             | A backend that can also render several builders into a kept directory (level 2). |
| [`RenderResult`](#epythet.validation.build.RenderResult)([outdirs, returncodes, ...])     | What a multi-builder render produced: one output directory per builder.          |
| [`SphinxBackend`](#epythet.validation.build.SphinxBackend)([sphinx_build, docsrc, ...])    | The default (and only shipped) backend: `sphinx-build -b html -W`.               |

### *class* epythet.validation.build.BuildBackend(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

What the `backend=` seam requires: a name, versions, and the warning stream.

[`SphinxBackend`](#epythet.validation.build.SphinxBackend) is the shipped implementation; a MkDocs backend
implements the same two methods and inherits the whole ledger. Level 2
additionally needs [`RenderBackend`](#epythet.validation.build.RenderBackend).

### *class* epythet.validation.build.BuildResult(returncode, warnings=<factory>, log='', outdir=None, command=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What one build produced: exit status, parsed warnings, and the raw log.

### *class* epythet.validation.build.BuildWarning(severity, message, type=None, file=None, line=None, object=None, raw='')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One parsed line of the Sphinx warning stream.

### epythet.validation.build.NO_DOCSRC *= -1*

`BuildResult.returncode` when there is no Sphinx source directory to build.

### epythet.validation.build.RENDER_BUILDERS *= ('html', 'text', 'xml')*

HTML for links and images, text for snapshots,
XML for structure (research §5.4: text and xml are complementary).

* **Type:**
  The builders level 2 reads

### *class* epythet.validation.build.RenderBackend(\*args, \*\*kwargs)

Bases: [`BuildBackend`](#epythet.validation.build.BuildBackend), [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A backend that can also render several builders into a kept directory (level 2).

### *class* epythet.validation.build.RenderResult(outdirs=<factory>, returncodes=<factory>, warnings=<factory>, log='')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What a multi-builder render produced: one output directory per builder.

`outdirs` maps a builder name (`html`, `text`, `xml`) to the
directory holding its pages; a builder that failed is absent from it and
its exit status is in `returncodes`. `warnings` is the parsed warning
stream of the first builder (the others repeat it).

#### *property* ok *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether every builder exited 0 or with warnings only.

### *class* epythet.validation.build.SphinxBackend(sphinx_build=None, docsrc=None, outdir=None, builder='html', nitpicky=False, name='sphinx')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The default (and only shipped) backend: `sphinx-build -b html -W`.

`docsrc` defaults to `<project>/docsrc`, the directory epythet
generates. `outdir` defaults to a temporary directory so validation
never litters the repository.

#### build_warnings(project_dir)

Run the build and parse its warnings; never raises on a failed build.

Without `outdir` the build goes to a temporary directory that is
removed before returning; only the parsed warnings and the log survive.

* **Return type:**
  [`BuildResult`](#epythet.validation.build.BuildResult)

#### render(project_dir, , builders=('html', 'text', 'xml'), outdir)

Build every builder in `builders` into `outdir/<builder>` (level 2).

Unlike [`build_warnings()`](#epythet.validation.build.SphinxBackend.build_warnings), the output is kept: level 2 reads it, and
level 3 packs it for review. The caller owns `outdir`.

* **Return type:**
  [`RenderResult`](#epythet.validation.build.RenderResult)

#### resolve_docsrc(project_dir)

The Sphinx source directory, or `None` when there is none to build.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/library/constants.html#None)

#### versions()

`{"sphinx": ..., "docutils": ...}` as importable here (`None` if not).

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)]

### epythet.validation.build.WARNINGS_ONLY_EXIT *= 1*

Sphinx’s exit status when the only problem was warnings under `-W`.

### epythet.validation.build.WARNING_LINE_RE *= re.compile('^(?:(?P<loc>.\*?):\\\\s\*)?(?P<sev>WARNING|ERROR|SEVERE|CRITICAL): (?P<msg>.\*?)(?: \\\\[(?P<type>[\\\\w.\\\\-]+)\\\\])?\\\\s\*$')*

`path:docstring of obj:3: WARNING: message [type]` and the simpler
`path:12: WARNING: message [type]` and `WARNING: message` shapes.

### epythet.validation.build.classify_warning(warning, ledger)

The first build-warning rule that matches, most specific first.

* **Return type:**
  `Rule` | [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.validation.build.default_sphinx_build()

`python -m sphinx` when Sphinx is importable here, else `sphinx-build` on PATH.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.validation.build.parse_warning_line(line, , project_dir=None)

Parse one warning line; `None` when the line is not a warning.

* **Return type:**
  [`BuildWarning`](#epythet.validation.build.BuildWarning) | [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> w = parse_warning_line("/p/dol/base.py:docstring of dol.base.Store:7: WARNING: Inline emphasis start-string without end-string. [docutils]")
>>> (w.file, w.object, w.line, w.type, w.severity)
('/p/dol/base.py', 'dol.base.Store', 7, 'docutils', 'warning')
>>> parse_warning_line("reading sources... [ 10%] index") is None
True
```

### epythet.validation.build.parse_warning_stream(text, , project_dir=None)

Every warning in a `-w` warnings file or a build log.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`BuildWarning`](#epythet.validation.build.BuildWarning)]

### epythet.validation.build.run_build_level(project_dir, ledger, , backend)

Level 1: build, classify warnings, and report a crashed build as a finding.

A missing `docsrc/` is a `NO_DOCSRC` warning, not an error: the fleet
plan deletes committed `docsrc/` directories, and “nothing to build”
must not gate a package whose docstrings are clean.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]

### epythet.validation.build.warnings_to_findings(warnings, ledger)

Map each warning to a ledger finding (unclassified warnings keep their type as the rule).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)]
