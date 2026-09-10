---
name: epythet-docstring-style
description: >-
  Write and improve Python docstrings that render correctly in epythet/Sphinx
  and that help both humans and AI agents: the epythet docstring dialect
  (Google sections, doctests, types in annotations), the quality rubric, the
  behaviour-claim policy (never document behaviour you have not verified), and
  the anti-patterns to avoid. Use when writing or editing docstrings, when
  asked to "document this function/module/package", "improve the docstrings",
  "add examples", "fix the docstring style", or when reviewing a docstring
  sweep. Also use before answering "should the type go in the docstring".
license: Apache-2.0
metadata:
  audience: users
---

# epythet-docstring-style: docstrings for humans and agents

Two facts govern everything here. **Incorrect documentation measurably hurts agents (about 23 points of task success in a controlled study); missing documentation is roughly neutral.** And **examples help more than prose**: for less-common libraries, example code is the documentation element that helps agents most. So: never invent behaviour, and spend the effort on runnable examples for entry points.

## The dialect (what to write)

The intersection of Markdown habits and reStructuredText that renders correctly under epythet, with no RST roles or directives needed:

- **Summary line**: one sentence, on the first line, ends with a period. Does not repeat the object's name, no meta-language ("This function..."), no internal period. Say what it does and, when siblings exist, what distinguishes it.
- **Sections in Google style**: `Args:`, `Returns:`, `Yields:`, `Raises:`, `Attributes:`, `Examples:`, `See Also:`. Existing RST field lists (`:param x:`) keep rendering; do not convert them en masse, but write new docstrings in Google style.
- **Types live in annotations, never in the docstring.** `def f(x: list[str]) -> dict[str, int]` is the type SSOT; the docstring says what `x` *means*, its units, valid range, and what the default *does*. Modern generics like `list[str]` cannot even be cross-referenced from docstring text.
- **Examples are doctests** under an `Examples:` header or after a blank line: `>>> f(1)` then the real output. Deterministic: seeded randomness, no clock, no network, no unordered dict output.
- **Inline code** with single or double backticks (single backticks render as code in epythet sites). `**bold**` works. Bullet lists need a blank line before them. Fenced code blocks (```` ```python ````) are accepted and converted.
- **Escape nothing by hand**: `*args` and `**kwargs` in prose are handled at build time. Write them plainly.
- **Avoid**: `## Headings` inside docstrings (use a short bold phrase or a section), Markdown links (allowed, converted, but a plain URL is clearer in source), tables, images.

What epythet's normalizer repairs at build time (so existing code renders, not so you may rely on it): doctest or bullet list glued to prose, ```` ``` ```` fences, `Returns: text` on one line, `## Heading`, `[text](url)`, unescaped `*args`, `Examples:` followed by an unindented doctest.

## The shape by size (three tiers)

**Tier 1, tiny helper** (private, or public but obvious; roughly 15 lines or fewer, no surprises): a one-line summary. Add `Args:` only for a parameter whose meaning is not evident from `name: type`. No example, no `Returns:` unless non-obvious. Target: 1 to 3 lines.

**Tier 2, entry point** (a name in `__all__` or re-exported from `__init__`): a disambiguating summary; two to four sentences of intent (what problem it solves); `Args:` with semantics, units, ranges, default behaviour; `Returns:` saying what the value is and how it is keyed or ordered; `Raises:` with trigger conditions; **at least one runnable doctest** for the common case plus one variation; `See Also:` naming 1 to 3 adjacent callables with how each differs; a when-to-use sentence if a near-neighbour exists. Target: 15 to 40 lines.

**Tier 3, complex class**: everything in Tier 2 on the class docstring (not `__init__`); `Attributes:` with invariants; a lifecycle sketch (construct, configure, use, tear down) as a doctest; state invariants (what mutates, what is safe to reuse); methods at Tier 1 or 2. Target: 40 to 80 lines on the class.

**Module docstring** (required on every non-underscore module): one line on purpose; two to four sentences of intent and how the module relates to the package; a curated `Main entry points:` block naming the 2 to 5 things to start with (a curation, not an inventory); one minimal doctest.

```python
"""<One line: what this module is for.>

<2-4 sentences: the problem it solves, the mental model, its place in the package.>

Main entry points:
    <name>: <one clause>
    <name>: <one clause>

    >>> from pkg.module import main_thing
    >>> main_thing([1, 2, 3])
    6
"""
```

## The behaviour-claim policy (what you may say)

An unverified behavioural claim is worse than no claim.

- **May always change**: formatting, section order, first-sentence style; removing type restatement and meta-language; removing a documented parameter that no longer exists; fixing a name that does not resolve; deleting a claim the code demonstrably contradicts.
- **Only after reading the implementation and the tests**: parameter semantics, return description, documented exceptions, when-to-use guidance.
- **Only after running it**: any example. Execute the doctest and paste the real output; never predict it. If you cannot execute (no environment, missing optional dependency), do not add the example: file it as a work item.
- **Never**: infer behaviour from the name; copy a claim from a sibling; state complexity, thread-safety or performance properties not evidenced in code or tests; describe a valid range not enforced or documented anywhere; document exceptions raised by *violating* the documented API (that makes violation behaviour part of the contract).
- **On uncertainty, downgrade rather than guess**: replace a specific suspect claim with a weaker true one, or delete it, and record the deletion.
- **Acceptance test**: ask a separate model to predict the function's output on a few inputs from the docstring alone, then run the function. Disagreement means the docstring is wrong or ambiguous.

## The procedure for one docstring

1. Read the whole implementation: every `raise`, early return, silent coercion, argument mutation.
2. Read the tests that exercise it. None? Note it; it limits what you may claim.
3. Read the siblings in the module, for disambiguation, `See Also`, and the package's terminology.
4. Score the current docstring on the rubric (below); record the before-score.
5. Write the summary first, alone. If it cannot add information beyond the name, this is Tier 1: stop after the summary.
6. Write the example next and **run it**. Paste the real output. If it fails, fix the example, not the expected output.
7. Fill in `Args:` / `Returns:` / `Raises:`, taking types from annotations and saying only what the annotation does not.
8. Failure modes and cross-references (1 to 3, with reasons).
9. Re-run the test suite and doctests (`pytest --doctest-modules`).
10. Record the after-score and every claim you declined to make.

## The quality rubric (six dimensions, 0 to 3 each)

| Dim | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| A Summary | absent | restates the name or uses meta-language | one verb-first sentence saying what it does | also implies when to reach for it; disambiguates from siblings |
| B Parameter and return semantics | absent | names listed, descriptions restate the type | each parameter's meaning, units, default behaviour | also parameter interactions, value ranges, what the return is keyed or ordered by |
| C Example presence and runnability | none | present but not runnable (pseudo-code, `...`, no output) | one runnable doctest for the common case | also a meaningful variation or edge case; deterministic |
| D Failure modes | nothing | exceptions named without cause | each exception paired with its trigger | also non-exception failures: silent coercions, empty input, partial failure |
| E Cross-references | none | a related name in prose | `See Also` with 1 to 3 adjacent callables and why each differs | also when *not* to use this one |
| F Module orientation | no module docstring | one line restating the name | purpose plus named entry points | also a minimal end-to-end example and how the module relates to the package |

Fleet targets: entry points mean 12/18 or more with A and C at 2 or more; other public callables A at 2 or more; private helpers A at 1; modules F at 2 or more. Do not chase a single aggregate percentage: the cheapest way to raise a score is to add words, which produces the *bloated* smell.

## Anti-patterns (and why)

| Anti-pattern | Why it is bad |
|---|---|
| Hallucinated behaviour | measured 22.6 point accuracy cost for agents |
| Restating the name (`get_users`: "Gets users.") | the *lazy* smell, 27.5 percent prevalence; counts as covered, says nothing |
| Restating the type (`n: int`, "An integer.") | pure token cost; the annotation is the SSOT |
| Meta-language ("This function will return...") | prohibited by Google's style rules |
| Over-long docstrings | 25 to 40 percent of docstring tokens are removable without loss; context rot |
| Tutorial in a docstring | wrong place; belongs in the README or docs pages |
| Non-deterministic examples (clock, network, unseeded RNG, dict order) | flaky doctests kill the doctest gate |
| Elided examples (`...`, `# etc.`, pseudo-code) | not runnable, so not verified, so not trusted |
| Exhaustive `See Also` | the *fragmented* smell; each link costs an agent a retrieval hop |
| Documenting API-violation behaviour ("Raises TypeError if you pass a str") | makes violations part of the contract |
| Copying a sibling's docstring | the *tangled* smell and near-certain incorrectness |

Noise rules: if the only true thing you can say restates the name, write the one-line summary and stop. Never write "Returns: the result". Never manufacture an `Args:` block for a two-parameter helper whose parameters are self-evident. A sweep that triples mean docstring length has probably made things worse.

## Division of labour (one home per fact)

| Content | Home |
|---|---|
| What one function or class does, its parameters, returns, raises, example | docstring |
| What a module is for, its 2 to 5 entry points, one minimal example | module docstring |
| What the package is for, install, smallest working example, links out | README (thin) |
| Concepts, design rationale, tutorials, how-tos | docs site pages |
| Conventions, commands, project workflow for agents | `AGENTS.md` / `CLAUDE.md` (keep under about 200 lines) |
| Reusable procedures for working *with* the package | skill files |
| The flat single-file view of everything | the generated `<package>.md` aggregate, never hand-maintained |

API facts live in docstrings and are generated upward. A README or skill that restates a signature is a drift source with no verification.

## Checks to run

- `epythet validate PROJECT_DIR` (level 1 by default: lint plus a doctree parse of every docstring, no build) catches rendering artifacts before they reach the site; `--level 2` adds the Sphinx build (needs a `docsrc/conf.py`, so run `epythet quickstart` first). See the `epythet-validate` skill.
- `pytest --doctest-modules` is the behavioural gate: every example must run.
- Ruff with `[tool.ruff.lint.pydocstyle] convention = "google"` gives `D417` (undocumented parameter); `pydoclint` with `--arg-type-hints-in-docstring=False` checks `Returns`/`Raises` against the body.

References: the research behind these rules is summarised in [`references/evidence.md`](references/evidence.md).
