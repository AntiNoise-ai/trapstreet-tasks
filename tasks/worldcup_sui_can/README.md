# World Cup betting — Switzerland vs Canada

One match from the 2026 FIFA World Cup, as a standalone TrapStreet task. A model
predicts the outcome **blind** (it never sees the odds) and is graded after the
match is played.

- Input: `inputs/wc26_20260624_SUI_CAN/question.txt` — teams + kickoff, no odds.
- Output: stdout JSON `{"home":p,"draw":p,"away":p}`.
- Graded by `judge.py`: log-loss + Brier (calibration) and, once odds are
  back-filled, a flat-stake +EV ROI. `grader.py` aggregates the single match.

This task is **pending** until kickoff (`result: null`). Odds/results are filled
by the shared tooling in `worldcup_tooling/` (`snapshot.py` near kickoff,
`grade.py` after full time) once `ODDS_API_KEY` is set. See that directory's
README for the live loop. Blind prediction + post-cutoff fixtures keep it
leakage-free.
