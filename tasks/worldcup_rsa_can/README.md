# World Cup betting — South Africa vs Canada

One 2026 FIFA World Cup match as a standalone TrapStreet task. A model predicts the
outcome **blind** — it sees only the teams and kickoff, never the odds — and is
graded after the match.

- **Input:** `inputs/wc26_20260628_RSA_CAN/question.txt` — teams + kickoff, no odds.
- **Output:** stdout JSON `{"home":p,"draw":p,"away":p}` (probabilities summing to 1).
- **Grading:** `judge.py` → log-loss + Brier (calibration) and, once odds are filled,
  a flat-stake +EV ROI. `grader.py` aggregates this match.

Hiding the odds is deliberate: shown them, a model just inverts the line and the
score becomes meaningless. Fixtures are played after the models' training cutoff and
frozen pre-kickoff, so there's no leakage.

## Self-contained — everything this task needs is here

| File | Role |
|---|---|
| `judge.py` / `grader.py` | scoring (no external deps) |
| `oddsapi.py` | the-odds-api client + parsers + FIFA team codes |
| `snapshot.py` | near kickoff: `ODDS_API_KEY=... python3 snapshot.py` — fills this match's odds |
| `grade.py` | after full time: `ODDS_API_KEY=... python3 grade.py` — fills this match's result |
| `test_judge.py` | `pytest` — scoring math |

This task is **pending** until kickoff (`result: null`). Run `snapshot.py` near
kickoff and `grade.py` after; then re-run the eval to update the leaderboard.
Calibration works without a key; ROI needs it (free tier at the-odds-api.com).
