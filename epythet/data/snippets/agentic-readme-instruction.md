Add the agentic aspects to this README. With `agentic_first` on, agents get their section before the humans get theirs; otherwise it closes the README.

Do not hand-write the section. Run `epythet ai-readme-check <project_dir> --write` so it lands between epythet's marker comments and a later run updates it in place. To change the wording, change the snippets, not the README: `epythet snippets init`, then edit `agentic-readme-section.md` and `agentic-readme-humor.md` in your snippets folder.

Then read the result as a stranger would. The humour is light and stays on the writer's side of the joke. No em-dashes, no "not X but Y", no closing paragraph that restates the section. Every link resolves. If the README already covers the same artifacts under a heading of its own, keep that heading only if it says something the generated section does not; otherwise remove it, so the two never disagree.
