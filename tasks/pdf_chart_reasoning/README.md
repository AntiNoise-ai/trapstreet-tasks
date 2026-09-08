# pdf_chart_reasoning — the public half

The public half of a split task: the twenty-three questions and the single
document they are about. The answers, the judge, the grader and the machinery
that authored them are held privately, so **`tp run` will not score against this
directory** — nothing here can tell you whether an answer is right.

Two files serve the same cases to two different readers, and both are *rendered*
from the private side. Editing either here would be overwritten and would not
move any score.

- `traptask.yaml` — the case list. The platform reads it, then builds each
  case's input from `inputs/`: the question inlined, the document handed over as
  a pinned URL. Grading happens on a worker that holds the answers.
- `traplite-question.yaml` — the same questions as one self-contained string
  each, for a client that fetches this file by URL and has no way to be handed a
  file at all.

Case descriptions are the questions themselves. They deliberately do not name
what each case tests: three of the twenty-three are answerable only by
declining, they are worded exactly like the twenty that are not, and saying so
here would give that away.

## Do not move or rename anything here

`inputs/case_01/document.pdf` is **load-bearing**. Twenty-three live questions
name it by a raw URL pinned to commit `2978c07`, because the benchmark format
that serves them carries no inputs of its own and 5.7 MB cannot be inlined into
a question string. That commit is chosen so the document is reachable at it and
the answers are not.

A commit-pinned raw URL keeps resolving after the file is deleted at HEAD, so
removing this directory would not break those questions today. Keeping it means
the dependency is visible to whoever reads the repository next, rather than
resting on a blob nothing at HEAD explains.

## What the document is

The June 2026 Federal Reserve *Summary of Economic Projections*, with its
thirteen figure pages rasterised at 200 DPI. In the release as published the
charts are vector paths, and a parser can measure every bar and dot exactly.
Rasterising deletes the paths, so a value that appears in no table survives only
as pixels — which is the whole point of asking about it. Pages 1–2 and 16–17
keep their text layer exactly as published.

Source and licence: see `ATTRIBUTION.md`.

## The questions

`inputs/case_*/question.txt` are the same twenty-three questions in the layout a
local runner expects. `traplite-question.yaml` carries them again, each prefixed
with the document's URL, because the format that serves it has no way to hand an
agent a file.
