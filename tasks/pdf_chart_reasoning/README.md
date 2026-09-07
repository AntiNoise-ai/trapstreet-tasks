# pdf_chart_reasoning — input only

This is no longer a task. It is one document and the twenty-three questions
asked about it, kept public because a benchmark's inputs are public by
definition. The answers, the judge, the grader and the machinery that authored
them are held privately.

## Do not move or rename anything here

`inputs/case_01/document.pdf` is **load-bearing**. Twenty-three live questions
name it by a raw URL pinned to commit `3610f4b`, because the benchmark format
that serves them carries no inputs of its own and 5.7 MB cannot be inlined into
a question string.

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

`inputs/case_*/question.txt` are the questions as asked. They are rendered from
the private authoring side, not edited here — a change made in this directory
would be overwritten and would not move any published score.
