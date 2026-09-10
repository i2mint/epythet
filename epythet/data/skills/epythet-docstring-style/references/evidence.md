# Evidence behind the docstring rules

Key measured findings, with the sources the rules rest on. Numbers are quoted from the studies; read the originals before generalising.

## Governing findings

1. **Incorrect documentation hurts; missing documentation is neutral.** Macke and Doyle (2024) compared base code, docstrings, randomised (incorrect) comments and partially removed docstrings on all 164 HumanEval solutions with GPT-3.5 and GPT-4. Incorrect comments were the worst condition (about a 22.6 percentage-point drop for GPT-4); removing docstrings entirely produced no statistically significant degradation. [1]
2. **Examples dominate prose.** Chen et al. (2025) studied 1,017 APIs across four less-common Python libraries: retrieval-augmented API documentation improved code-generation success by 83 to 220 percent, and "example code contributes the most to advance LLMs, instead of the descriptive texts and parameter lists". Models tolerated mild noise (typos, slightly wrong parameter names) but not missing examples. [3]
3. **Documentation buys the most when the model does not already know the library.** Reformulating docstrings on well-known benchmark code changed nothing measurable [6]; 25 to 40 percent of docstring tokens can be deleted with no quality loss [7]. A private ecosystem of small packages is exactly the "less common library" regime where documentation pays.
4. **Humans and agents want nearly the same thing**, diverging on locality: an agent reading a flat aggregate pays a retrieval cost for every cross-reference hop and degrades as context grows [9]. Prefer self-contained docstrings and 1 to 3 cross-references with reasons over a web of links (the *fragmented* smell, 19.6 percent of a 1,000-unit benchmark [10]).
5. **Coverage tools measure presence, not information.** The *lazy* smell (a docstring that restates the name) was the most prevalent smell at 27.5 percent [10] and is what a naive LLM sweep produces at scale. A trivial-summary detector (summary content words a subset of the name's content words) is cheap.
6. **Verification is the hard part.** Doctests make the example both the documentation and the test. LLM-based inconsistency detectors reach precision 0.58 to 0.70 [15] and are usable for ranking a work queue, never as a merge gate.

## Which elements matter, ranked for agents

1. Runnable examples (highest measured contribution; the only self-verifying element).
2. Correctness of every claim (negative value if violated; ranks above completeness).
3. A precise, disambiguating one-line summary (it survives truncation, indexing and aggregation; many tools extract only the first sentence [19]).
4. Parameter semantics, not types (meaning, units, ranges, default behaviour, interactions).
5. Failure modes (an agent cannot cheaply probe).
6. When-to-use / when-not (disambiguates siblings).
7. Terminology consistency across the package.
8. Cross-references, 1 to 3 with reasons.

## Why Google style, and why types belong in annotations

- Google's style guide already says `Args:` descriptions include types only "if the code does not contain a corresponding type annotation" [33]. numpydoc's maintainers explicitly reject that position; the two are incompatible and Google's avoids duplication.
- `Examples:` headers make the highest-value content artifact-proof: napoleon inserts the blank line after a recognised section header, so `Examples:` then `>>>` is safe while prose then `>>>` is not.
- Google is the only convention under which Ruff's `D417` (undocumented parameter) fires; `numpy` and `pep257` exclude it.
- `napoleon_preprocess_types` cannot cross-reference `list[str]`: PEP 585/604 generic syntax is unrepresentable as a docstring type, while the same annotation decomposes into linked `list` and `str`.
- Type duplication costs 13 to 30 percent more tokens; the choice between Google, NumPy and reST syntax costs almost nothing (79 vs 81 vs 76 tokens on a four-parameter example).

## The first-sentence rule

Combining PEP 257 [32], Google's API reference comment rules [19], Google's Python style guide [33] and pandas [30]: one line, ends with a period; does not repeat the name; no meta-language; no internal period (extractors truncate at the first one); pick one mood per package and keep it consistent (no fleet-wide mass rewrites for mood); for booleans, "True if ...; False otherwise" for state, or state what happens if true and if false for actions.

## References

1. Macke W, Doyle M. [Testing the Effect of Code Documentation on Large Language Model Code Understanding](https://arxiv.org/abs/2404.03114). arXiv:2404.03114; 2024.
2. Write the Docs. [Documentation principles](https://www.writethedocs.org/guide/writing/docs-principles/).
3. Chen J, et al. [When LLMs Meet API Documentation: Can Retrieval Augmentation Aid Code Generation Just as It Helps Developers?](https://arxiv.org/abs/2503.15231) arXiv:2503.15231; 2025.
4. Meng M, Steinhardt S, Schubert A. [How developers use API documentation: an observation study](https://dl.acm.org/doi/10.1145/3358931.3358937). Communication Design Quarterly 7(2); 2019.
5. Robillard MP, DeLine R. [A field study of API learning obstacles](https://link.springer.com/article/10.1007/s10664-010-9150-8). Empirical Software Engineering 16(6); 2011.
6. Vitale N, et al. [Can docstring reformulation with an LLM improve code generation?](https://aclanthology.org/2024.eacl-srw.24/) EACL SRW; 2024.
7. Yang G, et al. [Less is More: DocString Compression in Code Generation](https://arxiv.org/abs/2410.22793). arXiv:2410.22793; 2024, revised 2025.
9. Chroma Research. [Context Rot: Evaluating LLM Performance Degradation with Increasing Input Tokens](https://www.zenml.io/llmops-database/context-rot-evaluating-llm-performance-degradation-with-increasing-input-tokens). 2025.
10. Khan JY, et al. [Automatic Detection of Five API Documentation Smells](https://arxiv.org/abs/2102.08486). IEEE SANER; 2021.
11. Astral. [Ruff rules: pydocstyle (D) and pydoclint (DOC)](https://docs.astral.sh/ruff/rules/).
12. jsh9. [pydoclint](https://github.com/jsh9/pydoclint).
15. [DocPrism: Local Categorization and External Filtering to Identify Relevant Code-Documentation Inconsistencies](https://arxiv.org/html/2511.00215). arXiv:2511.00215; 2026.
18. Yang D, et al. [DocAgent: A Multi-Agent System for Automated Code Documentation Generation](https://arxiv.org/html/2504.08725v1). arXiv:2504.08725; 2025.
19. Google. [API reference code comments](https://developers.google.com/style/api-reference-comments). Google developer documentation style guide.
20. Eghbali A, et al. [Natural Language-Focused Software Engineering via Code-Documentation Equivalence](https://arxiv.org/html/2606.22247). arXiv:2606.22247; 2026.
30. pandas. [pandas docstring guide](https://pandas.pydata.org/docs/development/contributing_docstring.html).
32. van Rossum G, Goodger D. [PEP 257: Docstring Conventions](https://peps.python.org/pep-0257/).
33. Google. [Google Python Style Guide: Comments and Docstrings](https://google.github.io/styleguide/pyguide.html).
34. Procida D. [Diátaxis](https://diataxis.fr/).
38. Crall J. [xdoctest](https://xdoctest.readthedocs.io/en/latest/).
39. Python Software Foundation. [doctest](https://docs.python.org/3/library/doctest.html).
