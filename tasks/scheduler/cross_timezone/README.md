# Cross-Timezone Scheduler

A trap-compatible task that asks an agent to schedule a meeting across
attendees in different time zones, given each attendee's local availability
window. The agent must return a JSON object with a single canonical
meeting time in UTC plus each attendee's local start time.

The eval is **pure-rule-based** (no LLM-judge): the judge uses Python's
`zoneinfo` to convert UTC ↔ local, then checks the agent's answer against
the gold availability windows.

---

## Layout

```
cross_timezone/
├── README.md
├── traptask.yaml             # case list + judge/grader cmds
├── judge.py                  # per-case scorer (zoneinfo-driven; strict)
├── grader.py                 # aggregator (score, latency, cost, by-category)
├── gold.cases.json           # source-of-truth case data
├── inputs/
│   └── {case_id}/
│       └── question.txt      # the scheduling brief
└── expected/
    └── {case_id}/
        └── answer.json       # gold UTC window + per-attendee availability + canonical answer
```

## Cases (v0 — 2 cases)

| id | category | difficulty | what it tests |
|---|---|---|---|
| `dst_gap_with_ist` | `dst_boundary` | hard | UK still on GMT (DST starts 2026-03-29) **and** India on UTC+5:30 — catches models that assume "London in spring = BST" or round India to UTC+5 |
| `dst_quarter_hour_sydney` | `multi_zone_expert` | expert | 5 attendees · all of `dst_gap_with_ist`'s traps **plus** Nepal `UTC+5:45` (quarter-hour) + Sydney `UTC+11` (southern-hemisphere DST in March) + day-shift for Sam (their local date is the next day). Exactly **one** valid start time exists. |

Planned additions (still to draft):

| Idea | Hits |
|---|---|
| Simple 2-zone in May | baseline TZ math |
| 3-zone with Sydney (UTC+10/11) crossing midnight | day-boundary |
| October DST gap (UK ends BST Oct 25, US Nov 1 — 1-week reverse) | symmetric DST |
| 5-attendee overlap (Sydney/Singapore/Mumbai/Berlin/SF) | narrow overlap |
| **No overlap exists** → expected `{"start_utc": null, "reason": "..."}` | refusal vs hallucination |
| Recurring weekly across a DST shift | series consistency |

---

## Solution contract

Each solution must:

1. Read `INPUTS` env var (JSON dict mapping `filename → absolute path`).
2. Read `INPUTS["question.txt"]` — the scheduling brief.
3. Print exactly one JSON object to **stdout**, matching this schema:

   ```json
   {
     "start_utc": "2026-03-26T14:00:00Z",
     "duration_min": 60,
     "attendees": [
       {"name": "Alice", "tz": "America/Los_Angeles", "local_start": "2026-03-26 07:00"},
       {"name": "Bob",   "tz": "Europe/London",        "local_start": "2026-03-26 14:00"},
       {"name": "Priya", "tz": "Asia/Kolkata",         "local_start": "2026-03-26 19:30"}
     ]
   }
   ```

The judge tolerates markdown code-fence wrappers (`` ```json ... ``` ``) — but
not prose. Plain JSON is the canonical format.

---

## What the judge checks (strict, no partial credit)

| # | Check | How it's verified |
|---|---|---|
| 1 | stdout parses as a JSON object | `json.loads` (markdown fences stripped) |
| 2 | `start_utc` is ISO 8601 with explicit UTC (`Z` or `+00:00`) | `datetime.fromisoformat` |
| 3 | `start_utc` ∈ `[expected_start_utc_min, expected_start_utc_max]` | arithmetic |
| 4 | `duration_min` matches exactly | int equality |
| 5 | For every attendee, `local_start` ≈ converted UTC (± 1 min) | `zoneinfo`-based conversion |
| 6 | For every attendee, the meeting fits inside their availability window | naive datetime arithmetic |

Any single check failing → score 0.0. All pass → 1.0.

---

## Example: the `dst_gap_with_ist` case explained

**Today** = 2026-03-25 (Wednesday). Meeting is *tomorrow* (Thursday 2026-03-26).

| Attendee | TZ | Offset on 2026-03-26 | Why |
|---|---|---|---|
| Alice (SF)   | `America/Los_Angeles` | UTC−7 (PDT) | US DST'd on 2026-03-08 |
| Bob (London) | `Europe/London`       | UTC+0 (GMT) | UK DST starts 2026-03-29 — Bob is still on GMT |
| Priya (Mumbai) | `Asia/Kolkata`      | UTC+5:30 (IST) | India has no DST |

Their local 2-hour availability windows all align with UTC **14:00–16:00**
on this date — overlap window for the 60-min meeting is start times in
`[14:00Z, 15:00Z]`.

Common failure modes:

| Model thinks | Resulting UTC start | Off by |
|---|---|---|
| "London in spring is BST" | 13:00Z | −1 hr |
| "India is UTC+5" | 14:30Z (but with wrong local times) | +30 min and inconsistent |
| Both errors | 13:30Z | chaos |
| Off-by-one date math (`tomorrow` ≠ +1 day) | wrong date entirely | clearly wrong |

---

## Wiring up a solution

From a solution dir with a `trap.yaml` pointing here:

```yaml
tasks:
  cross-timezone-scheduler:
    cmd: uv run python solution.py
    traptask: /path/to/trapstreet-tasks/tasks/scheduler/cross_timezone
    timeout: 120
```

Then:

```bash
uv run tp run                        # all cases
uv run tp run --fail-fast            # stop on first failure
uv run tp submit cross-timezone-scheduler   # upload to trapstreet.run
```
