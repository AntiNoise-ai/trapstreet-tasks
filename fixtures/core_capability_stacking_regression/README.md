# Replay fixture — core_capability_stacking_regression

One real run's model outputs, frozen. Edit the task's `judge.py` or `grader.py`,
run `replay.py`, read the numbers — about three seconds, no models called, no
API key.

```bash
python3 replay.py                  # headline numbers
python3 replay.py --json           # the full grader output
```

This exists so that scoring can be developed at the speed of an edit. Iterating
on a metric by launching a fresh run costs a dollar and several minutes per
attempt, which is enough friction to change what gets tried.

## What is here

```
outputs/claude-haiku-4-5/
  case_01.txt … case_108.txt   the solution's stdout, verbatim
  exit_codes.json              per-case exit code, so solution_error stays reachable
```

`replay.py` feeds each output to `judge.py` through the same
`TRAPTASK_MANIFEST` contract trap-cli uses, then hands the collected metrics to
`grader.py`. Nothing is reimplemented — a change to either file shows up here
immediately, and anything that works here works on the platform.

## Provenance

| | |
|---|---|
| model | `claude-haiku-4-5-20251001`, no thinking (the model has no adaptive mode) |
| task | `trapstreet-tasks` @ `6c8c7b4`, `tasks/core_capability_stacking_regression` |
| run | 108 cases, all levels including L4, one pass, $1.07 |
| result | `RESULTS.md` run 3 — score 0.867, arm_gap 0.1636, primary p = 0.0293 |

Replaying against an unmodified `judge.py` reproduces those numbers exactly. If
it does not, the task has moved and this fixture is stale — it is pinned to the
commit above, not to `main`.

## What it cannot tell you

The outputs are fixed, so this measures **how a scoring change re-reads one
model's behaviour**, not how a model behaves under a changed task. Anything that
alters the prompts — `catalog.json`, `scenarios.json`, `build_cases.py` — makes
these outputs answers to questions that were never asked. Those changes need a
fresh run.
