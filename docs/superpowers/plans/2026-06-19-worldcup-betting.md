# World Cup Betting (live ROI eval) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tasks/worldcup_betting/` — the first *live* TrapStreet task: agents predict not-yet-played 2026 FIFA World Cup fixtures **blind** (they never see the odds), and are graded after kickoff on calibration (log-loss + Brier, headline) plus ROI-vs-bookmaker (value-betting diagnostic).

**Architecture:** Each case is one fixture. A `snapshot.py` step (run close to kickoff) pulls upcoming fixtures + decimal H/D/A odds from the-odds-api, **freezes** them into `inputs/<id>/question.txt` (matchup + kickoff only — **no odds**) and a skeleton `expected/<id>/answer.json` (odds kept here, for settlement only), and appends to `gold.cases.json` + `traptask.yaml`. Agents output a probability distribution over {home, draw, away} from their own judgment. After matches finish, `grade.py` pulls results and fills the actual outcome into each `expected/<id>/answer.json`. The `judge.py` then scores each fixture offline (no network): log-loss + Brier (calibration) and a fixed flat-stake +EV betting rule → realized P&L (value betting against the held-out line). `grader.py` ranks by mean log-loss and reports ROI = Σprofit / Σstaked. Because odds + results are frozen into files, grading and replay are fully offline and reproducible — the only network touch is at snapshot/grade time, mirroring how `cuad/build_cases.py` downloads upstream data.

**Why the model is graded blind:** if the input showed the odds, every frontier model would just invert them (`p ≈ 1/odds`, renormalized) and report the bookmaker's own de-vigged line. Books are sharply calibrated, so all models would land at near-identical log-loss — the metric would measure arithmetic, not prediction, and reward regurgitation over judgment. Hiding the odds makes log-loss a real independent-calibration test, and makes ROI genuine value-betting: does the model's blind estimate find +EV spots the held-out line missed? (This is how pro bettors actually work — build the estimate first, *then* compare to the line.)

**Tech Stack:** Python 3 (stdlib only for judge/grader; `urllib` for the API client — no third-party deps), pytest, the-odds-api v4 (`soccer_fifa_world_cup` sport key, `h2h` market, decimal odds), YAML for `traptask.yaml` (hand-written, matching existing tasks).

---

## Leakage rationale (why this is valid)

Frontier LLMs have a ~Jan 2026 training cutoff. The 2026 World Cup is being **played right now** (group stage in progress, June–July 2026), so every fixture we snapshot post-dates every model's cutoff — the model cannot have memorized the result. This is the same guard the CUAD task documents ("test split, never train"). The forward-live framing makes leakage *structurally impossible*: we snapshot and freeze inputs **before kickoff**, grade **after**.

## File structure

```
tasks/worldcup_betting/
├── README.md                       # task explanation, live mechanism, metric, leakage, attribution
├── traptask.yaml                   # dirs + cases + judge/grader cmds (appended to by snapshot.py)
├── gold.cases.json                 # manifest of all fixtures (appended to by snapshot.py)
├── oddsapi.py                      # pure parsing fns + thin urllib client for the-odds-api
├── snapshot.py                     # CLI: fetch upcoming fixtures+odds → freeze inputs/ + expected/ skeletons
├── grade.py                        # CLI: fetch finished-match results → fill expected/ outcomes
├── judge.py                        # per-case: parse probs, log-loss + flat-stake +EV P&L → metrics JSON
├── grader.py                       # run-level: ROI, mean log-loss, pass threshold
├── test_oddsapi.py                 # parsing tests against captured fixture JSON
├── test_judge.py                   # log-loss + staking math tests
├── test_grader.py                  # ROI aggregation tests
├── fixtures/                       # captured API JSON for tests (committed)
│   ├── odds_sample.json
│   └── scores_sample.json
├── inputs/<case-id>/question.txt   # frozen match + odds + instruction (committed once snapshotted)
└── expected/<case-id>/answer.json  # odds + (after grading) actual result + matchers
```

**Case id convention:** `wc26_<commence-date>_<HOME>_<AWAY>`, e.g. `wc26_20260620_BRA_MAR`. Slugify team names to 3–4 uppercase letters; if collision, append the the-odds-api event `id` short hash. Each case is self-contained once frozen.

> **Note on the odds:** they live ONLY in `expected/<id>/answer.json`, never in `inputs/<id>/question.txt`. The model predicts blind; the judge uses the frozen odds to settle bets.

**Per-case `expected/<id>/answer.json` shape:**
```json
{
  "id": "wc26_20260620_BRA_MAR",
  "type": "match_prediction",
  "home_team": "Brazil",
  "away_team": "Morocco",
  "commence_time": "2026-06-20T19:00:00Z",
  "odds": {"home": 2.10, "draw": 3.40, "away": 3.60},
  "graded": false,
  "result": null,
  "matchers": [{"kind": "roi_logloss"}],
  "_source": "the-odds-api soccer_fifa_world_cup h2h (decimal)"
}
```
After `grade.py` runs: `"graded": true, "result": "home"` (one of `home|draw|away`).

**Agent I/O contract** (matches every other task):
- Input: `inputs/<id>/question.txt` (the only file the agent sees) — matchup + kickoff time, **no odds**.
- Output: stdout, either plain JSON `{"home":0.45,"draw":0.28,"away":0.27}` or wrapped `{"answer":"{...}"}`. Probabilities should sum to ~1; the judge renormalizes if they don't and fails the case if they can't be parsed.

---

### Task 1: Scaffold directory, README, and traptask.yaml skeleton

**Files:**
- Create: `tasks/worldcup_betting/README.md`
- Create: `tasks/worldcup_betting/traptask.yaml`
- Create: `tasks/worldcup_betting/gold.cases.json`
- Create: `tasks/worldcup_betting/fixtures/.gitkeep`

- [ ] **Step 1: Create the directory and empty manifest**

Run:
```bash
mkdir -p tasks/worldcup_betting/fixtures tasks/worldcup_betting/inputs tasks/worldcup_betting/expected
printf '[]\n' > tasks/worldcup_betting/gold.cases.json
touch tasks/worldcup_betting/fixtures/.gitkeep
```
Expected: directory tree exists, `gold.cases.json` contains `[]`.

- [ ] **Step 2: Write `traptask.yaml` skeleton**

Create `tasks/worldcup_betting/traptask.yaml`:
```yaml
dirs:
  inputs: inputs/
  expected: expected/

# `cases:` is appended to by snapshot.py as fixtures are frozen.
cases: []

judge:
  cmd: python3 judge.py

grader:
  cmd: python3 grader.py
```
Expected: file mirrors the `cuad/traptask.yaml` structure (dirs / cases / judge / grader).

- [ ] **Step 3: Write `README.md`**

