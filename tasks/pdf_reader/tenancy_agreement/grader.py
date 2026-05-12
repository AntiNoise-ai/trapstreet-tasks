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

    # Break out accuracy by tag-derived buckets if the judge surfaced them in expected metadata.
    # We don't have direct access to tags here, but the judge's "expected" metadata works as a proxy.
    by_category: Counter[str] = Counter()
    by_category_total: Counter[str] = Counter()
    for c in scored:
        cat = (c["metrics"].get("category")
               or c["metrics"].get("expected", {}).get("category") if isinstance(c["metrics"].get("expected"), dict)
               else None)
        if cat:
            by_category_total[cat] += 1
            by_category[cat] += c["metrics"]["score"]

    by_category_pct = {k: round(by_category[k] / by_category_total[k], 3) for k in by_category_total}

    passed = bool(scored) and accuracy >= PASS_THRESHOLD

    print(json.dumps({
        "passed": passed,
        "score": round(accuracy, 3),
        "n_total": len(cases),
        "n_scored": len(scored),
        "n_skipped_no_gold": len(skipped),
        "threshold": PASS_THRESHOLD,
        "by_category": by_category_pct,
    }))


if __name__ == "__main__":
    main()
