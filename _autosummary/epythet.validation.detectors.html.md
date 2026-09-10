# epythet.validation.detectors

Named doctree detectors, referenced from ledger rules by `detector.function`.

Each detector takes a [`ParsedDocstring`](epythet.validation.parse.html.md#epythet.validation.parse.ParsedDocstring) and
returns a list of evidence strings, one per hit (an empty list means the rule
does not fire). They read the docutils doctree rather than rendered HTML so
that the rules keep working under any Sphinx theme, and under a MkDocs
backend, exactly as decided in D8.

The detectors are the measured prototype from the validation research
(`detect2.py` and `refine.py`), ported one to one; the refinements that
took false positives from 2/14 to 1/14 on the control set are marked inline.

### Module Attributes

| [`DETECTORS`](#epythet.validation.detectors.DETECTORS)         | Registry filled by [`detector()`](#epythet.validation.detectors.detector); the ledger loader validates against it.   |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [`NAPOLEON_SECTIONS`](#epythet.validation.detectors.NAPOLEON_SECTIONS) | Section names napoleon recognises (Google style), lower-cased.                                                            |
| [`NEAR_SECTIONS`](#epythet.validation.detectors.NEAR_SECTIONS)     | Common misspellings / near-misses of section names that napoleon ignores.                                                 |

### Functions

| [`blockquote_with_unexpected_indent`](#epythet.validation.detectors.blockquote_with_unexpected_indent)(parsed)   | A block quote *and* an `Unexpected indentation` message: stray indent (DR016).       |
|----------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`collapsed_table`](#epythet.validation.detectors.collapsed_table)(parsed)                     | A simple-table border in the source with no `table` node in the tree (DR019).        |
| [`detector`](#epythet.validation.detectors.detector)(name)                              | Register a detector under `name` (the name used in rule YAML).                       |
| [`directive_content_lost`](#epythet.validation.detectors.directive_content_lost)(parsed)              | A directive is written in the source but produced no content node (DR018).           |
| [`markdown_fence_literal`](#epythet.validation.detectors.markdown_fence_literal)(parsed)              | A Markdown fence collapsed into an inline literal (DR006).                           |
| [`mixed_bullet_markers`](#epythet.validation.detectors.mixed_bullet_markers)(parsed)                | Two adjacent sibling bullet lists: the marker character changed mid-list (DR022).    |
| [`near_miss_section_term`](#epythet.validation.detectors.near_miss_section_term)(parsed)              | A definition-list term that is a misspelt section name (DR013).                      |
| [`param_definition_list`](#epythet.validation.detectors.param_definition_list)(parsed)               | A top-level definition list of single-word terms: probably a parameter list (DR017). |
| [`problematic_nodes`](#epythet.validation.detectors.problematic_nodes)(parsed)                   | Unbalanced inline markup: every `problematic` node in the tree (DR010).              |
| [`prose_definition_term`](#epythet.validation.detectors.prose_definition_term)(parsed)               | A definition-list term of three or more words: prose eaten by indentation (DR014).   |
| [`section_as_definition_list`](#epythet.validation.detectors.section_as_definition_list)(parsed)          | A Google section (`Args:`) became a definition-list term: napoleon is off (DR012).   |
| [`system_messages`](#epythet.validation.detectors.system_messages)(parsed)                     | Every message docutils reported while parsing the docstring (DR032).                 |
| [`title_references`](#epythet.validation.detectors.title_references)(parsed)                    | Single backticks parsed as a title reference, i.e. italics not code (DR011).         |

### epythet.validation.detectors.DETECTORS *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), Detector]* *= {'blockquote_with_unexpected_indent': <function blockquote_with_unexpected_indent>, 'collapsed_table': <function collapsed_table>, 'directive_content_lost': <function directive_content_lost>, 'markdown_fence_literal': <function markdown_fence_literal>, 'mixed_bullet_markers': <function mixed_bullet_markers>, 'near_miss_section_term': <function near_miss_section_term>, 'param_definition_list': <function param_definition_list>, 'problematic_nodes': <function problematic_nodes>, 'prose_definition_term': <function prose_definition_term>, 'section_as_definition_list': <function section_as_definition_list>, 'system_messages': <function system_messages>, 'title_references': <function title_references>}*

Registry filled by [`detector()`](#epythet.validation.detectors.detector); the ledger loader validates against it.

### epythet.validation.detectors.NAPOLEON_SECTIONS *= frozenset({'args', 'arguments', 'attention', 'attributes', 'caution', 'danger', 'error', 'example', 'examples', 'hint', 'important', 'keyword args', 'keyword arguments', 'methods', 'note', 'notes', 'other parameters', 'parameters', 'raise', 'raises', 'receive', 'receives', 'references', 'return', 'returns', 'see also', 'tip', 'todo', 'warning', 'warnings', 'warns', 'yield', 'yields'})*

Section names napoleon recognises (Google style), lower-cased.

### epythet.validation.detectors.NEAR_SECTIONS *= frozenset({'arg', 'argument', 'attribute', 'exception', 'exceptions', 'exemple', 'exemples', 'kwarg', 'kwargs', 'param', 'parameter', 'params', 'rasies', 'retruns', 'returnss', 'yeilds'})*

Common misspellings / near-misses of section names that napoleon ignores.

### epythet.validation.detectors.blockquote_with_unexpected_indent(parsed)

A block quote *and* an `Unexpected indentation` message: stray indent (DR016).

The message gate is what makes this reliable; a block quote alone is how a
legitimate quotation is written (research §3.3).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.collapsed_table(parsed)

A simple-table border in the source with no `table` node in the tree (DR019).

Refinement from the research: the border line must contain two or more
whitespace-separated runs of `=`, otherwise a section underline matches.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.detector(name)

Register a detector under `name` (the name used in rule YAML).

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`ParsedDocstring`](epythet.validation.parse.html.md#epythet.validation.parse.ParsedDocstring)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`ParsedDocstring`](epythet.validation.parse.html.md#epythet.validation.parse.ParsedDocstring)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]]

### epythet.validation.detectors.directive_content_lost(parsed)

A directive is written in the source but produced no content node (DR018).

With stub directives registered, an unknown directive name (`.. codeblock::`)
or a body that docutils rejected leaves only a system message behind; the
content the author wrote is gone from the page.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.markdown_fence_literal(parsed)

A Markdown fence collapsed into an inline literal (DR006).

Refinement from the research: a triple-backtick fence parses as an inline
`literal` whose text starts or ends with a backtick, because two of the
fence characters are consumed as the literal’s delimiters. Testing for
three backticks in the paragraph text does not work.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.mixed_bullet_markers(parsed)

Two adjacent sibling bullet lists: the marker character changed mid-list (DR022).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.near_miss_section_term(parsed)

A definition-list term that is a misspelt section name (DR013).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.param_definition_list(parsed)

A top-level definition list of single-word terms: probably a parameter list (DR017).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.problematic_nodes(parsed)

Unbalanced inline markup: every `problematic` node in the tree (DR010).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.prose_definition_term(parsed)

A definition-list term of three or more words: prose eaten by indentation (DR014).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.section_as_definition_list(parsed)

A Google section (`Args:`) became a definition-list term: napoleon is off (DR012).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.system_messages(parsed)

Every message docutils reported while parsing the docstring (DR032).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### epythet.validation.detectors.title_references(parsed)

Single backticks parsed as a title reference, i.e. italics not code (DR011).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]
