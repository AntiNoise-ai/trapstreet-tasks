"""Overall grader for the imported CUAD task.

Aggregates per-case judge results into a run-level verdict. Emits JSON to stdout —
trap stores it as GraderResult.metrics. Beyond overall accuracy + by_category, CUAD
reports two diagnostic splits that are the whole point of the task:

  - recall_present   : accuracy on rows where the clause IS present.
                       Low here = the LAZINESS failure (missing real clauses).
  - precision_absent : accuracy on rows where the clause is ABSENT.
                       Low here = the HALLUCINATION failure (inventing clauses).
"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.80


def _accuracy(rows: list[dict]) -> float:
    return sum(r["metrics"]["score"] for r in rows) / len(rows) if rows else 0.0


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = _accuracy(scored)

    present = [c for c in scored if c["metrics"].get("gold_present") is True]
    absent = [c for c in scored if c["metrics"].get("gold_present") is False]

    by_category_score: Counter[str] = Counter()
    by_category_total: Counter[str] = Counter()
    for c in scored:
        cat = c["metrics"].get("category")
        if cat:
            by_category_total[cat] += 1
            by_category_score[cat] += c["metrics"]["score"]
    by_category_pct = {k: round(by_category_score[k] / by_category_total[k], 3)
                       for k in by_category_total}

    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    if durations:
        ds = sorted(durations)
        latency_ms_median = round(ds[len(ds) // 2] * 1000, 1)
        latency_ms_p95 = round(ds[int(0.95 * len(ds))] * 1000, 1) if len(ds) > 1 else latency_ms_median
        latency_ms_total = round(sum(ds) * 1000, 1)
    else:
        latency_ms_median = latency_ms_p95 = latency_ms_total = 0.0

    case_costs = [c["metrics"].get("usd_cost") for c in scored if isinstance(c.get("metrics"), dict)]
    cost_usd_total = round(sum(x for x in case_costs if x is not None), 4) if any(x is not None for x in case_costs) else None

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
        "recall_present": round(_accuracy(present), 3),
        "n_present": len(present),
        "precision_absent": round(_accuracy(absent), 3),
        "n_absent": len(absent),
        "by_category": by_category_pct,
        "latency_ms_median": latency_ms_median,
        "latency_ms_p95": latency_ms_p95,
        "latency_ms_total": latency_ms_total,
        "cost_usd_total": cost_usd_total,
    }))


if __name__ == "__main__":
    main()
