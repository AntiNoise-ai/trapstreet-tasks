"""Overall grader for debug_subscription_billing_pipeline.

Aggregates per-case judge results (the trap-cli TRAPTASK_MANIFEST list)
into a run-level verdict. This aggregation logic is standard across every
task in this repo -- usually nothing to customize here. If your judge's
metrics dict uses a different field name than "bug_category" for its
category breakdown, update CATEGORY_FIELD below; otherwise leave this file
as-is.
"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.5
CATEGORY_FIELD = "category"  # change to match your judge.py's metrics dict, or None to disable


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_MANIFEST"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = sum(c["metrics"]["score"] for c in scored) / len(scored) if scored else 0.0

    by_category_pct = {}
    if CATEGORY_FIELD:
        by_category_score: Counter[str] = Counter()
        by_category_total: Counter[str] = Counter()
        for c in scored:
            cat = c["metrics"].get(CATEGORY_FIELD)
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
