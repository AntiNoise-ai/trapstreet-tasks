"""Overall grader for core_tool_selection_at_scale.

Aggregates per-case judge results into a run-level verdict. Beyond the single
headline accuracy this emits the three marginals the task was designed to
separate -- catalog size, correct-tool position, and catalog ambiguity -- plus
a failure-mode census.

The marginals are the honest unit of analysis here, not the per-cell numbers:
each cell holds 8 cases (one per intent family), while each marginal level
holds 16-40. Report cell values as directional and marginals as the claim.
"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.5


def breakdown(scored: list, field: str) -> dict:
    total: Counter = Counter()
    got: Counter = Counter()
    for c in scored:
        key = c["metrics"].get(field)
        if key is None:
            continue
        total[str(key)] += 1
        got[str(key)] += c["metrics"]["score"]
    return {k: round(got[k] / total[k], 3) for k in sorted(total, key=str)}


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_MANIFEST"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = sum(c["metrics"]["score"] for c in scored) / len(scored) if scored else 0.0

    # A provider/transport failure (context overflow, 5xx, timeout) is not a
    # discrimination failure. It still scores 0.0 in the headline -- otherwise
    # a solution could game the leaderboard by erroring on the cases it finds
    # hard -- but it is surfaced separately, and broken out by catalog size,
    # because errors concentrated at N=300 would otherwise read as a clean
    # "accuracy degrades with catalog size" effect. That is the single most
    # likely way this task produces a false positive, so it is reported next
    # to the number it would corrupt.
    errored = [c for c in scored if c["metrics"].get("failure_mode") == "solution_error"]
    valid = [c for c in scored if c["metrics"].get("failure_mode") != "solution_error"]
    accuracy_excl_errors = (
        sum(c["metrics"]["score"] for c in valid) / len(valid) if valid else 0.0
    )
    errors_by_n_tools = dict(Counter(str(c["metrics"].get("n_tools")) for c in errored))

    failure_modes = Counter(
        c["metrics"].get("failure_mode")
        for c in scored
        if c["metrics"]["score"] == 0.0 and c["metrics"].get("failure_mode")
    )
    # Which specific near-miss won, when one did -- the most article-relevant
    # detail the run produces.
    lost_to = Counter(
        c["metrics"].get("called_tool")
        for c in scored
        if c["metrics"]["score"] == 0.0 and c["metrics"].get("failure_mode") == "near_miss"
    )

    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    if durations:
        ds = sorted(durations)
        latency_ms_median = round(ds[len(ds) // 2] * 1000, 1)
        latency_ms_p95 = round(ds[int(0.95 * len(ds))] * 1000, 1) if len(ds) > 1 else latency_ms_median
        latency_ms_total = round(sum(ds) * 1000, 1)
    else:
        latency_ms_median = latency_ms_p95 = latency_ms_total = 0.0

    case_costs = [
        c["cost"]["cost_usd"]
        for c in cases
        if isinstance(c.get("cost"), dict) and c["cost"].get("cost_usd") is not None
    ]
    cost_usd_total = round(sum(case_costs), 4) if case_costs else None

    print(json.dumps({
        "passed": bool(scored) and accuracy >= PASS_THRESHOLD,
        "score": round(accuracy, 3),
        "n_passed": sum(1 for c in scored if c["metrics"]["score"] == 1.0),
        "n_total": len(cases),
        "n_scored": len(scored),
        "n_skipped_no_gold": len(skipped),
        "threshold": PASS_THRESHOLD,
        "n_solution_error": len(errored),
        "score_excluding_solution_errors": round(accuracy_excl_errors, 3),
        "solution_errors_by_n_tools": errors_by_n_tools,
        "by_ambiguity": breakdown(scored, "ambiguity"),
        "by_n_tools": breakdown(scored, "n_tools"),
        "by_position": breakdown(scored, "position"),
        "by_intent": breakdown(scored, "intent"),
        "by_category": breakdown(scored, "category"),
        "failure_modes": dict(failure_modes),
        "lost_to_near_miss": dict(lost_to.most_common()),
        "latency_ms_median": latency_ms_median,
        "latency_ms_p95": latency_ms_p95,
        "latency_ms_total": latency_ms_total,
        "cost_usd_total": cost_usd_total,
    }))


if __name__ == "__main__":
    main()
