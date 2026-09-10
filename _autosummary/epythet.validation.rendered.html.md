# epythet.validation.rendered

Level 2: read the *rendered* output (XML, HTML, text) and report what the build hid.

A strict build is silent about most of what a reader sees wrong (research
§2.2): an object listed with no description, a cross-reference that rendered
as plain code, a link to an anchor Sphinx pruned, an image that is not in the
built tree. This level renders three builders through the `backend=` seam
([`render()`](epythet.validation.build.html.md#epythet.validation.build.SphinxBackend.render)) and reads each for
what it shows best (research §5.4):

- `xml` for structure: empty object descriptions and unresolved
  cross-references (a `literal` with class `xref` that no `reference`
  wraps, detectable without `-n`);
- `html` for links and assets: dangling `#idN` anchors and `<img src>`
  that resolve to nothing in the built tree;
- `text` for snapshots: a 4 KB page that keeps every text-leak artifact
  verbatim and none of the theme, diffed against `docsrc/_snapshots/text`
  when `snapshot=True`.

Only the standard library parses the output (`xml.etree` and `html.parser`):
the pages are Sphinx’s own, not untrusted input. Snapshots are opt-in and
off by default; `update_snapshots=True` re-baselines.

```pycon
>>> from epythet.validation.rendered import dangling_anchors
>>> dangling_anchors('<a id="x"></a><a href="#x">ok</a><a href="#id7">gone</a>')
['#id7']
```

### Module Attributes

| [`SNAPSHOT_DIRNAME`](#epythet.validation.rendered.SNAPSHOT_DIRNAME)   | Where `-b text` snapshots live, relative to the Sphinx source directory.     |
|---------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`EMPTY_DESCRIPTION`](#epythet.validation.rendered.EMPTY_DESCRIPTION)  | Rule ids this level reports under (all bundled; see `epythet/ledger/rules`). |
| [`RenderDetector`](#epythet.validation.rendered.RenderDetector)     | A detector takes `{builder: outdir}` and the Sphinx source dir.              |
| [`RENDER_DETECTORS`](#epythet.validation.rendered.RENDER_DETECTORS)   | Detector name (as in a rule's `detector.function`) -> function.              |

### Functions

| [`changed_pages`](#epythet.validation.rendered.changed_pages)(diff)                            | Pages level 3 should review: changed or new relative to the snapshot.                 |
|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`compare_snapshots`](#epythet.validation.rendered.compare_snapshots)(text_dir, snapshot_dir)      | Diff every rendered text page against its stored snapshot.                            |
| [`dangling_anchors`](#epythet.validation.rendered.dangling_anchors)(html)                         | Fragment links on a page whose target id does not exist on that page.                 |
| [`dangling_anchors_detector`](#epythet.validation.rendered.dangling_anchors_detector)(outdirs, \_docsrc)   | Level-2 detector over the `html` output (DR027).                                      |
| [`empty_descriptions`](#epythet.validation.rendered.empty_descriptions)(outdirs, \_docsrc)          | Level-2 detector over the `xml` output (DR026).                                       |
| [`empty_descriptions_in`](#epythet.validation.rendered.empty_descriptions_in)(root)                    | Objects the page lists or describes with no text at all.                              |
| [`missing_images`](#epythet.validation.rendered.missing_images)(html, \*, page_dir)             | `<img src>` values that resolve to no file next to the page.                          |
| [`missing_images_detector`](#epythet.validation.rendered.missing_images_detector)(outdirs, \_docsrc)     | Level-2 detector over the `html` output (DR024 at level 2).                           |
| [`render_detector`](#epythet.validation.rendered.render_detector)(name)                          | Register a level-2 detector; the ledger loader validates `html` rules against it.     |
| [`render_findings`](#epythet.validation.rendered.render_findings)(outdirs, ledger, \*, docsrc)   | Run every `html`-kind rule of the ledger over the rendered output.                    |
| [`run_render_level`](#epythet.validation.rendered.run_render_level)(project_dir, ledger, \*, ...) | Level 2: render html, text and xml into `outdir` and read them.                       |
| [`snapshot_findings`](#epythet.validation.rendered.snapshot_findings)(diff, ledger)                | One DR035 finding per changed page, plus info findings for new and removed pages.     |
| [`text_snapshots_detector`](#epythet.validation.rendered.text_snapshots_detector)(_outdirs, \_docsrc)    | DR035's detector is the snapshot diff, driven by `snapshot=`; nothing to scan here.   |
| [`unresolved_xrefs`](#epythet.validation.rendered.unresolved_xrefs)(outdirs, \_docsrc)            | Level-2 detector over the `xml` output (DR023 at level 2).                            |
| [`unresolved_xrefs_in`](#epythet.validation.rendered.unresolved_xrefs_in)(root)                      | Cross-references that rendered as plain code: an `xref` literal no `reference` wraps. |
| [`update_snapshots`](#epythet.validation.rendered.update_snapshots)(text_dir, snapshot_dir)       | Replace the stored snapshots with the current render; returns pages written.          |

### Classes

| [`RenderArtifacts`](#epythet.validation.rendered.RenderArtifacts)([outdirs, docsrc, snapshot])      | What level 2 leaves behind for level 3: output dirs and the snapshot diff.   |
|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`RenderHit`](#epythet.validation.rendered.RenderHit)(page, evidence[, object])               | One thing a render detector found on one page.                               |
| [`SnapshotDiff`](#epythet.validation.rendered.SnapshotDiff)([changed, added, removed, compared]) | How the `-b text` render compares with the stored snapshots.                 |

### epythet.validation.rendered.EMPTY_DESCRIPTION *= 'DR026'*

Rule ids this level reports under (all bundled; see `epythet/ledger/rules`).

### epythet.validation.rendered.RENDER_DETECTORS *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/typing.html#typing.Callable)[[[dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)], [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)], [list](https://docs.python.org/3/library/stdtypes.html#list)[[RenderHit](#epythet.validation.rendered.RenderHit)]]]* *= {'dangling_anchors': <function dangling_anchors_detector>, 'empty_descriptions': <function empty_descriptions>, 'missing_images': <function missing_images_detector>, 'text_snapshots': <function text_snapshots_detector>, 'unresolved_xrefs': <function unresolved_xrefs>}*

Detector name (as in a rule’s `detector.function`) -> function.

### *class* epythet.validation.rendered.RenderArtifacts(outdirs=<factory>, docsrc=None, snapshot=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What level 2 leaves behind for level 3: output dirs and the snapshot diff.

### epythet.validation.rendered.RenderDetector

A detector takes `{builder: outdir}` and the Sphinx source dir.

alias of `Callable`[[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)], [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]]

### *class* epythet.validation.rendered.RenderHit(page, evidence, object=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One thing a render detector found on one page.

### epythet.validation.rendered.SNAPSHOT_DIRNAME *= '_snapshots/text'*

Where `-b text` snapshots live, relative to the Sphinx source directory.

### *class* epythet.validation.rendered.SnapshotDiff(changed=<factory>, added=<factory>, removed=<factory>, compared=0)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

How the `-b text` render compares with the stored snapshots.

### epythet.validation.rendered.changed_pages(diff)

Pages level 3 should review: changed or new relative to the snapshot.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.rendered.compare_snapshots(text_dir, snapshot_dir)

Diff every rendered text page against its stored snapshot.

* **Return type:**
  [`SnapshotDiff`](#epythet.validation.rendered.SnapshotDiff)

### epythet.validation.rendered.dangling_anchors(html)

Fragment links on a page whose target id does not exist on that page.

This is the research’s exact detector (§6.3): every `problematic` span
Sphinx emits links to a `#idN` system message it then prunes, and a
hand-written `:ref:` to a missing label ends the same way.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.rendered.dangling_anchors_detector(outdirs, \_docsrc)

Level-2 detector over the `html` output (DR027).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.empty_descriptions(outdirs, \_docsrc)

Level-2 detector over the `xml` output (DR026).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.empty_descriptions_in(root)

Objects the page lists or describes with no text at all.

Two shapes: a `desc` whose `desc_content` holds nothing but generated
paragraphs, index entries and nested objects; and an autosummary row
whose summary cell is an empty paragraph (autodoc leaves undocumented
members out of the page entirely, so the table row is all a reader sees).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.missing_images(html, , page_dir)

`<img src>` values that resolve to no file next to the page.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.rendered.missing_images_detector(outdirs, \_docsrc)

Level-2 detector over the `html` output (DR024 at level 2).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.render_detector(name)

Register a level-2 detector; the ledger loader validates `html` rules against it.

### epythet.validation.rendered.render_findings(outdirs, ledger, , docsrc)

Run every `html`-kind rule of the ledger over the rendered output.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)]

### epythet.validation.rendered.run_render_level(project_dir, ledger, , backend, outdir, snapshot=False, update=False, snapshot_dir=None)

Level 2: render html, text and xml into `outdir` and read them.

Returns `(findings, notes, artifacts)`; the artifacts hand level 3 the
output directories and the snapshot diff so it never builds again.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`RenderArtifacts`](#epythet.validation.rendered.RenderArtifacts)]

### epythet.validation.rendered.snapshot_findings(diff, ledger)

One DR035 finding per changed page, plus info findings for new and removed pages.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)]

### epythet.validation.rendered.text_snapshots_detector(\_outdirs, \_docsrc)

DR035’s detector is the snapshot diff, driven by `snapshot=`; nothing to scan here.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.unresolved_xrefs(outdirs, \_docsrc)

Level-2 detector over the `xml` output (DR023 at level 2).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.unresolved_xrefs_in(root)

Cross-references that rendered as plain code: an `xref` literal no `reference` wraps.

Autosummary rows are left out: an unwrapped name there means an
undocumented object (reported by [`empty_descriptions_in()`](#epythet.validation.rendered.empty_descriptions_in)), not a
bad target.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`RenderHit`](#epythet.validation.rendered.RenderHit)]

### epythet.validation.rendered.update_snapshots(text_dir, snapshot_dir)

Replace the stored snapshots with the current render; returns pages written.

* **Return type:**
  [`int`](https://docs.python.org/3/library/functions.html#int)
