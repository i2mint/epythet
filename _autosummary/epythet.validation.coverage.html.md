# epythet.validation.coverage

Level 0 coverage and quality smells: the queue signals, computed from the `ast` alone.

The doc-quality research (`research_doc_quality.md` §2, §6) defines what
the fleet sweep should *queue*, as opposed to gate: a public callable with
no docstring, an entry point with no runnable example, a summary that only
restates the name, a parameter description that only restates the type, a
summary written as meta-language (“This function…”). None of these needs
ruff or pydoclint, so the sweep can run them on a checkout that has neither;
none of them changes the exit code unless `--fail-on info` asks for it.

The public surface follows the R1 decision: `__all__` is honoured where
present, otherwise every non-underscore name; *entry points* are the names
the package’s `__init__` binds (its `__all__`, else what it defines and
imports), and only those owe an example.

Each detector is a function `PublicObject -> list[str]` registered under
the name a `coverage`-kind ledger rule refers to. The two text heuristics
are the research’s, verbatim:

- trivial summary: split the identifier on `snake_case`/`camelCase`,
  split the summary on whitespace, strip stop words, crude lemmatisation;
  flag when the summary’s content words are a subset of the name’s;
- type restatement: flag a parameter description whose content words are a
  subset of the annotation’s tokens (`n: int` described as “an integer”).

```pycon
>>> trivial_summary_words("load_config", "Load the config.")
True
>>> trivial_summary_words("load_config", "Read pyproject.toml and setup.cfg into a DocsConfig.")
False
```

### Functions

