"""End-to-end check of judge.py against the two fixtures.

Runs the real judge, through the real browser, on a page that should pass every
scored family and one that should fail every scored family. Needs Node, the
`check/` install, and a Chrome — it is slow and it is the only test that proves
anything.

    python3 tests/test_judge.py        # or: pytest tests/test_judge.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent
BASELINE = ["case_01", "case_05"]      # same checks, different brief
ANTI_DEFAULT = "case_03"               # counterfactual lever


def run_judge(html: str, case_id: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        run = Path(td)
        (run / "stdout.txt").write_text(html, encoding="utf-8")
        (run / "meta.json").write_text(json.dumps({"exit_code": 0}))
        manifest = {
            "run": {"stdout": str(run / "stdout.txt"), "meta": str(run / "meta.json")},
            "expected_dir": str(TASK / "expected" / case_id),
            "inputs_dir": str(TASK / "inputs" / "case_01"),
            "output_dir": str(run / "artifacts"),
        }
        proc = subprocess.run(
            [sys.executable, "judge.py"], cwd=TASK, capture_output=True, text=True,
            env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)},
        )
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        out["_artifacts_written"] = sorted(p.name for p in (run / "artifacts").glob("*"))
        return out


def test_fixtures_separate() -> None:
    good = (TASK / "fixtures" / "good.html").read_text()
    broken = (TASK / "fixtures" / "broken.html").read_text()

    for case_id in BASELINE:
        g = run_judge(good, case_id)
        b = run_judge(broken, case_id)
        print(f"{case_id:9s} good={g['score']}  broken={b['score']}   "
              f"broken_reason={b['failure_reason']}")
        assert g["score"] == 1.0, f"{case_id}: good fixture scored {g['score']} — {g['failure_reason']}"
        assert b["score"] == 0.0, f"{case_id}: broken fixture scored {b['score']}"
        assert "render.png" in g["_artifacts_written"], "no screenshot written"
        assert "rects.json" in g["_artifacts_written"], "no rects written"

    # the diagnostic families must be populated but must not have moved score
    g = run_judge(good, "case_01")
    b = run_judge(broken, "case_01")
    assert b["contrast_violations"] > 0 and g["contrast_violations"] == 0
    print(f"diagnostics  good contrast={g['contrast_violations']}  "
          f"broken contrast={b['contrast_violations']}")


def test_anti_default_case() -> None:
    """case_04 carries the counterfactual + prohibition levers.

    The two pages built to the plain brief must fail it — that failure is the
    lever working, not a bug.
    """
    cf = (TASK / "fixtures" / "counterfactual.html").read_text()
    plain = (TASK / "fixtures" / "good.html").read_text()
    a = run_judge(cf, ANTI_DEFAULT)
    b = run_judge(plain, ANTI_DEFAULT)
    print(f"{ANTI_DEFAULT:9s} counterfactual={a['score']}  plain-good={b['score']}   "
          f"plain_reason={b['failure_reason']}")
    assert a["score"] == 1.0, f"counterfactual fixture failed: {a['failure_reason']}"
    assert b["score"] == 0.0, "a default-shaped page passed the anti-default brief"


def test_walker_reaches_later_steps() -> None:
    """A three-step form must be captured three times, not once.

    `fixtures/wizard.html` puts steps 2 and 3 outside the DOM until step 1
    validates — the shape that made the open form briefs unjudgeable from a
    screenshot. If the walker regresses, states_captured drops to 1 and any
    judge reading these images is reading a third of the page.
    """
    wiz = (TASK / "fixtures" / "wizard.html").read_text()
    r = run_judge(wiz, "case_09")
    print(f"wizard      states_captured={r['states_captured']} floor={r['floor_passed']}")
    assert r["states_captured"] >= 3, f"walker stalled at {r['states_captured']} state(s)"
    assert len(r["artifacts"]["screens"]) >= 3


def test_garbage_input_scores_zero() -> None:
    r = run_judge("I could not complete this task.", "case_01")
    assert r["score"] == 0.0 and r["failure_reason"] == "no_html"
    print(f"no-html     score={r['score']} reason={r['failure_reason']}")


if __name__ == "__main__":
    test_fixtures_separate()
    test_anti_default_case()
    test_walker_reaches_later_steps()
    test_garbage_input_scores_zero()
    print("\nall passed")
