# World Cup Betting — live ROI eval

TrapStreet's first **live** task: AI agents predict 2026 FIFA World Cup fixtures
**blind** (they never see the odds), and are graded after kickoff on how well
calibrated they were — and whether their judgment could beat the bookmaker.

## What this task tests

**Can an AI predict football it has never seen — well enough to beat the bookmaker?**

Each case is one World Cup fixture. The model gets *only* the matchup and kickoff
time — **never the odds** — and must output its own probability for each outcome
(`home` / `draw` / `away`). After the match is played, we grade two ways:

- **Calibration: log-loss + Brier** (headline / ranking) — how good the model's
  *independent* probabilities were. Because it never saw the odds, it can't game
  this by parroting the bookmaker line; it has to actually know football.
- **ROI vs. the bookmaker** (value-betting diagnostic) — a fixed flat-stake rule
  bets $1 on every outcome the model's blind estimate rates +EV against the frozen
  odds (`p × odds > 1`). ROI = profit ÷ total staked. Positive ROI means the model
  found value the held-out line missed; most can't.

> Models are **ranked by mean log-loss, then ROI**. On a sharp market and a small
> sample almost everyone runs slightly negative ROI, so ROI only separates the
> field at scale (~50+ graded matches). Treat early ROI as directional.

## Why the model is graded blind

If the input showed the odds, every frontier model would just invert them
(`p ≈ 1/odds`, renormalized) and report the bookmaker's own de-vigged line. Books
are sharply calibrated, so all models would land at near-identical log-loss — the
metric would measure arithmetic, not prediction, and reward regurgitation over
judgment. Hiding the odds makes log-loss a real independent-calibration test, and
makes ROI genuine value-betting: build the estimate first, *then* compare to the
line — exactly how pro bettors work.

## Why the 2026 World Cup (leakage)

A betting eval is only valid if the model doesn't already know the result. Every
frontier model has a training cutoff (~Jan 2026), so any past tournament is
memorized. The 2026 World Cup is being played *now*, after every model's cutoff —
and because we freeze inputs before kickoff, leakage is structurally impossible.

## Input

`inputs/<case-id>/question.txt` — matchup (home vs away) + kickoff time + an
instruction to output `{"home":p,"draw":p,"away":p}`. **The odds are deliberately
withheld.**

## Expected output

stdout: a JSON object with `home`/`draw`/`away` probabilities (or `{"answer":"..."}`
wrapping the same). Probabilities are renormalized if they don't sum to 1; an
unparseable answer fails the case.

## How answers are graded

`judge.py` (offline, no network) reads the actual result and the frozen odds from
`expected/<id>/answer.json` and emits per-case `log_loss`, `brier`, an accuracy
`score` (did it call the winner), and — once odds are present — `staked` /
`returned` / `profit`. `grader.py` ranks by `mean_log_loss` and reports
`mean_brier`, `winner_accuracy` (fraction whose argmax was the actual winner —
biased low, since argmax is never "draw"), and `roi`. A fixture that hasn't been
played yet scores `null` and is skipped (that's how a live, growing leaderboard
works).

`snapshot.py` and `grade.py` print a `WARNING:` to stderr whenever the API returns
a team name that isn't explicitly mapped, or a completed match joins to no case —
so a name/date mismatch shows up loudly instead of silently dropping a fixture
from the board. On the **first** key'd `snapshot.py`, eyeball the team strings the
API actually returns and confirm each resolves to the right code before trusting
the grading.

Case-id convention: `wc26_<YYYYMMDD>_<HOME>_<AWAY>` using FIFA 3-letter codes
(e.g. `wc26_20260624_SCO_BRA`). Cases join to API data by **date + team-pair**
(order-independent), so a home/away swap between sources doesn't break grading.

## The live mechanism

```
near kickoff              model answers            after final whistle
──────────────           ──────────────          ────────────────────
seed.py / snapshot.py  →  question.txt        →   grade.py
freeze fixtures + odds    fed to each model       fetch results, fill them in
(odds hidden in           (unplayed games          → re-grade, leaderboard
 expected/)                score null, skipped)        updates
```

- `seed.py` — create cases from a known fixture list **without an API key** (used
  to set up upcoming matches now; odds back-filled later). Idempotent.
- `snapshot.py` — `ODDS_API_KEY=... python3 snapshot.py` — fetch upcoming fixtures
  + odds; back-fill odds onto seeded cases (matched by date + team-pair) and create
  any new fixtures. Run close to kickoff so the snapshot approximates the closing
  line.
- `grade.py` — `ODDS_API_KEY=... python3 grade.py` — fetch finished-match results
  and stamp the outcome into each case.

Grading and replay need **no network** — odds and results are frozen into files;
only `snapshot.py` / `grade.py` call the API (mirroring how `cuad/build_cases.py`
downloads upstream data). The committed cases are self-contained.

## Operating the live task

1. Get a free key at the-odds-api.com (free tier: 500 req/month — ample for one
   snapshot + one grade per day): `export ODDS_API_KEY=...`
2. **Set up upcoming matches:** `python3 seed.py` (no key needed) — or
   `python3 snapshot.py` (with key) to fetch fixtures + odds directly. Commit the
   new `inputs/` + `expected/` files.
3. Run the eval: the harness feeds each `question.txt` to the model; pending
   fixtures score `null` and are skipped by the grader.
4. **Near kickoff:** `python3 snapshot.py` to back-fill odds onto seeded cases.
5. **After matches finish:** `python3 grade.py` to stamp results. Re-run the eval
   (or just the grader) to update the leaderboard.

To automate, schedule `snapshot.py` and `grade.py` daily via `/schedule` or cron.
Both are idempotent — safe to run repeatedly.

## Tests

```bash
pytest -q       # 32 tests: judge math, grader aggregation, odds/score parsing,
                # case seeding, odds back-fill orientation, result grading
```

## Data source & attribution

Odds and results from [the-odds-api.com](https://the-odds-api.com)
(`soccer_fifa_world_cup`, `h2h` market, decimal). Odds are a snapshot taken near
kickoff (an approximation of the closing line), stored verbatim in each case's
`expected/answer.json` for reproducible settlement — **never shown to the model**.
Fixture schedule sourced from public match listings (Wikipedia / FIFA).
