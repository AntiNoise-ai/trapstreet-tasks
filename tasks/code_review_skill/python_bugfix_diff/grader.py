"""Overall grader for the code_review_skill/python_bugfix_diff task.

Aggregates per-case judge results (the trap-cli TRAPTASK_MANIFEST list) into
a run-level verdict. Same shape as wildlife_camera_trap/grader.py and
connections/word_groups/grader.py.
"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.5


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_MANIFEST"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = sum(c["metrics"]["score"] for c in scored) / len(scored) if scored else 0.0

    by_category_score: Counter[str] = Counter()
    by_category_total: Counter[str] = Counter()
    for c in scored:
        cat = c["metrics"].get("bug_category")
        if cat:
            by_category_total[cat] += 1
            by_category_score[cat] += c["metrics"]["score"]
    by_category_pct = {
        k: round(by_category_score[k] / by_category_total[k], 3) for k in by_category_total
    }

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

    n_passed = sum(1 for c in scored if c["metrics"]["score"] == 1.0)

    passed = bool(scored) and accuracy >= PASS_THRESHOLD

    print(json.dumps({
        "passed": passed,
        "score": round(accuracy, 3),
        "n_passed": n_passed,
        "n_total": len(cases),
        "n_scored": len(scored),
        "n_skipped_no_gold": len(skipped),
        "threshold": PASS_THRESHOLD,
        "by_category": by_category_pct,
        "latency_ms_median": latency_ms_median,
        "latency_ms_p95": latency_ms_p95,
        "latency_ms_total": latency_ms_total,
        "cost_usd_total": cost_usd_total,
    }))


if __name__ == "__main__":
    main()
