"""Overall grader for the love_or_fifty_million task.

Aggregates the single case into a run-level verdict. Shape matches the other
tasks: score, n_passed/scored, latency, cost, by_category. With one binary case
the run score is 1.0 (committed) or 0.0 (hedged) and nothing in between — that
is the intended two-value board, not a bug.

"""
from __future__ import annotations

import json
import os
from collections import Counter

PASS_THRESHOLD = 0.80


def case_cost_usd(case: dict) -> float | None:
    """Per-case spend in USD, or None when nothing measured it.

    Preferred source is trap's own cost proxy, which lands on the case as
    `cost.cost_usd`. It only intercepts Anthropic / OpenAI / Mistral / Moonshot,
    though, and most of this task's models run through OpenRouter — so fall back
    to the `usd_cost` the judge surfaces from the solution's own usage.json.
    """
    cost = case.get("cost")
    if isinstance(cost, dict) and cost.get("cost_usd") is not None:
        return cost["cost_usd"]
    metrics = case.get("metrics")
    if isinstance(metrics, dict):
        return metrics.get("usd_cost")
    return None


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_MANIFEST"])

    scored = [c for c in cases if c.get("metrics") and c["metrics"].get("score") is not None]
    skipped = [c for c in cases if not c.get("metrics") or c["metrics"].get("score") is None]

    accuracy = sum(c["metrics"]["score"] for c in scored) / len(scored) if scored else 0.0
    n_passed = sum(1 for c in scored if c["metrics"]["score"] == 1.0)

    # By-category breakdown
    by_cat_score: Counter[str] = Counter()
    by_cat_total: Counter[str] = Counter()
    for c in scored:
        cat = c["metrics"].get("category")
        if cat:
            by_cat_total[cat] += 1
            by_cat_score[cat] += c["metrics"]["score"]
    by_category_pct = {
        k: round(by_cat_score[k] / by_cat_total[k], 3) for k in by_cat_total
    }

    # Latency stats from trap-captured per-case duration
    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    if durations:
        ds = sorted(durations)
        latency_ms_median = round(ds[len(ds) // 2] * 1000, 1)
        latency_ms_p95 = round(ds[int(0.95 * len(ds))] * 1000, 1) if len(ds) > 1 else latency_ms_median
        latency_ms_total = round(sum(ds) * 1000, 1)
    else:
        latency_ms_median = latency_ms_p95 = latency_ms_total = 0.0

    # Cost per case, from trap's proxy where it reaches, else the solution's usage.json
    case_costs = [case_cost_usd(c) for c in cases]
    cost_usd_total = (
        round(sum(x for x in case_costs if x is not None), 6)
        if any(x is not None for x in case_costs)
        else None
    )

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