| [`annotation_words`](#epythet.validation.coverage.annotation_words)(annotation)                       | Words a reader could use to restate an annotation: `list[int]` -> int, list, integer...             |
|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| [`content_words`](#epythet.validation.coverage.content_words)(text)                                | Content words of prose: lower-cased, stop words out, crudely lemmatised.                            |
| [`coverage_detector`](#epythet.validation.coverage.coverage_detector)(name)                            | Register a coverage detector under the name a rule's `detector.function` uses.                      |
| [`entry_point_names`](#epythet.validation.coverage.entry_point_names)(package_dir)                     | Names the package's `__init__` exposes: `__all__`, else what it binds without a leading underscore. |
| [`entry_point_without_example`](#epythet.validation.coverage.entry_point_without_example)(obj)                   | An entry point (bound by the package `__init__`) whose docstring has no `>>>` (DQ002).              |
| [`evaluate_coverage_rule`](#epythet.validation.coverage.evaluate_coverage_rule)(rule, obj)                  | Run one `coverage`-kind rule over one public object.                                                |
| [`iter_coverage_cases`](#epythet.validation.coverage.iter_coverage_cases)(fixture_path)                  | The tagged specimens of a coverage fixture (a specimen may have no docstring at all).               |
| [`iter_public_objects`](#epythet.validation.coverage.iter_public_objects)(package_dir, \*[, ...])        | Every public module, class and function under `package_dir`.                                        |
| [`meta_language_summary`](#epythet.validation.coverage.meta_language_summary)(obj)                         | A summary that talks about the object instead of saying what it does (DQ005).                       |
| [`missing_docstring`](#epythet.validation.coverage.missing_docstring)(obj)                             | A public module, class or function with no docstring at all (DQ001).                                |
| [`name_words`](#epythet.validation.coverage.name_words)(identifier)                             | Content words of an identifier: `load_config` -> `{"load", "config"}`.                              |
| [`param_descriptions`](#epythet.validation.coverage.param_descriptions)(docstring)                      | `{name: description}` from an RST, Google or NumPy docstring, first line plus continuations.        |
| [`restates_type`](#epythet.validation.coverage.restates_type)(param)                               | Whether a parameter's description only restates its annotation.                                     |
| [`run_coverage_level`](#epythet.validation.coverage.run_coverage_level)(package_dir, ledger, \*[, ...]) | Level 0 coverage: `(findings, objects_checked, objects_undocumented)`.                              |
| [`trivial_summary`](#epythet.validation.coverage.trivial_summary)(obj)                               | A summary whose content words all come from the object's name (DQ003).                              |
| [`trivial_summary_words`](#epythet.validation.coverage.trivial_summary_words)(identifier, summary)         | Whether the summary's content words are all in the identifier's (the *lazy* smell).                 |
| [`type_restatement`](#epythet.validation.coverage.type_restatement)(obj)                              | A parameter description that only restates the annotation (DQ004).                                  |

### Classes

| [`CoverageCase`](#epythet.validation.coverage.CoverageCase)(name, line, expect_hit, ...)     | One tagged specimen of a coverage fixture: the object and what the tag promises.   |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`Param`](#epythet.validation.coverage.Param)(name[, annotation, description])        | A signature parameter and, if the docstring describes it, that description.        |
| [`PublicObject`](#epythet.validation.coverage.PublicObject)(qualname, kind, file, line, ...) | One public module, class or function, with what a detector needs to judge it.      |

### *class* epythet.validation.coverage.CoverageCase(name, line, expect_hit, rule_ids, object)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One tagged specimen of a coverage fixture: the object and what the tag promises.

### *class* epythet.validation.coverage.Param(name, annotation=None, description=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A signature parameter and, if the docstring describes it, that description.

### *class* epythet.validation.coverage.PublicObject(qualname, kind, file, line, docstring, params=<factory>, is_entry_point=False, name='')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One public module, class or function, with what a detector needs to judge it.

#### *property* summary *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The first non-blank line of the docstring, or `""`.

### epythet.validation.coverage.annotation_words(annotation)

Words a reader could use to restate an annotation: `list[int]` -> int, list, integer…

* **Return type:**
  [`set`](https://docs.python.org/3/library/stdtypes.html#set)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.content_words(text)

Content words of prose: lower-cased, stop words out, crudely lemmatised.

* **Return type:**
  [`set`](https://docs.python.org/3/library/stdtypes.html#set)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.coverage_detector(name)

Register a coverage detector under the name a rule’s `detector.function` uses.

### epythet.validation.coverage.entry_point_names(package_dir)

Names the package’s `__init__` exposes: `__all__`, else what it binds without a leading underscore.

* **Return type:**
  [`set`](https://docs.python.org/3/library/stdtypes.html#set)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.entry_point_without_example(obj)

An entry point (bound by the package `__init__`) whose docstring has no `>>>` (DQ002).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.evaluate_coverage_rule(rule, obj)

Run one `coverage`-kind rule over one public object.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.iter_coverage_cases(fixture_path)

The tagged specimens of a coverage fixture (a specimen may have no docstring at all).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`CoverageCase`](#epythet.validation.coverage.CoverageCase)]

### epythet.validation.coverage.iter_public_objects(package_dir, , ignore=(), files=None, all_entry_points=False)

Every public module, class and function under `package_dir`.

Public means no leading underscore anywhere in the dotted name below the
package; a module’s `__all__`, when present, narrows its public names.
`all_entry_points` treats every top-level name as an entry point (rule
fixtures use it: they have no package `__init__`).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`PublicObject`](#epythet.validation.coverage.PublicObject)]

### epythet.validation.coverage.meta_language_summary(obj)

A summary that talks about the object instead of saying what it does (DQ005).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.missing_docstring(obj)

A public module, class or function with no docstring at all (DQ001).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.name_words(identifier)

Content words of an identifier: `load_config` -> `{"load", "config"}`.

* **Return type:**
  [`set`](https://docs.python.org/3/library/stdtypes.html#set)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> sorted(name_words("DocsConfig")), sorted(name_words("mk_parser"))
(['config', 'doc'], ['mk', 'parser'])
```

### epythet.validation.coverage.param_descriptions(docstring)

`{name: description}` from an RST, Google or NumPy docstring, first line plus continuations.

Deliberately not delegated to `docstring_parser` (an optional extra):
a detector’s verdict must not depend on what is installed.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> param_descriptions(":param n: how many\n    retries\n:param delay: seconds")
{'n': 'how many retries', 'delay': 'seconds'}
>>> param_descriptions("Args:\n    n (int): how many\n    delay: seconds\n\nReturns:\n    x")
{'n': 'how many', 'delay': 'seconds'}
>>> param_descriptions("Parameters\n----------\nn : int\n    how many\ndelay\n    seconds\n\nReturns\n-------")
{'n': 'how many', 'delay': 'seconds'}
```

### epythet.validation.coverage.restates_type(param)

Whether a parameter’s description only restates its annotation.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

```pycon
>>> restates_type(Param("n", "int", "an integer"))
True
>>> restates_type(Param("n", "int", "how many retries before giving up"))
False
>>> restates_type(Param("n", None, "an integer"))
False
```

### epythet.validation.coverage.run_coverage_level(package_dir, ledger, , ignore=())

Level 0 coverage: `(findings, objects_checked, objects_undocumented)`.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`int`](https://docs.python.org/3/library/functions.html#int), [`int`](https://docs.python.org/3/library/functions.html#int)]

### epythet.validation.coverage.trivial_summary(obj)

A summary whose content words all come from the object’s name (DQ003).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.coverage.trivial_summary_words(identifier, summary)

Whether the summary’s content words are all in the identifier’s (the *lazy* smell).

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

### epythet.validation.coverage.type_restatement(obj)

A parameter description that only restates the annotation (DQ004).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]
