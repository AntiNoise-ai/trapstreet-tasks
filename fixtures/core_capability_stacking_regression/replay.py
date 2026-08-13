#!/usr/bin/env python3
"""Replay frozen model outputs through the task's judge and grader.

Edit `judge.py` (or `grader.py`), run this, read the numbers. No models are
called, no API key is needed, and the whole thing takes a couple of seconds --
so a scoring change can be evaluated as fast as it can be typed.

    python3 replay.py                       # default fixture
    python3 replay.py --model claude-haiku-4-5
    python3 replay.py --json                # full grader output, unabridged

The outputs under `outputs/<model>/` are one real run's stdout, one file per
case, exactly as the solution printed it. `exit_codes.json` carries each case's
exit code so `solution_error` handling stays reachable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent.parent / "tasks" / "core_capability_stacking_regression"


def run(script: Path, manifest, cwd: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(script)],
        env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)},
        cwd=cwd, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"{script.name} exited {proc.returncode}\n{proc.stderr}")
    return proc.stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--json", action="store_true", help="print the full grader output")
    args = ap.parse_args()

    out_dir = HERE / "outputs" / args.model
    if not out_dir.is_dir():
        avail = ", ".join(sorted(p.name for p in (HERE / "outputs").iterdir())) or "none"
        sys.exit(f"no fixture for {args.model!r} (have: {avail})")

    exit_codes = json.loads((out_dir / "exit_codes.json").read_text())
    cases = sorted(p.stem for p in out_dir.glob("case_*.txt"))
    if not cases:
        sys.exit(f"no case outputs in {out_dir}")

    scored = []
    with tempfile.TemporaryDirectory() as tmp:
        meta_path = Path(tmp) / "meta.json"
        for case_id in cases:
            meta_path.write_text(json.dumps({"exit_code": exit_codes.get(case_id, 0)}))
            metrics = run(TASK / "judge.py", {
                "run": {"stdout": str(out_dir / f"{case_id}.txt"), "meta": str(meta_path)},
                "expected_dir": str(TASK / "expected" / case_id),
            }, cwd=TASK)
            scored.append({"case_id": case_id, "metrics": json.loads(metrics)})

    report = json.loads(run(TASK / "grader.py", scored, cwd=TASK))

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"{args.model} -- {len(scored)} cases replayed\n")
    for k in ("score", "primary_p", "arm_gap", "high_overlap_score", "low_overlap_score"):
        if k in report:
            print(f"  {k:22s} {report[k]}")
    for k in ("by_overlap_class", "curve_high_overlap", "by_failure_reason"):
        if k in report:
            print(f"\n  {k}\n    {json.dumps(report[k])}")
    print("\n(--json for everything else)")


if __name__ == "__main__":
    main()
