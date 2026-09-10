# epythet.validation.review

Level 3: a review *packet* for an in-session agent, and the ingestion of its reply.

Level 3 never calls a model itself and never gates (decision D8; research
§7.3). It packs what a reviewer needs into one directory under the user data
dir and stops:

- `pages/<docname>.txt`: the `-b text` render of the pages to review
  (changed against the snapshot when there is one, else a sample), which is
  about nine times fewer tokens than the HTML (research §7.3);
- `screenshots/<docname>.png`: optional, when Playwright is installed and
  `screenshots=True`;
- `rubric.md`: the six-dimension rubric, the ledger’s rule ids for
  grounding, and the review controls;
- `schema.json`: the strict JSON schema the reply must satisfy;
- `packet.json`: the manifest (package, version, pages, prompt hash).

An agent (through a skill; the maintainer’s decision 7) reads the packet and
writes `review.json`. Passing that file back as `review_reply=` turns its
`findings` into level-3 findings and leaves its `proposed_rules` for
`epythet ledger propose`, which writes them as `status: proposed` rules
into an overlay for a human to promote.

```pycon
>>> from epythet.validation.review import REPLY_SCHEMA
>>> sorted(REPLY_SCHEMA["properties"])
['findings', 'model', 'prompt_hash', 'proposed_rules', 'schema_version']
```

### Module Attributes

