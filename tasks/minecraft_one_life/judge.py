"""Per-case judge for the one_life task (Phase 0, self-reported).

ONE LIFE. The run ends at the first death, and the score is the tech-tree rung
the agent had reached *at that moment* -- not what it accumulated afterwards.

That is the whole point of this board. Its sibling, obtain-diamond, measures
the tech tree alone, and the tech tree alone is close to saturated: the same
setup that reached a diamond in 738 seconds on peaceful reached an iron pickaxe
on difficulty easy and then died four times to skeletons without ever getting
one. The discrimination lives in staying alive, so death has to cost something.

Because a death is a real loss -- the inventory drops where you fell -- a run
that continues past one is not the same run. So:

  deaths == 0  ->  score from `milestones` / `inventory` as usual
  deaths  > 0  ->  score ONLY from `milestones_at_death`

`milestones_at_death` is REQUIRED once anything died. Leaving it out while
reporting a death is a malformed report, not a generous default: without it the
most important number on the entry would be whatever the entrant remembered
afterwards. A harness that plays this task is expected to record it at the
moment it happens.

The solution — a Minecraft agent — plays a time-limited survival run and prints a
single JSON outcome object as the LAST line of stdout (diagnostics go to stderr):

    {"obtained": false, "item": "diamond", "count": 0,
     "ticks": 41234, "wall_time_s": 512.3,
     "inventory": ["stone_pickaxe x1", "iron_ingot x2", "cobblestone x40"],
     "milestones": ["wooden_pickaxe", "stone_pickaxe", "iron_ingot"],
     "video": "https://.../recording.mp4",
     "seed": "diamondrun", "mc_version": "1.20.4"}

SCORING IS GRADED BY TECH-TREE PROGRESS, not all-or-nothing. Reaching a diamond
is genuinely hard, so a run earns PARTIAL CREDIT for how far up the tree it got —
this makes the task discriminate between agents that get nowhere and agents that
nearly made it. The ladder (each rung's score, highest reached wins) lives in
`expected.json` under `milestones`, e.g.:

    wooden_pickaxe 0.2 · stone_pickaxe 0.4 · iron_ingot 0.6 · iron_pickaxe 0.8 · diamond 1.0

A rung counts as reached if the agent lists it in `milestones`, OR any of that
rung's items appears in the reported `inventory`, OR (for the goal) `obtained`.

Phase 0 is SELF-REPORTED: the judge trusts the report, but REQUIRES a non-empty
`video` link — video-first is the credibility floor until a deterministic
verifier lands (Phase 1). No video => score 0.0 regardless of progress.

I/O contract matches the trapstreet CLI (see cli/examples): reads
`TRAPTASK_MANIFEST` → run.stdout / run.meta / expected_dir.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def _parse_outcome(stdout: str) -> tuple[dict | None, str]:
    """Find the agent's JSON outcome. Tolerates surrounding log lines and code
    fences by scanning stdout for the last parseable JSON object."""
    s = stdout.strip()
    if not s:
        return None, "empty stdout"
    for candidate in (s, *reversed(s.splitlines())):
        c = candidate.strip().strip("`").strip()
        if not c.startswith("{"):
            continue
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj, ""
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj, ""
        except json.JSONDecodeError:
            pass
    return None, "no JSON outcome object found in stdout"


# Default tech-tree ladder, used when expected.json omits `milestones`. Each rung:
# key, its score, and the item names that PROVE the rung was reached (a later
# rung's items may prove an earlier one, but we take the highest reached anyway).
_DEFAULT_MILESTONES = [
    {"key": "wooden_pickaxe", "score": 0.2, "items": ["wooden_pickaxe"]},
    {"key": "stone_pickaxe", "score": 0.4, "items": ["stone_pickaxe"]},
    {"key": "iron_ingot", "score": 0.6,
     "items": ["iron_ingot", "iron_pickaxe", "iron_axe", "iron_sword", "iron_shovel", "iron_hoe", "iron_block"]},
    {"key": "iron_pickaxe", "score": 0.8, "items": ["iron_pickaxe"]},
    {"key": "diamond", "score": 1.0, "items": ["diamond", "diamond_block", "diamond_ore"]},
]


def _item_names(outcome: dict) -> set[str]:
    """Normalise the reported inventory to bare item names. Entries may look like
    'iron_ingot x3', 'iron_ingotx3', or plain 'iron_ingot'."""
    names: set[str] = set()
    inv = outcome.get("inventory") or []
    if isinstance(inv, list):
        for entry in inv:
            name = re.sub(r"\s*x?\s*\d+\s*$", "", str(entry).strip())
            if name:
                names.add(name.lower())
    return names


def _explicit_milestone_keys(outcome: dict) -> set[str]:
    ms = outcome.get("milestones")
    if isinstance(ms, list):
        return {str(k).lower() for k in ms}
    if isinstance(ms, dict):
        return {str(k).lower() for k, v in ms.items() if v}
    return set()


def evaluate(stdout: str, expected: dict, exit_code: int) -> dict[str, Any]:
    """Pure scoring function — unit-tested in tests/test_judge.py."""
    one_life = bool(expected.get("one_life", False))
    goal_item = str(expected["goal_item"]).lower()
    min_count = expected.get("min_count", 1)
    video_required = expected.get("video_required", True)
    milestones = expected.get("milestones") or _DEFAULT_MILESTONES

    outcome, err = _parse_outcome(stdout)
    if outcome is None:
        return {
            "score": 0.0,
            "milestone_score": 0.0,
            "highest_milestone": None,
            "obtained": False,
            "format_ok": False,
            "reason": err,
            "exit_code": exit_code,
        }

    item = str(outcome.get("item", "")).lower()
    count = outcome.get("count", 0)
    obtained = bool(outcome.get("obtained", False))
    video = str(outcome.get("video", "")).strip()
    video_declared = bool(video)

    count_valid = isinstance(count, int) and not isinstance(count, bool)
    goal_met = obtained and item == goal_item and count_valid and count >= min_count

    deaths = outcome.get("deaths")
    deaths_valid = isinstance(deaths, int) and not isinstance(deaths, bool) and deaths >= 0
    died = deaths_valid and deaths > 0

    # Items we can prove the agent had: the reported inventory, plus the goal item
    # if it was legitimately obtained (goal item may have been consumed/placed).
    present = _item_names(outcome)
    if goal_met:
        present.add(goal_item)
    explicit_keys = _explicit_milestone_keys(outcome)

    at_death_error = None
    if one_life:
        if not deaths_valid:
            at_death_error = "one-life task requires an integer `deaths` field"
        elif died:
            # Everything after the first death is off the record, including the
            # goal item: dying with a diamond you picked up on your second life
            # is not a one-life diamond.
            at_death = outcome.get("milestones_at_death")
            if not isinstance(at_death, list):
                at_death_error = (
                    "died but reported no `milestones_at_death` list -- required, "
                    "because the score is what had been reached when the run ended"
                )
            else:
                explicit_keys = {str(k).lower() for k in at_death}
                present = set()
                goal_met = goal_item in explicit_keys

    reached = []
    for m in milestones:
        key = str(m["key"]).lower()
        items = [str(i).lower() for i in m.get("items", [key])]
        if key in explicit_keys or any(i in present for i in items):
            reached.append(m)

    milestone_score = max((float(m["score"]) for m in reached), default=0.0)
    highest = max(reached, key=lambda m: float(m["score"]))["key"] if reached else None

    # Off by default: recorded on the result, not used to gate the score.
    score = milestone_score if (video_declared or not video_required) else 0.0
    if at_death_error is not None:
        # A report we cannot read honestly scores nothing rather than guessing.
        return {
            "score": 0.0,
            "milestone_score": 0.0,
            "highest_milestone": None,
            "obtained": False,
            "format_ok": False,
            "reason": at_death_error,
            "deaths": deaths,
            "exit_code": exit_code,
        }

    return {
        "score": round(score, 3),
        "milestone_score": round(milestone_score, 3),
        "highest_milestone": highest,
        "milestones_reached": [m["key"] for m in reached],
        "obtained": obtained,
        "item": item,
        "count": count,
        "goal_met": goal_met,
        "video_declared": video_declared,
        "video": video,
        "video_required": video_required,
        "deaths": deaths,
        "died": died,
        "one_life": one_life,
        "ticks": outcome.get("ticks"),
        "wall_time_s": outcome.get("wall_time_s"),
        "seed": outcome.get("seed"),
        "mc_version": outcome.get("mc_version"),
        "format_ok": True,
        "exit_code": exit_code,
    }


def main() -> None:
    data = json.loads(os.environ["TRAPTASK_MANIFEST"])
    run = data["run"]
    stdout = Path(run["stdout"]).read_text()
    exit_code = json.loads(Path(run["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(data["expected_dir"]) / "expected.json").read_text())

    print(json.dumps(evaluate(stdout, expected, exit_code)))


if __name__ == "__main__":
    main()
