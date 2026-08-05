"""Re-score completed tp runs from their stored solution output.

Run:  python3 rescore_runs.py <solution-variant-dir> [<dir> ...]

Every case directory under .trap/runs/ keeps the solution's raw stdout and its
exit code, so a judge change can be applied to runs that already happened
without spending anything on new API calls. Writes `report.rescored.json`
alongside each `report.json`; `analyze_runs.py` prefers the rescored file when
it is present. The original report is never modified -- trap-cli's own
artifact stays exactly as it was produced.

Why this exists: the judge gained a fairness fix (a clock-time expectation is
satisfied by a full ISO-8601 timestamp carrying the same hour and minute)
partway through the run matrix. Mixing pre-fix and post-fix scores across
passes of the same variant would put a scoring change inside the measurement,
which is precisely the kind of artifact this task is built to avoid. Re-scoring
every pass with the final judge makes the comparison uniform.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from judge import score_case  # noqa: E402

EXPECTED_DIR = HERE / "expected"


def breakdown(scored: list[dict], field: str) -> dict:
    total: Counter = Counter()
    got: Counter = Counter()
    for m in scored:
        key = m.get(field)
        if key is None:
            continue
        total[str(key)] += 1
        got[str(key)] += m["score"]
    return {k: round(got[k] / total[k], 3) for k in sorted(total, key=str)}


def rescore_run(run_dir: Path) -> dict | None:
    metrics: list[dict] = []
    for case_dir in sorted(run_dir.glob("case_*")):
        stdout_p = case_dir / "solution" / "stdout"
        meta_p = case_dir / "solution" / "meta.json"
        exp_p = EXPECTED_DIR / case_dir.name / "answer.json"
        if not (stdout_p.exists() and meta_p.exists() and exp_p.exists()):
            continue

        expected = json.loads(exp_p.read_text())
        exit_code = json.loads(meta_p.read_text()).get("exit_code", 0)
        stdout = stdout_p.read_text()

        base = {
            "id": expected["id"], "n_tools": expected["n_tools"],
            "position": expected["position"], "ambiguity": expected["ambiguity"],
            "intent": expected["intent"], "category": expected["category"],
        }
        if exit_code != 0:
            m = {"score": 0.0, "reason": f"solution exited {exit_code}",
                 "failure_mode": "solution_error"}
        elif not stdout.strip():
            m = {"score": 0.0, "reason": "agent produced no output",
                 "failure_mode": "solution_error"}
        else:
            m = score_case(stdout, expected)
        metrics.append({**m, **base})

    if not metrics:
        return None

    errored = [m for m in metrics if m.get("failure_mode") == "solution_error"]
    valid = [m for m in metrics if m.get("failure_mode") != "solution_error"]
    return {
        "score": round(sum(m["score"] for m in metrics) / len(metrics), 3),
        "n_passed": sum(1 for m in metrics if m["score"] == 1.0),
        "n_total": len(metrics),
        "n_scored": len(metrics),
        "n_solution_error": len(errored),
        "score_excluding_solution_errors": round(
            sum(m["score"] for m in valid) / len(valid), 3) if valid else 0.0,
        "solution_errors_by_n_tools": dict(Counter(str(m["n_tools"]) for m in errored)),
        "by_ambiguity": breakdown(metrics, "ambiguity"),
        "by_n_tools": breakdown(metrics, "n_tools"),
        "by_position": breakdown(metrics, "position"),
        "by_intent": breakdown(metrics, "intent"),
        "by_category": breakdown(metrics, "category"),
        "failure_modes": dict(Counter(
            m.get("failure_mode") for m in metrics
            if m["score"] == 0.0 and m.get("failure_mode"))),
        "lost_to_near_miss": dict(Counter(
            m.get("called_tool") for m in metrics
            if m["score"] == 0.0 and m.get("failure_mode") == "near_miss").most_common()),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    for arg in sys.argv[1:]:
        variant = Path(arg).resolve()
        runs = sorted(variant.glob(".trap/runs/*/*/*/report.json"))
        if not runs:
            print(f"{variant.name}: no runs found")
            continue
        for report in runs:
            metrics = rescore_run(report.parent)
            if metrics is None:
                print(f"  {report.parent.name}: no case outputs, skipped")
                continue
            old = json.loads(report.read_text()).get("grader_metrics", {}).get("score")
            out = report.parent / "report.rescored.json"
            out.write_text(json.dumps({"grader_metrics": metrics}, indent=2) + "\n")
            delta = "" if old is None else f"  (was {old:.3f})"
            print(f"  {variant.name}/{report.parent.name}: {metrics['score']:.3f}{delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