Create `tasks/worldcup_betting/README.md` with these sections (prose, following the `cuad`/`shoeprint_reader` voice — explain task, input, output, grading, the live mechanism, leakage rationale, and attribution):

```markdown
# World Cup Betting — live ROI eval

## What this task tests

**Can an AI predict football it has never seen — well enough to beat the bookmaker?**

Each case is one 2026 FIFA World Cup fixture. The model gets *only* the matchup and
kickoff time — **never the odds** — and must output its own probability for each
outcome. After the match is played, we grade two ways:

- **Calibration: log-loss + Brier** (headline) — how good the model's *independent*
  probabilities were. Because the model never saw the odds, it can't game this by
  parroting the bookmaker line; it has to actually know football.
- **ROI vs. the bookmaker** (value-betting diagnostic) — a fixed flat-stake rule
  bets $1 on every outcome the model's blind estimate rates +EV against the frozen
  odds (`p × odds > 1`). ROI = profit ÷ total staked. Positive ROI means the model
  found value the held-out line missed; most can't.

> Models are **ranked by mean log-loss, then ROI** — on a sharp market and a small
> sample, almost everyone runs slightly negative ROI, so ROI separates the field
> only at scale (~50+ graded matches). Treat early ROI as directional.

This is TrapStreet's **first live task**: cases are snapshotted *near kickoff* and
graded *after*, so the leaderboard grows as the tournament plays out.

## Why the 2026 World Cup (leakage)

A betting eval is only valid if the model doesn't already know the result. Every
frontier model has a training cutoff (~Jan 2026), so any past tournament is
memorized. The 2026 World Cup is being played *now*, after every model's cutoff —
and because we freeze inputs before kickoff, leakage is structurally impossible.

## Input

`inputs/<case-id>/question.txt` — matchup (home vs away) + kickoff time + an
instruction to output `{"home":p,"draw":p,"away":p}`. **The odds are deliberately
withheld** — the model must form an independent estimate.

## Expected output

stdout: a JSON object with `home`/`draw`/`away` probabilities (or `{"answer":"..."}`
wrapping the same). Probabilities are renormalized if they don't sum to 1; an
unparseable answer fails the case.

## How answers are graded

`judge.py` (offline, no network) reads the frozen odds + actual result and emits
per-case `log_loss`, `brier`, `staked`, `returned`, `profit`. `grader.py` ranks by
`mean_log_loss` (and reports `mean_brier`), and reports `roi = Σprofit / Σstaked`
as a value-betting diagnostic. The `passed` boolean (`roi > 0`) is a coarse
"did it beat the line at all" flag, not the primary signal — the ranking is.

## The live mechanism

- `snapshot.py` — run before each match day; pulls upcoming fixtures + odds from
  the-odds-api and freezes them into `inputs/` + `expected/` (with `graded:false`).
- `grade.py` — run after matches finish; fills the actual result into `expected/`.
- Both need `ODDS_API_KEY` in the environment (free tier at the-odds-api.com).
  Grading/replay needs no network — odds and results are frozen into files.

## Data source & attribution

Odds and results from [the-odds-api.com](https://the-odds-api.com)
(`soccer_fifa_world_cup`, `h2h` market, decimal). Odds are a **snapshot taken near
kickoff** (an approximation of the closing line), stored verbatim in each case's
`expected/answer.json` for reproducible settlement — never shown to the model.
```
Expected: README renders and explains the task end-to-end.

- [ ] **Step 4: Commit**

```bash
git add tasks/worldcup_betting/README.md tasks/worldcup_betting/traptask.yaml tasks/worldcup_betting/gold.cases.json tasks/worldcup_betting/fixtures/.gitkeep
git commit -m "feat(worldcup_betting): scaffold task dir, README, traptask skeleton"
```

---

### Task 2: judge.py — probability parsing + log-loss + flat-stake +EV P&L

**Files:**
- Create: `tasks/worldcup_betting/judge.py`
- Test: `tasks/worldcup_betting/test_judge.py`

The judge has three pure helpers (`parse_probs`, `log_loss`, `settle_bets`) plus a `main()` that follows the same `TRAPTASK_PAYLOAD` contract as `cuad/judge.py`.

- [ ] **Step 1: Write the failing tests**

Create `tasks/worldcup_betting/test_judge.py`:
```python
import math
import pytest
from judge import parse_probs, log_loss, brier_score, settle_bets


def test_parse_probs_plain_json():
    assert parse_probs('{"home":0.5,"draw":0.3,"away":0.2}') == pytest.approx(
        {"home": 0.5, "draw": 0.3, "away": 0.2}, rel=1e-9
    )


def test_parse_probs_wrapped_answer():
    out = parse_probs('{"answer": "{\\"home\\":0.5,\\"draw\\":0.3,\\"away\\":0.2}"}')
    assert out == pytest.approx({"home": 0.5, "draw": 0.3, "away": 0.2}, rel=1e-9)


def test_parse_probs_renormalizes():
    out = parse_probs('{"home":2,"draw":1,"away":1}')
    assert out == pytest.approx({"home": 0.5, "draw": 0.25, "away": 0.25}, rel=1e-9)


def test_parse_probs_rejects_garbage():
    assert parse_probs("not json at all") is None
    assert parse_probs('{"home":0.5}') is None          # missing keys
    assert parse_probs('{"home":-1,"draw":1,"away":1}') is None  # negative
    assert parse_probs('{"home":0,"draw":0,"away":0}') is None   # zero sum


def test_log_loss_perfect_vs_wrong():
    p = {"home": 0.9, "draw": 0.05, "away": 0.05}
    assert log_loss(p, "home") == pytest.approx(-math.log(0.9), rel=1e-9)
    assert log_loss(p, "away") == pytest.approx(-math.log(0.05), rel=1e-9)


def test_log_loss_clamps_zero():
    # a model that assigned ~0 to the actual outcome shouldn't yield inf
    p = {"home": 1.0, "draw": 0.0, "away": 0.0}
    assert log_loss(p, "away") == pytest.approx(-math.log(1e-15), rel=1e-6)


def test_brier_score_multiclass():
    # perfect: brier 0
    assert brier_score({"home": 1.0, "draw": 0.0, "away": 0.0}, "home") == pytest.approx(0.0)
    # worst confident-wrong: (1-0)^2 + 0 + (0-1)^2 = 2.0
    assert brier_score({"home": 1.0, "draw": 0.0, "away": 0.0}, "away") == pytest.approx(2.0)
    # 0.5/0.3/0.2, actual home: (.5-1)^2+.3^2+.2^2 = .25+.09+.04 = .38
    assert brier_score({"home": 0.5, "draw": 0.3, "away": 0.2}, "home") == pytest.approx(0.38)


def test_settle_bets_places_only_positive_ev():
    # odds 2.1 / 3.4 / 3.6; model 0.55/0.25/0.20
    # EV home = .55*2.1=1.155>1 -> bet; draw .25*3.4=0.85 -> no; away .20*3.6=0.72 -> no
    odds = {"home": 2.1, "draw": 3.4, "away": 3.6}
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    staked, returned = settle_bets(probs, odds, result="home")
    assert staked == pytest.approx(1.0)        # one +EV bet
    assert returned == pytest.approx(2.1)      # it won


def test_settle_bets_loses_when_wrong():
    odds = {"home": 2.1, "draw": 3.4, "away": 3.6}
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    staked, returned = settle_bets(probs, odds, result="away")
    assert staked == pytest.approx(1.0)
    assert returned == pytest.approx(0.0)


def test_settle_bets_abstains_when_no_edge():
    odds = {"home": 2.0, "draw": 3.0, "away": 4.0}
    probs = {"home": 0.40, "draw": 0.30, "away": 0.20}  # all p*odds <= ~1
    staked, returned = settle_bets(probs, odds, result="home")
    assert staked == pytest.approx(0.0)
    assert returned == pytest.approx(0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_judge.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'judge'` (or import errors for the helpers).

