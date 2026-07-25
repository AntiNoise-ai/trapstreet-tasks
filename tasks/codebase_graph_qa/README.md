# codebase_graph_qa

Given a small multi-file repository (Python source, a SQL schema, YAML
config, or Markdown docs) and a natural-language question about its
internal structure, the solution must answer with the exact set of
identifiers (functions, files, or tables) that satisfy the question.

## Why this task

Tools like AST-based "codebase-to-knowledge-graph" skills (e.g. the
`/graphify`-style skill for coding agents) claim to answer structural
questions about a codebase -- "what does this function transitively call",
"what does this table depend on", "is this doc still accurate" -- by
building an explicit, queryable graph instead of relying on vector search
or the model's own memory. This task gives a concrete, checkable version of
that claim: five categories of structural query, each requiring the
solution to actually trace relationships across multiple files rather than
pattern-match on a single snippet.

Solutions being compared can be a bare coding agent, an agent equipped with
a graph/structure-aware skill, or any other tool that can read a directory
and answer a question about it -- the task doesn't require any particular
approach, only a correct answer to a structural question with an
unambiguous, mechanically-checkable ground truth.

All 15 case repositories are **original, hand-authored synthetic code** --
none of it is copied or adapted from any real project. This was a
deliberate choice per `ground-truth-sourcing.md`: structural-relationship
answers can be computed exactly by construction (we wrote the code, so we
know its call graph / import graph / FK graph / doc-vs-code drift
precisely), which eliminates both the leakage risk of real, possibly
memorized repositories and any licensing exposure from reusing someone
else's code. Every case also includes at least one deliberate distractor
(a similarly-named function, an unrelated table, a same-named-but-different
config key, a same-domain-but-wrong doc match) so that a solution which
merely lists everything plausible, rather than actually tracing the
relationship, is penalized -- see Scoring below.

Categories (3 cases each):
- **call_chain** -- transitive function call graph, including import
  aliasing, decorators, and inherited/overridden methods.
- **import_chain** -- transitive module dependency graph, including
  function-local imports and `TYPE_CHECKING`-only imports that never
  execute at runtime.
- **schema_fk** -- transitive foreign-key dependency graph in a SQL schema,
  including self-referencing FKs, many-to-many join tables, and both
  inline and `ALTER TABLE` FK syntax.
- **config_trace** -- which files read a given config key, whether via
  direct `os.environ` access, an indirection layer (a shared settings
  object), or a YAML config loader.
- **doc_code_xref** -- whether a function documented in a Markdown doc
  still exists under that name, was renamed (match by documented
  behavior), or was actually removed.

## Input / output contract

Each `inputs/<case_id>/` contains:
- `repo/` -- the actual multi-file repository the question is about.
- `question.txt` -- the natural-language question, plus the required
  output format.

The solution must print, to stdout, ONLY a JSON object of the form:
```json
{"answer": ["<identifier 1>", "<identifier 2>", ...]}
```
The exact identifier format (e.g. `<path>:<function_name>` vs. a bare file
path vs. a bare table name) is restated in each case's question, with a
worked example. All paths are relative to `repo/`.

## Scoring

`judge.py`'s `score_case()` parses the solution's `answer` list, normalizes
each identifier (trim whitespace, normalize path separators, strip a
leading `repo/` prefix if the solution included one, case-fold), and
computes set-based **F1** against the expected identifier set: precision
(how much of what you listed was correct) and recall (how much of the
correct set you found), combined as the harmonic mean.

F1 was chosen over a simple hit/miss specifically because it is
self-regulating against shotgunning: a solution that lists every
plausible-looking identifier in the repo will tank its own precision, so
there's no need for a separate `MAX_FINDINGS_SCORED` cap the way a
single-best-guess bug-finding task needs one (see
`references/scoring-design.md`, Anti-shotgun). Every case includes at
least one distractor specifically to test this -- a correct-but-imprecise
"list everything" answer scores meaningfully lower than a precise one (see
`tests/test_judge.py::test_shotgun_answer_is_self_punishing`).

Malformed output degrades gracefully rather than crashing the judge:
non-JSON stdout, JSON missing the `answer` key, `answer` not being a list,
non-string list entries, and deeply nested/malformed JSON are all handled
and scored `0.0` with a `reason` field, never an unhandled exception (see
`tests/test_judge.py` for the specific cases covered).

**Known limitation:** normalization case-folds every identifier before
comparing. This means an answer that gets the file/function name right but
in different case still counts as correct -- a deliberate leniency choice,
not a bug, since case sensitivity isn't what any of these questions are
actually testing.

## Sources & licensing

No external/real-world material is used anywhere in this task. Every file
in every case's `repo/` (and every `docs/*.md`, `schema.sql`, `*.yaml`) was
authored from scratch specifically for this task. No sources/licensing
table is needed.

## Run

```bash
python3 build_cases.py                 # (re)generate inputs/ + expected/ from gold.cases.json
python3 -m pytest tests/ -v            # unit tests
```