| [`PACKET_RULE`](#epythet.validation.review.PACKET_RULE)   | The rule id of the one finding a packet run always produces.    |
|----------------------------------------------------------------|-----------------------------------------------------------------|
| [`UNRULED`](#epythet.validation.review.UNRULED)       | The rule id of a reply finding that names no ledger rule.       |
| [`RUBRIC`](#epythet.validation.review.RUBRIC)        | The six dimensions of research_doc_quality §3, scored 0-3 each. |

### Functions

| [`load_reply`](#epythet.validation.review.load_reply)(path)                                   | Read and validate a `review.json`.                                                                         |
|-----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| [`reply_findings`](#epythet.validation.review.reply_findings)(reply, ledger, \*[, source])        | Turn a reply's `findings` into level-3 findings (informational by construction).                           |
| [`reviews_dir`](#epythet.validation.review.reviews_dir)()                                      | `<user data dir>/review`: one subdirectory per package, one per run below it.                              |
| [`rubric_text`](#epythet.validation.review.rubric_text)(ledger)                                | The rubric with the ledger's rule ids appended, so replies can name them.                                  |
| [`run_review_level`](#epythet.validation.review.run_review_level)(\*, package, ...[, changed, ...]) | Level 3: write the packet, then ingest `reply` when one is given.                                          |
| [`select_pages`](#epythet.validation.review.select_pages)(available, \*[, mode, changed, ...])  | Which pages go into the packet.                                                                            |
| [`validate_reply`](#epythet.validation.review.validate_reply)(reply)                              | Raise [`ReplyError`](#epythet.validation.review.ReplyError) unless `reply` satisfies `REPLY_SCHEMA`. |
| [`write_packet`](#epythet.validation.review.write_packet)(\*, package, package_version, ...)    | Write a review packet and return where it is.                                                              |

### Classes

| [`ReviewPacket`](#epythet.validation.review.ReviewPacket)(path[, pages, screenshots, ...])   | Where a packet was written and what went into it.   |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------|

### Exceptions

| [`ReplyError`](#epythet.validation.review.ReplyError)   | A review reply is not valid against `REPLY_SCHEMA`.   |
|---------------------------------------------------------------|-------------------------------------------------------|

### epythet.validation.review.PACKET_RULE *= 'REVIEW'*

The rule id of the one finding a packet run always produces.

### epythet.validation.review.RUBRIC *= '# Review rubric\\n\\nScore each documented object on the page 0-3 on the six dimensions below.\\nOnly report an object whose score is 0 or 1 on a dimension, or whose page\\nshows a rendering artifact. Never report a style preference.\\n\\n| Dimension | 0 | 1 | 2 | 3 |\\n|---|---|---|---|---|\\n| A. Summary | absent | restates the name, or meta-language ("This function...") | one verb-first sentence saying what it does | also implies when to reach for it and disambiguates siblings |\\n| B. Parameter and return semantics | absent | descriptions restate the type | meaning, units, default behaviour | plus interactions, ranges, what the return is keyed or ordered by |\\n| C. Example presence and runnability | none | present but not runnable (pseudo-code, \`...\`, no output) | one runnable doctest for the common case | plus a variation or edge case; deterministic |\\n| D. Failure modes | nothing | exceptions named without cause | each exception paired with its trigger | plus non-exception failure modes |\\n| E. Cross-references and orientation | none | related name in prose | See Also with 1-3 adjacent callables and why | plus when \*not\* to use |\\n| F. Module orientation (per module) | none | one line restating the name | purpose and named entry points | plus a minimal example and the relation to the package |\\n\\n# What to look for first (research_doc_quality §4.3)\\n\\n1. Runnable examples. 2. Correctness of every claim (ranks above completeness).\\n3. A precise, disambiguating one-line summary. 4. Parameter \*semantics\*, not types.\\n5. Failure modes. 6. When to use and when not. 7. Consistent terminology.\\n8. Cross-references, one to three, with reasons.\\n\\n# Rendering artifacts\\n\\nA \`-b text\` page keeps text leaks verbatim: a \`:param x:\` in running prose,\\na \`>>>\` inside a paragraph, a literal \`\`\`\` \`\`\` \`\`\`\` fence, \`\*args\` opening\\nan emphasis, a \`##\` heading, a \`[text](url)\` link. Each of those is a ledger\\nrule (below). Name the rule id when one fits; otherwise mark the finding\\n\`proposed\` and draft a rule under \`proposed_rules\`.\\n\\n# Controls\\n\\n- You are proposing, not gating: nothing here fails a build.\\n- Report only what is stable: re-read the page in a different order and keep\\n  the findings you would make both times.\\n- Name a \`rule\` from the list below, or write \`proposed\` and fill in\\n  \`proposed_rules\` with a detector a machine can run (a regex over the\\n  docstring text, or a doctree/html detector name), an \`example_bad\` and an\\n  \`example_good\` docstring, a \`message\` and a \`fix\` hint.\\n- Never invent behaviour: a claim about what code does must come from the\\n  code or its tests, and an example must have been executed.\\n- Put the model name in \`model\` and the packet\\'s \`prompt_hash\` in the reply.\\n\\n# Ledger rules you may name\\n'*

The six dimensions of research_doc_quality §3, scored 0-3 each.

### *exception* epythet.validation.review.ReplyError

Bases: [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

A review reply is not valid against `REPLY_SCHEMA`.

### *class* epythet.validation.review.ReviewPacket(path, pages=<factory>, screenshots=<factory>, prompt_hash='', notes=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Where a packet was written and what went into it.

### epythet.validation.review.UNRULED *= 'REVIEW-PROPOSED'*

The rule id of a reply finding that names no ledger rule.

### epythet.validation.review.load_reply(path)

Read and validate a `review.json`.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### epythet.validation.review.reply_findings(reply, ledger, , source='')

Turn a reply’s `findings` into level-3 findings (informational by construction).

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)]

### epythet.validation.review.reviews_dir()

`<user data dir>/review`: one subdirectory per package, one per run below it.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### epythet.validation.review.rubric_text(ledger)

The rubric with the ledger’s rule ids appended, so replies can name them.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### epythet.validation.review.run_review_level(, package, package_version, outdirs, ledger, changed=None, mode='changed', sample=8, screenshots=False, packet_dir=None, reply=None)

Level 3: write the packet, then ingest `reply` when one is given.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`Finding`](epythet.validation.model.html.md#epythet.validation.model.Finding)], [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]

### epythet.validation.review.select_pages(available, , mode='changed', changed=None, sample=8)

Which pages go into the packet.

`changed` mode uses the snapshot diff when there is one and falls back
to `sample` (the first `sample` API pages, index first) otherwise;
`all` takes every page.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> select_pages(["index", "api", "_autosummary/p", "_autosummary/p.m"], mode="sample", sample=2)
['index', '_autosummary/p']
>>> select_pages(["index", "a"], mode="changed", changed=["a"])
['a']
```

### epythet.validation.review.validate_reply(reply)

Raise [`ReplyError`](#epythet.validation.review.ReplyError) unless `reply` satisfies `REPLY_SCHEMA`.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

### epythet.validation.review.write_packet(, package, package_version, outdirs, ledger, changed=None, mode='changed', sample=8, screenshots=False, packet_dir=None)

Write a review packet and return where it is.

* **Return type:**
  [`ReviewPacket`](#epythet.validation.review.ReviewPacket)