- [ ] **Step 3: Write `judge.py`**

Create `tasks/worldcup_betting/judge.py`:
```python
"""Per-case judge for the worldcup_betting task — calibration + realized P&L.

Reads the agent's stdout (a probability distribution over {home, draw, away}),
the frozen odds and the actual result from expected/<id>/answer.json, and emits a
metrics JSON on stdout (trap stores it as CaseResult.metrics).

Numbers per case:
  - log_loss : -ln(p_actual), the calibration signal (lower is better).
  - brier    : Σ(p_o - y_o)^2, bounded calibration signal, robust on small samples.
  - profit   : realized P&L from a fixed flat-stake +EV rule — bet $1 on every
               outcome where p*odds > 1; a winning bet returns `odds`, else 0.
               profit = returned - staked. This is the "beat the bookmaker" signal.

`score` is a per-case convenience flag (1.0 if the fixture turned a profit, 0.5 if
the model abstained, 0.0 if it lost). The real verdict is the run-level ROI in
grader.py. Ungraded fixtures (match not yet played) emit score=null.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

OUTCOMES = ("home", "draw", "away")
_EPS = 1e-15


def parse_probs(stdout: str) -> dict | None:
    """Parse stdout into {home,draw,away} probabilities, renormalized to sum 1.

    Accepts a bare JSON object or `{"answer": "<json string>"}`. Returns None if
    the answer can't be parsed, is missing an outcome, has a negative value, or
    sums to <= 0.
    """
    s = (stdout or "").strip()
    if not s:
        return None
    obj: Any
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and "answer" in obj and not all(k in obj for k in OUTCOMES):
        inner = obj["answer"]
        if isinstance(inner, str):
            try:
                obj = json.loads(inner)
            except json.JSONDecodeError:
                return None
    if not isinstance(obj, dict):
        return None
    try:
        vals = {k: float(obj[k]) for k in OUTCOMES}
    except (KeyError, TypeError, ValueError):
        return None
    if any(v < 0 for v in vals.values()):
        return None
    total = sum(vals.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in vals.items()}


def log_loss(probs: dict, result: str) -> float:
    """-ln(p_actual), with p clamped to [_EPS, 1] to avoid infinities."""
    p = max(_EPS, min(1.0, probs[result]))
    return -math.log(p)


def brier_score(probs: dict, result: str) -> float:
    """Multiclass Brier: Σ_o (p_o - y_o)^2, bounded [0, 2]. More robust than
    log-loss on tiny samples (a confident miss can't blow it up to infinity)."""
    return sum((probs[o] - (1.0 if o == result else 0.0)) ** 2 for o in OUTCOMES)


def settle_bets(probs: dict, odds: dict, result: str) -> tuple[float, float]:
    """Flat $1 stake on every +EV outcome; return (staked, returned).

    A bet on outcome o is placed when probs[o] * odds[o] > 1. A winning bet (o ==
    result) returns odds[o]; a losing bet returns 0.
    """
    staked = 0.0
    returned = 0.0
    for o in OUTCOMES:
        if probs[o] * odds[o] > 1.0:
            staked += 1.0
            if o == result:
                returned += odds[o]
    return staked, returned


def _case_score(staked: float, returned: float) -> float:
    if staked == 0.0:
        return 0.5  # abstained — neutral
    return 1.0 if returned > staked else 0.0


def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])
    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    base = {
        "id": expected.get("id"),
        "type": expected.get("type"),
        "home_team": expected.get("home_team"),
        "away_team": expected.get("away_team"),
    }

    # Not yet played — nothing to grade.
    if not expected.get("graded") or expected.get("result") is None:
        print(json.dumps({"score": None, "reason": "match not yet graded", **base}))
        return

    if exit_code != 0:
        print(json.dumps({"score": 0.0, "reason": f"solution exited {exit_code}", **base}))
        return

    probs = parse_probs(stdout)
    if probs is None:
        print(json.dumps({"score": 0.0, "reason": "could not parse probabilities",
                          "agent_answer": (stdout or "")[:300], **base}))
        return

    odds = expected["odds"]
    result = expected["result"]
    ll = log_loss(probs, result)
    brier = brier_score(probs, result)
    staked, returned = settle_bets(probs, odds, result)
    profit = returned - staked

    print(json.dumps({
        "score": _case_score(staked, returned),
        "log_loss": round(ll, 6),
        "brier": round(brier, 6),
        "staked": staked,
        "returned": round(returned, 4),
        "profit": round(profit, 4),
        "probs": probs,
        "odds": odds,
        "result": result,
        **base,
    }))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_judge.py -q`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add tasks/worldcup_betting/judge.py tasks/worldcup_betting/test_judge.py
