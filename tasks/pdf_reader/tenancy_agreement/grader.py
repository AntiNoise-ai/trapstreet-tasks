"""Overall grader for the tenancy_agreement task.

Aggregates per-case judge results into a run-level verdict. Emits JSON to stdout —
trap stores it as GraderResult.metrics. Convention: include `passed` (bool) and
`score` (float) so the reporter can render them.

Pass threshold defaults to 80% accuracy; tweak below.
"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.80


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    if scored:
        accuracy = sum(c["metrics"]["score"] for c in scored) / len(scored)
    else:
        accuracy = 0.0

    # Break out accuracy by category (the judge tags each case with its category).
    by_category_score: Counter[str] = Counter()
    by_category_total: Counter[str] = Counter()
    for c in scored:
        cat = c["metrics"].get("category")
        if cat:
            by_category_total[cat] += 1
            by_category_score[cat] += c["metrics"]["score"]

    by_category_pct = {
        k: round(by_category_score[k] / by_category_total[k], 3)
        for k in by_category_total
    }

    passed = bool(scored) and accuracy >= PASS_THRESHOLD

    # Latency stats — trap records `duration` (seconds) per case. The leaderboard
    # displays median latency. Round-trip to ms for the JSON contract.
    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    if durations:
        ds = sorted(durations)
        latency_ms_median = round(ds[len(ds) // 2] * 1000, 1)
        latency_ms_p95 = round(ds[int(0.95 * len(ds))] * 1000, 1) if len(ds) > 1 else latency_ms_median
        latency_ms_total = round(sum(ds) * 1000, 1)
    else:
        latency_ms_median = latency_ms_p95 = latency_ms_total = 0.0

    # Cost — sum per-case usd_cost if the solution captured usage; otherwise
    # leave it None and let the regrade/submit script stamp a known total.
    case_costs = [c["metrics"].get("usd_cost") for c in scored if isinstance(c.get("metrics"), dict)]
    cost_usd_total = round(sum(x for x in case_costs if x is not None), 4) if any(x is not None for x in case_costs) else None

    n_passed = sum(1 for c in scored if c["metrics"]["score"] == 1.0)

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
