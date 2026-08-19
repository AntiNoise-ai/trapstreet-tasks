"""Run-level grader for the obtain_diamond task.

Aggregates per-case judge metrics into a run verdict. Matches the trapstreet CLI
contract (see cli/examples): reads `TRAPTASK_MANIFEST` = a JSON list of case
results, each with `metrics` (the judge's output). Prints `{passed, score, ...}`.
"""
from __future__ import annotations

import json
import os


def main() -> None:
    results = json.loads(os.environ["TRAPTASK_MANIFEST"])
    if not results:
        print(json.dumps({"passed": True, "score": 1.0}))
        return

    scores = [
        r["metrics"]["score"]
        for r in results
        if r.get("metrics") and r["metrics"].get("score") is not None
    ]
    avg = sum(scores) / len(scores) if scores else 0.0
    passed = bool(scores) and all(s == 1.0 for s in scores)

    print(json.dumps({
        "passed": passed,
        "score": round(avg, 3),
        "n_total": len(results),
        "n_passed": sum(1 for s in scores if s == 1.0),
    }))


if __name__ == "__main__":
    main()