git commit -m "feat(worldcup_betting): judge with log-loss + flat-stake +EV P&L"
```

---

### Task 3: grader.py — ROI aggregation + calibration + pass threshold

**Files:**
- Create: `tasks/worldcup_betting/grader.py`
- Test: `tasks/worldcup_betting/test_grader.py`

The grader reads the case list from `TRAPTASK_PAYLOAD` (same as `cuad/grader.py`) and aggregates `metrics.profit` / `metrics.staked` / `metrics.log_loss`. Pass if `roi > 0`.

- [ ] **Step 1: Write the failing tests**

Create `tasks/worldcup_betting/test_grader.py`:
```python
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def run_grader(cases):
    env = {"TRAPTASK_PAYLOAD": json.dumps(cases), "PATH": "/usr/bin:/bin"}
    out = subprocess.run(
        [sys.executable, "grader.py"], cwd=HERE, env=env,
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def _case(profit, staked, log_loss, score, brier=0.4):
    return {"metrics": {"profit": profit, "staked": staked, "log_loss": log_loss,
                        "brier": brier, "score": score}, "duration": 0.1}


def test_roi_positive_passes():
    cases = [_case(1.1, 1.0, 0.5, 1.0), _case(-1.0, 1.0, 0.9, 0.0),
             _case(2.6, 2.0, 0.4, 1.0)]
    # staked total = 4.0, profit total = 2.7 -> roi = 0.675
    res = run_grader(cases)
    assert res["roi"] == 0.675
    assert res["total_staked"] == 4.0
    assert res["passed"] is True


def test_roi_negative_fails():
    cases = [_case(-1.0, 1.0, 1.2, 0.0), _case(-1.0, 1.0, 1.5, 0.0)]
    res = run_grader(cases)
    assert res["roi"] == -1.0
    assert res["passed"] is False


def test_mean_log_loss_and_brier_reported():
    cases = [_case(0.0, 0.0, 0.4, 0.5, brier=0.3), _case(0.0, 0.0, 0.6, 0.5, brier=0.5)]
    res = run_grader(cases)
    assert res["mean_log_loss"] == 0.5
    assert res["mean_brier"] == 0.4
    # all abstained -> no staked -> roi defined as 0.0, not a crash
    assert res["total_staked"] == 0.0
    assert res["roi"] == 0.0


def test_ungraded_cases_skipped():
    cases = [_case(1.1, 1.0, 0.5, 1.0),
             {"metrics": {"score": None, "reason": "match not yet graded"}, "duration": 0.0}]
    res = run_grader(cases)
    assert res["n_graded"] == 1
    assert res["n_pending"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_grader.py -q`
Expected: FAIL — `grader.py` does not exist / `FileNotFoundError`.

- [ ] **Step 3: Write `grader.py`**

Create `tasks/worldcup_betting/grader.py`:
```python
"""Run-level grader for the worldcup_betting task.

Aggregates per-case judge metrics into the leaderboard verdict. Models are RANKED
by mean_log_loss (lower is better) — that's the primary signal, because the model
predicted blind and calibration converges faster than ROI on small samples.

  - mean_log_loss  : ranking key — average calibration loss (lower better).
  - mean_brier     : bounded calibration loss, robust on tiny samples.
  - roi            : Σprofit / Σstaked — value-betting diagnostic. On a sharp
                     market + small sample most models run slightly negative;
                     ROI only separates the field at scale (~50+ matches).
  - passed         : coarse roi>0 flag (beat the line at all), NOT the ranking.
  - n_graded       : fixtures already played + judged.
  - n_pending      : fixtures snapshotted but not yet played (score is null).

Cases with score==null are pending (match not played) and are excluded from
aggregates — that's how a live, growing leaderboard works.
"""
from __future__ import annotations

import json
import os


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    graded = [c for c in cases
              if c.get("metrics") and c["metrics"].get("score") is not None]
    pending = [c for c in cases
               if not c.get("metrics") or c["metrics"].get("score") is None]

    total_staked = sum(c["metrics"].get("staked", 0.0) or 0.0 for c in graded)
    total_profit = sum(c["metrics"].get("profit", 0.0) or 0.0 for c in graded)
    roi = (total_profit / total_staked) if total_staked > 0 else 0.0

    log_losses = [c["metrics"]["log_loss"] for c in graded
                  if c["metrics"].get("log_loss") is not None]
    mean_log_loss = (sum(log_losses) / len(log_losses)) if log_losses else None

    briers = [c["metrics"]["brier"] for c in graded
              if c["metrics"].get("brier") is not None]
    mean_brier = (sum(briers) / len(briers)) if briers else None

    n_bets_won = sum(1 for c in graded if (c["metrics"].get("profit", 0.0) or 0.0) > 0)
    n_bets_placed = sum(1 for c in graded if (c["metrics"].get("staked", 0.0) or 0.0) > 0)

    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    latency_ms_total = round(sum(durations) * 1000, 1) if durations else 0.0

    passed = bool(graded) and roi > 0.0

    print(json.dumps({
        "passed": passed,
        "rank_key": round(mean_log_loss, 6) if mean_log_loss is not None else None,
        "mean_log_loss": round(mean_log_loss, 6) if mean_log_loss is not None else None,
        "mean_brier": round(mean_brier, 6) if mean_brier is not None else None,
        "roi": round(roi, 6),
        "total_staked": round(total_staked, 4),
        "total_profit": round(total_profit, 4),
        "n_graded": len(graded),
        "n_pending": len(pending),
        "n_bets_placed": n_bets_placed,
        "n_bets_won": n_bets_won,
        "latency_ms_total": latency_ms_total,
    }))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_grader.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tasks/worldcup_betting/grader.py tasks/worldcup_betting/test_grader.py
git commit -m "feat(worldcup_betting): grader with ROI + mean log-loss + pending split"
```

---

### Task 4: oddsapi.py — pure parsing of the-odds-api responses

**Files:**
- Create: `tasks/worldcup_betting/oddsapi.py`
- Create: `tasks/worldcup_betting/fixtures/odds_sample.json`
- Create: `tasks/worldcup_betting/fixtures/scores_sample.json`
- Test: `tasks/worldcup_betting/test_oddsapi.py`

Keep the network call thin and the parsing pure, so parsing is unit-tested against captured JSON without hitting the API. Fixtures below are minimal but real-shaped (the-odds-api v4 `h2h` + `scores`).

- [ ] **Step 1: Write the fixture JSON**

Create `tasks/worldcup_betting/fixtures/odds_sample.json`:
```json
[
  {
    "id": "abc123",
    "sport_key": "soccer_fifa_world_cup",
    "commence_time": "2026-06-20T19:00:00Z",
    "home_team": "Brazil",
    "away_team": "Morocco",
    "bookmakers": [
      {
        "key": "pinnacle",
        "markets": [
          {
            "key": "h2h",
            "outcomes": [
              {"name": "Brazil", "price": 2.10},
              {"name": "Morocco", "price": 3.60},
              {"name": "Draw", "price": 3.40}
            ]
          }
        ]
      }
    ]
  },
  {
    "id": "def456",
    "sport_key": "soccer_fifa_world_cup",
    "commence_time": "2026-06-20T22:00:00Z",
    "home_team": "Spain",
    "away_team": "Japan",
    "bookmakers": []
  }
]
```

Create `tasks/worldcup_betting/fixtures/scores_sample.json`:
```json
[
  {
    "id": "abc123",
    "completed": true,
    "home_team": "Brazil",
    "away_team": "Morocco",
    "scores": [
      {"name": "Brazil", "score": "2"},
      {"name": "Morocco", "score": "1"}
    ]
  },
  {
    "id": "ghi789",
    "completed": true,
    "home_team": "France",
    "away_team": "Canada",
    "scores": [
      {"name": "France", "score": "1"},
      {"name": "Canada", "score": "1"}
    ]
  },
  {
    "id": "jkl000",
    "completed": false,
    "home_team": "Spain",
    "away_team": "Japan",
    "scores": null
  }
]
```

- [ ] **Step 2: Write the failing tests**

Create `tasks/worldcup_betting/test_oddsapi.py`:
```python
import json
from pathlib import Path
import pytest
from oddsapi import parse_odds_event, parse_scores_event, slugify_case_id

HERE = Path(__file__).parent
ODDS = json.loads((HERE / "fixtures" / "odds_sample.json").read_text())
SCORES = json.loads((HERE / "fixtures" / "scores_sample.json").read_text())


def test_parse_odds_event_extracts_decimal_hda():
    ev = parse_odds_event(ODDS[0])
    assert ev["home_team"] == "Brazil"
    assert ev["away_team"] == "Morocco"
    assert ev["odds"] == {"home": 2.10, "draw": 3.40, "away": 3.60}
    assert ev["commence_time"] == "2026-06-20T19:00:00Z"


def test_parse_odds_event_no_bookmakers_returns_none():
    assert parse_odds_event(ODDS[1]) is None  # Spain/Japan has empty bookmakers


def test_parse_scores_event_decides_outcome():
    res = parse_scores_event(SCORES[0])
    assert res == {"id": "abc123", "result": "home"}   # Brazil 2-1 Morocco
    draw = parse_scores_event(SCORES[1])
    assert draw == {"id": "ghi789", "result": "draw"}  # France 1-1 Canada


def test_parse_scores_event_skips_incomplete():
    assert parse_scores_event(SCORES[2]) is None  # not completed


def test_slugify_case_id():
    cid = slugify_case_id("2026-06-20T19:00:00Z", "Brazil", "Morocco")
    assert cid == "wc26_20260620_BRA_MOR"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_oddsapi.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'oddsapi'`.

- [ ] **Step 4: Write `oddsapi.py`**

Create `tasks/worldcup_betting/oddsapi.py`:
```python
"""Thin the-odds-api v4 client + pure parsers for the worldcup_betting task.

Network is isolated to fetch_odds()/fetch_scores() (urllib, stdlib only). The
parse_* functions are pure and unit-tested against captured fixture JSON.

API docs: https://the-odds-api.com/liveapi/guides/v4/
Sport key: soccer_fifa_world_cup ; market: h2h ; oddsFormat: decimal.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

SPORT = "soccer_fifa_world_cup"
_BASE = "https://api.the-odds-api.com/v4"


# --- pure parsing ----------------------------------------------------------

def _avg_h2h_prices(event: dict) -> dict | None:
    """Average decimal h2h prices across all bookmakers -> {home,draw,away}.

    Returns None if no bookmaker carries an h2h market for this event.
    """
    home, away = event["home_team"], event["away_team"]
    buckets = {"home": [], "draw": [], "away": []}
    for bk in event.get("bookmakers") or []:
        for mk in bk.get("markets") or []:
            if mk.get("key") != "h2h":
                continue
            for oc in mk.get("outcomes") or []:
                name, price = oc.get("name"), oc.get("price")
                if price is None:
                    continue
                if name == home:
                    buckets["home"].append(float(price))
                elif name == away:
                    buckets["away"].append(float(price))
                elif name == "Draw":
                    buckets["draw"].append(float(price))
    if not all(buckets[k] for k in ("home", "draw", "away")):
        return None
    return {k: round(sum(v) / len(v), 4) for k, v in buckets.items()}


def parse_odds_event(event: dict) -> dict | None:
    """Normalize one the-odds-api odds event. None if no usable h2h odds."""
    odds = _avg_h2h_prices(event)
    if odds is None:
        return None
    return {
        "id": event["id"],
        "home_team": event["home_team"],
        "away_team": event["away_team"],
        "commence_time": event["commence_time"],
        "odds": odds,
    }


def parse_scores_event(event: dict) -> dict | None:
    """Decide home/draw/away from a completed scores event. None if not done."""
    if not event.get("completed"):
        return None
    scores = event.get("scores") or []
    by_name = {s["name"]: int(s["score"]) for s in scores if s.get("score") is not None}
    home, away = event["home_team"], event["away_team"]
    if home not in by_name or away not in by_name:
        return None
    hs, as_ = by_name[home], by_name[away]
    result = "home" if hs > as_ else "away" if as_ > hs else "draw"
    return {"id": event["id"], "result": result}


def slugify_case_id(commence_time: str, home_team: str, away_team: str) -> str:
    """wc26_<YYYYMMDD>_<HOME3>_<AWAY3> — uppercase, alnum-only team prefixes."""
    date = commence_time[:10].replace("-", "")

    def code(name: str) -> str:
        letters = re.sub(r"[^A-Za-z]", "", name).upper()
        return (letters[:3] or "XXX")

    return f"wc26_{date}_{code(home_team)}_{code(away_team)}"


# --- network (not unit-tested; exercised by snapshot.py / grade.py) ---------

def _get(path: str, params: dict) -> list:
    url = f"{_BASE}{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode())


def fetch_odds(api_key: str) -> list:
    """Upcoming WC fixtures with decimal h2h odds (EU + UK + US books)."""
    return _get(f"/sports/{SPORT}/odds", {
        "apiKey": api_key, "regions": "eu,uk,us",
        "markets": "h2h", "oddsFormat": "decimal",
    })


def fetch_scores(api_key: str, days_from: int = 3) -> list:
    """Recently completed (and live) WC fixtures with scores."""
    return _get(f"/sports/{SPORT}/scores", {
        "apiKey": api_key, "daysFrom": str(days_from),
    })
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_oddsapi.py -q`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add tasks/worldcup_betting/oddsapi.py tasks/worldcup_betting/test_oddsapi.py tasks/worldcup_betting/fixtures/odds_sample.json tasks/worldcup_betting/fixtures/scores_sample.json
git commit -m "feat(worldcup_betting): odds-api client + pure parsers + fixtures"
```

---

### Task 5: snapshot.py — freeze upcoming fixtures into cases

**Files:**
- Create: `tasks/worldcup_betting/snapshot.py`
- Test: `tasks/worldcup_betting/test_snapshot.py`

`snapshot.py` turns parsed odds events into committed case files. Factor the file-writing into a pure-ish `freeze_event(base_dir, event)` so it's testable without the network, and a `main()` that wires `fetch_odds` → `freeze_event` → manifest update.

- [ ] **Step 1: Write the failing test**

Create `tasks/worldcup_betting/test_snapshot.py`:
```python
import json
from pathlib import Path
from snapshot import freeze_event, rebuild_traptask_yaml, _update_manifest, QUESTION_TEMPLATE

EVENT = {
    "id": "abc123",
    "home_team": "Brazil",
    "away_team": "Morocco",
    "commence_time": "2026-06-20T19:00:00Z",
    "odds": {"home": 2.10, "draw": 3.40, "away": 3.60},
}


def test_freeze_event_writes_input_and_expected(tmp_path):
    cid = freeze_event(tmp_path, EVENT)
    assert cid == "wc26_20260620_BRA_MOR"

    q = (tmp_path / "inputs" / cid / "question.txt").read_text()
    assert "Brazil" in q and "Morocco" in q
    assert "home" in q and "draw" in q and "away" in q  # output format named
    # odds must NOT leak into the model's input — blind prediction
    assert "2.1" not in q and "3.4" not in q and "3.6" not in q

    ans = json.loads((tmp_path / "expected" / cid / "answer.json").read_text())
    assert ans["graded"] is False
    assert ans["result"] is None
    assert ans["event_id"] == "abc123"
    assert ans["odds"] == {"home": 2.10, "draw": 3.40, "away": 3.60}  # kept for settlement
    assert ans["matchers"] == [{"kind": "roi_logloss"}]


def test_freeze_event_is_idempotent(tmp_path):
    cid1 = freeze_event(tmp_path, EVENT)
    cid2 = freeze_event(tmp_path, EVENT)
    assert cid1 == cid2
    # only one case dir exists
    assert len(list((tmp_path / "inputs").iterdir())) == 1


def test_rebuild_traptask_yaml_is_deterministic_and_safe(tmp_path):
    (tmp_path / "gold.cases.json").write_text("[]")
    rebuild_traptask_yaml(tmp_path)
    text1 = (tmp_path / "traptask.yaml").read_text()
    assert "cases: []" in text1
    assert "cmd: python3 judge.py" in text1 and "cmd: python3 grader.py" in text1

    _update_manifest(tmp_path, "wc26_20260620_BRA_MOR", EVENT)
    rebuild_traptask_yaml(tmp_path)
    text2 = (tmp_path / "traptask.yaml").read_text()
    assert "id: wc26_20260620_BRA_MOR" in text2
    assert "- worldcup_2026" in text2
    # rebuilding again is byte-identical (no corruption on re-run)
    rebuild_traptask_yaml(tmp_path)
    assert (tmp_path / "traptask.yaml").read_text() == text2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_snapshot.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'snapshot'`.

- [ ] **Step 3: Write `snapshot.py`**

Create `tasks/worldcup_betting/snapshot.py`:
```python
"""Freeze upcoming 2026 World Cup fixtures + odds into committed task cases.

Run close to kickoff (so the snapshot odds approximate the closing line):
  ODDS_API_KEY=... python3 snapshot.py

For each upcoming fixture with usable h2h odds it writes:
  inputs/<id>/question.txt        — matchup + kickoff only (NO odds — blind predict)
  expected/<id>/answer.json       — odds frozen here, graded:false, result:null
and appends the case to gold.cases.json + traptask.yaml. Idempotent: re-running
skips fixtures already frozen (so odds are never overwritten after freeze).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import fetch_odds, parse_odds_event, slugify_case_id

HERE = Path(__file__).parent

QUESTION_TEMPLATE = """\
2026 FIFA World Cup — match prediction

{home} (home) vs {away} (away)
Kickoff: {commence}

Task: using your own knowledge of these teams, estimate the probability of each
outcome. Output ONLY a JSON object on a single line with keys "home", "draw",
"away" whose values are probabilities that sum to 1.
Example: {{"home": 0.45, "draw": 0.28, "away": 0.27}}
Do not explain your reasoning. Output only the JSON.
"""


def freeze_event(base_dir: Path, event: dict) -> str:
    """Write inputs/ + expected/ for one parsed odds event. Returns the case id.

    No-op (returns the id) if the case already exists, so a re-run never
    overwrites previously frozen odds.
    """
    cid = slugify_case_id(event["commence_time"], event["home_team"], event["away_team"])
    in_dir = base_dir / "inputs" / cid
    exp_dir = base_dir / "expected" / cid
    if (exp_dir / "answer.json").exists():
        return cid

    in_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    odds = event["odds"]
    # NOTE: odds are deliberately NOT written into question.txt — the model
    # predicts blind. They live only in answer.json, for settlement.
    (in_dir / "question.txt").write_text(QUESTION_TEMPLATE.format(
        home=event["home_team"], away=event["away_team"],
        commence=event["commence_time"],
    ))
    (exp_dir / "answer.json").write_text(json.dumps({
        "id": cid,
        "event_id": event["id"],
        "type": "match_prediction",
        "home_team": event["home_team"],
        "away_team": event["away_team"],
        "commence_time": event["commence_time"],
        "odds": odds,
        "graded": False,
        "result": None,
        "matchers": [{"kind": "roi_logloss"}],
        "_source": "the-odds-api soccer_fifa_world_cup h2h (decimal)",
    }, indent=2) + "\n")
    return cid


TRAPTASK_HEADER = """\
dirs:
  inputs: inputs/
  expected: expected/

"""

TRAPTASK_FOOTER = """
judge:
  cmd: python3 judge.py

grader:
  cmd: python3 grader.py
"""


def _update_manifest(base_dir: Path, cid: str, event: dict) -> None:
    """Append the case to gold.cases.json (the source of truth) if not present."""
    manifest_path = base_dir / "gold.cases.json"
    manifest = json.loads(manifest_path.read_text())
    if any(c["id"] == cid for c in manifest):
        return
    desc = f"{event['home_team']} vs {event['away_team']} ({event['commence_time'][:10]})"
    manifest.append({"id": cid, "description": desc,
                     "commence_time": event["commence_time"]})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def rebuild_traptask_yaml(base_dir: Path) -> None:
    """Regenerate traptask.yaml deterministically from gold.cases.json.

    Rebuilding from the manifest (instead of string-splicing the YAML) means a
    re-run can never corrupt the file — it's a pure function of the manifest.
    """
    manifest = json.loads((base_dir / "gold.cases.json").read_text())
    if not manifest:
        cases_block = "cases: []\n"
    else:
        lines = ["cases:"]
        for c in manifest:
            tags = "  - example" if "example" in c["id"] else ""
            lines.append(f"- id: {c['id']}")
            lines.append(f"  description: \"{c['description']}\"")
            lines.append("  tags:")
            lines.append("  - worldcup")
            lines.append("  - worldcup_2026")
            if tags:
                lines.append(tags)
        cases_block = "\n".join(lines) + "\n"
    (base_dir / "traptask.yaml").write_text(TRAPTASK_HEADER + cases_block + TRAPTASK_FOOTER)


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com)")
    events = fetch_odds(api_key)
    frozen = 0
    for raw in events:
        parsed = parse_odds_event(raw)
        if parsed is None:
            continue
        cid = freeze_event(HERE, parsed)
        _update_manifest(HERE, cid, parsed)
        frozen += 1
    rebuild_traptask_yaml(HERE)
    print(f"snapshot: {frozen} fixture(s) frozen ({len(events)} returned by API)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_snapshot.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tasks/worldcup_betting/snapshot.py tasks/worldcup_betting/test_snapshot.py
git commit -m "feat(worldcup_betting): snapshot.py to freeze fixtures into cases"
```

---

### Task 6: grade.py — fill actual results into frozen cases

**Files:**
- Create: `tasks/worldcup_betting/grade.py`
- Test: `tasks/worldcup_betting/test_grade.py`

`grade.py` reads completed scores and stamps the outcome into each ungraded `expected/<id>/answer.json`. Factor a pure `apply_result(base_dir, event_id, result)` for testing.

- [ ] **Step 1: Write the failing test**

Create `tasks/worldcup_betting/test_grade.py`:
```python
import json
from pathlib import Path
import pytest
from grade import apply_result


def _seed_case(base_dir, cid, event_id):
    exp = base_dir / "expected" / cid
    exp.mkdir(parents=True)
    (exp / "answer.json").write_text(json.dumps({
        "id": cid, "event_id": event_id, "graded": False, "result": None,
        "odds": {"home": 2.1, "draw": 3.4, "away": 3.6},
    }))


def test_apply_result_marks_graded(tmp_path):
    _seed_case(tmp_path, "wc26_20260620_BRA_MOR", "abc123")
    n = apply_result(tmp_path, "abc123", "home")
    assert n == 1
    ans = json.loads((tmp_path / "expected" / "wc26_20260620_BRA_MOR" / "answer.json").read_text())
    assert ans["graded"] is True
    assert ans["result"] == "home"


def test_apply_result_no_match_returns_zero(tmp_path):
    _seed_case(tmp_path, "wc26_20260620_BRA_MOR", "abc123")
    assert apply_result(tmp_path, "zzz999", "home") == 0


def test_apply_result_idempotent(tmp_path):
    _seed_case(tmp_path, "wc26_20260620_BRA_MOR", "abc123")
    apply_result(tmp_path, "abc123", "home")
    # already graded -> not re-applied
    assert apply_result(tmp_path, "abc123", "away") == 0
    ans = json.loads((tmp_path / "expected" / "wc26_20260620_BRA_MOR" / "answer.json").read_text())
    assert ans["result"] == "home"  # unchanged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_grade.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'grade'`.

- [ ] **Step 3: Write `grade.py`**

Note: `freeze_event` (Task 5) already writes `"event_id": event["id"]` into each `answer.json`; `grade.py` matches completed scores on that field.

Create `tasks/worldcup_betting/grade.py`:
```python
"""Stamp actual results into frozen worldcup_betting cases.

Run after matches finish:  ODDS_API_KEY=... python3 grade.py

Pulls completed fixtures from the-odds-api scores endpoint and writes the decided
outcome (home/draw/away) into the matching expected/<id>/answer.json, flipping
graded:false -> true. Idempotent: already-graded cases are left untouched.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import fetch_scores, parse_scores_event

HERE = Path(__file__).parent


def apply_result(base_dir: Path, event_id: str, result: str) -> int:
    """Write result into the case whose event_id matches. Returns 1 if updated."""
    for ans_path in (base_dir / "expected").glob("*/answer.json"):
        data = json.loads(ans_path.read_text())
        if data.get("event_id") != event_id or data.get("graded"):
            continue
        data["graded"] = True
        data["result"] = result
        ans_path.write_text(json.dumps(data, indent=2) + "\n")
        return 1
    return 0


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com)")
    events = fetch_scores(api_key)
    updated = 0
    for raw in events:
        decided = parse_scores_event(raw)
        if decided is None:
            continue
        updated += apply_result(HERE, decided["id"], decided["result"])
    print(f"grade: {updated} fixture(s) newly graded")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tasks/worldcup_betting && python3 -m pytest test_grade.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tasks/worldcup_betting/grade.py tasks/worldcup_betting/test_grade.py tasks/worldcup_betting/snapshot.py
git commit -m "feat(worldcup_betting): grade.py to stamp results into cases"
```

---

### Task 7: Seed example cases + end-to-end dry run

**Files:**
- Create: `tasks/worldcup_betting/inputs/wc26_example_BRA_MOR/question.txt`
- Create: `tasks/worldcup_betting/expected/wc26_example_BRA_MOR/answer.json`
- Modify: `tasks/worldcup_betting/gold.cases.json`
- Modify: `tasks/worldcup_betting/traptask.yaml`

So a fresh clone has a runnable, fully-graded example (no API key needed to see the task work). Use a clearly-labeled `example` id so it's distinguishable from live fixtures.

- [ ] **Step 1: Create one frozen, already-graded example case**

Generate it with the real code path (so it matches `freeze_event` output exactly), then hand-edit the result in. Run:
```bash
cd tasks/worldcup_betting && python3 - <<'PY'
from pathlib import Path
import json
from snapshot import freeze_event
ev = {"id": "example", "home_team": "Brazil", "away_team": "Morocco",
      "commence_time": "2026-06-20T19:00:00Z",
      "odds": {"home": 2.10, "draw": 3.40, "away": 3.60}}
cid = freeze_event(Path("."), ev)
# rename to an explicit example id and stamp a result
import shutil
for sub in ("inputs", "expected"):
    src = Path(sub) / cid
    dst = Path(sub) / "wc26_example_BRA_MOR"
    if dst.exists(): shutil.rmtree(dst)
    src.rename(dst)
ans_path = Path("expected/wc26_example_BRA_MOR/answer.json")
ans = json.loads(ans_path.read_text())
ans["id"] = "wc26_example_BRA_MOR"
ans["event_id"] = "example"
ans["graded"] = True
ans["result"] = "home"
ans_path.write_text(json.dumps(ans, indent=2) + "\n")
print("seeded", cid)
PY
```
Expected: prints `seeded ...`; the `wc26_example_BRA_MOR` input + a graded answer exist.

- [ ] **Step 2: Add the example to the manifest + traptask.yaml**

Edit `tasks/worldcup_betting/gold.cases.json` to:
```json
[
  {
    "id": "wc26_example_BRA_MOR",
    "description": "Brazil vs Morocco (2026-06-20) — committed example",
    "commence_time": "2026-06-20T19:00:00Z"
  }
]
```
Edit `tasks/worldcup_betting/traptask.yaml` `cases:` to:
```yaml
cases:
- id: wc26_example_BRA_MOR
  description: "Brazil vs Morocco (2026-06-20) — committed example"
  tags:
  - worldcup
  - worldcup_2026
  - example
```

- [ ] **Step 3: Verify judge scores the example end-to-end**

Simulate a model answer and run the judge directly against the example case. Run:
```bash
cd tasks/worldcup_betting && python3 - <<'PY'
import json, os, subprocess, sys, tempfile
from pathlib import Path
d = Path(tempfile.mkdtemp())
(d / "stdout.txt").write_text('{"home":0.55,"draw":0.25,"away":0.20}')
(d / "meta.json").write_text(json.dumps({"exit_code": 0}))
payload = {
    "outputs": {"case_stdout": str(d/"stdout.txt"), "case_meta.json": str(d/"meta.json")},
    "expected": {"answer.json": "expected/wc26_example_BRA_MOR/answer.json"},
}
out = subprocess.run([sys.executable, "judge.py"], env={**os.environ, "TRAPTASK_PAYLOAD": json.dumps(payload)},
                     capture_output=True, text=True, check=True)
m = json.loads(out.stdout)
print(json.dumps(m, indent=2))
assert m["result"] == "home"
assert m["staked"] == 1.0 and m["returned"] == 2.1      # bet home, won
assert m["profit"] == 1.1
assert m["score"] == 1.0
print("JUDGE OK")
PY
```
Expected: prints metrics then `JUDGE OK` (home bet placed at 2.10, won, profit 1.1).

- [ ] **Step 4: Verify grader aggregates the example**

Run:
```bash
cd tasks/worldcup_betting && python3 - <<'PY'
import json, os, subprocess, sys
cases = [{"metrics": {"score": 1.0, "profit": 1.1, "staked": 1.0, "log_loss": 0.5977}, "duration": 0.1}]
out = subprocess.run([sys.executable, "grader.py"], env={**os.environ, "TRAPTASK_PAYLOAD": json.dumps(cases)},
                     capture_output=True, text=True, check=True)
g = json.loads(out.stdout)
print(json.dumps(g, indent=2))
assert g["passed"] is True and g["roi"] == 1.1 and g["n_graded"] == 1
print("GRADER OK")
PY
```
Expected: prints verdict then `GRADER OK` (roi 1.1, passed).

- [ ] **Step 5: Run the whole test suite**

Run: `cd tasks/worldcup_betting && python3 -m pytest -q`
Expected: PASS (all tests across the 5 test files — 25 total: judge 10, grader 4, oddsapi 5, snapshot 3, grade 3).

- [ ] **Step 6: Commit**

```bash
git add tasks/worldcup_betting/inputs tasks/worldcup_betting/expected tasks/worldcup_betting/gold.cases.json tasks/worldcup_betting/traptask.yaml
git commit -m "test(worldcup_betting): seed committed example case + e2e dry run"
```

---

### Task 8: Live-run docs + scheduling note

**Files:**
- Modify: `tasks/worldcup_betting/README.md`

Document the operational loop so a non-tech user can actually run the live leaderboard, and note how to automate it.

- [ ] **Step 1: Append an "Operating the live task" section to README.md**

Add to `tasks/worldcup_betting/README.md`:
```markdown
## Operating the live task

1. Get a free API key at the-odds-api.com and export it:
   `export ODDS_API_KEY=...`  (free tier: 500 requests/month — well within one
   snapshot + one grade per day for the whole tournament).
2. **Near kickoff:** `python3 snapshot.py` — freezes upcoming fixtures + odds
   (taken close to kickoff to approximate the closing line) into new cases. Commit
   the new `inputs/` + `expected/` files. Odds go into `expected/` only, never the
   model's input.
3. Run the eval: the harness feeds each `inputs/<id>/question.txt` to the model;
   pending fixtures (not yet played) score `null` and are skipped by the grader.
4. **After matches finish:** `python3 grade.py` — stamps results into the frozen
   cases. Re-run the eval (or just the grader) to update ROI + log-loss.

To automate, schedule `snapshot.py` each morning and `grade.py` each night via the
`/schedule` skill or cron. Both are idempotent — safe to run repeatedly.
```
Expected: README now documents the full daily loop.

- [ ] **Step 2: Final self-test of the whole suite**

Run: `cd tasks/worldcup_betting && python3 -m pytest -q`
Expected: PASS (all tests).

- [ ] **Step 3: Commit**

```bash
git add tasks/worldcup_betting/README.md
git commit -m "docs(worldcup_betting): operating instructions for the live loop"
```

---

## Self-review

**Spec coverage:**
- Forward-live framing → Tasks 5 (snapshot), 6 (grade), 8 (operating loop). ✓
- **Blind prediction** (odds withheld from input) → `QUESTION_TEMPLATE` has no odds (Task 5) + test asserts odds absent from `question.txt` (Task 5). ✓
- Calibration headline (log-loss + Brier) → `log_loss`/`brier_score` (Task 2) + `mean_log_loss`/`mean_brier` ranking (Task 3). ✓
- ROI value-betting diagnostic → `settle_bets` (Task 2) + `roi` aggregate, reframed as diagnostic not pass-gate (Task 3). ✓
- the-odds-api at snapshot time, frozen for offline grading → Task 4 (client/parsers) + Task 5 (freeze). ✓
- Frontier-LLMs-only first field → no agent scaffolding built; the `question.txt → stdout` contract is model-agnostic, so frontier models run directly. ✓
- Leakage guard → README rationale + forward-freeze mechanism (structural). ✓
- Self-contained committed example → Task 7. ✓
- `traptask.yaml` built deterministically from `gold.cases.json` (no string-surgery) → `rebuild_traptask_yaml` + idempotency test (Task 5). ✓
- Matches existing task conventions (traptask.yaml dirs/cases, `TRAPTASK_PAYLOAD` judge/grader contract, gold.cases.json) → Tasks 1–3, verified against `cuad`. ✓

**Type/name consistency:**
- `parse_probs`, `log_loss`, `brier_score`, `settle_bets` defined in Task 2, imported in Task 2 tests. ✓
- `parse_odds_event`, `parse_scores_event`, `slugify_case_id`, `fetch_odds`, `fetch_scores` defined in Task 4, used in Tasks 5–6. ✓
- `freeze_event(base_dir, event)`, `rebuild_traptask_yaml(base_dir)`, `_update_manifest(base_dir, cid, event)` defined Task 5, used in Tasks 5/7 and Task 5 tests. ✓
- `apply_result(base_dir, event_id, result)` consistent Task 6 test ↔ impl. ✓
- `event_id` field: written into `answer.json` by `freeze_event` (Task 5) and matched by `grade.py` (Task 6). ✓
- Matcher kind `roi_logloss` is written into `answer.json` (Task 5) but the judge doesn't branch on matcher kind (single grading path) — it's metadata only, consistent with how the judge reads `expected`. ✓

**Placeholder scan:** no TBD/TODO; every code step shows full code; every run step shows expected output. ✓

**Known limitation (documented, not a plan gap):** ROI separates skill from luck only at scale (~50+ graded matches). With a handful of group-stage fixtures the leaderboard **ranks by `mean_log_loss`** (with `mean_brier` as a robust companion) and treats early ROI as directional — stated in the README grading section and the grader docstring.
```
