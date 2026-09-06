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
        dc = b.get("deciding_checks") or {}
        print(f"{case_id:9s} good={g['score']}  broken={b['score']} "
              f"({dc.get('passed')}/{dc.get('total')})  reason={b['failure_reason']}")
        assert g["score"] == 1.0, f"{case_id}: good fixture scored {g['score']} — {g['failure_reason']}"
        # Dense scoring: the broken fixture fails some checks, not all, so the
        # assertion is separation rather than a clean zero. A hard 0.0 here would
        # only mean the fixture happens to fail everything in the family.
        assert b["score"] < g["score"], f"{case_id}: broken {b['score']} !< good {g['score']}"
        assert b["score"] < 1.0, f"{case_id}: broken fixture scored {b['score']}"
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
    assert b["score"] < 1.0, "a default-shaped page passed the anti-default brief"
    assert b["score"] < a["score"], "the counterfactual lever did not separate"


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


def test_generated_payloads_are_harder_than_the_written_ones() -> None:
    """The generated family must be able to fail a page the written one passes.

    This is the point of the generator and it is worth a regression test: the
    thirteen hand-written payloads were taken 13/13 by three frontier arms, and
    the first generated run found a live XSS in this repo's own `good.html`
    (an `<img onerror>` in a plan name executed). A generator whose payloads all
    pass everything has silently reverted to a written list.
    """
    good = (TASK / "fixtures" / "good.html").read_text()
    broken = (TASK / "fixtures" / "broken.html").read_text()
    g = run_judge(good, "case_06")
    b = run_judge(broken, "case_06")
    gd, bd = g.get("deciding_checks") or {}, b.get("deciding_checks") or {}
    print(f"case_06    good={g['score']:.3f} ({gd.get('passed')}/{gd.get('total')})  "
          f"broken={b['score']:.3f} ({bd.get('passed')}/{bd.get('total')})")
    assert gd.get("total", 0) >= 40, f"only {gd.get('total')} variants ran — the generator is not wired in"
    assert b["score"] < g["score"], "the hostile-data family does not separate the fixtures"


def test_budget_separates_a_working_page_from_an_overbuilt_one() -> None:
    """A page that works and a page that works *and* stays inside a ceiling.

    `fixtures/overbuilt.html` is real model output from the 2026-09-06 run — it
    passes every behaviour check and misses all three budget limits (119 nodes,
    59 CSS rules, 13,231 bytes against 70 / 42 / 10,500). It is here because the
    hand-written fixtures are far too small to exercise a budget, so without it
    the check would look like it works while never having fired.
    """
    good = (TASK / "fixtures" / "good.html").read_text()
    fat = (TASK / "fixtures" / "overbuilt.html").read_text()
    g = run_judge(good, "case_10")
    o = run_judge(fat, "case_10")
    od = o.get("deciding_checks") or {}
    print(f"case_10    good={g['score']:.2f}  overbuilt={o['score']:.2f} "
          f"({od.get('passed')}/{od.get('total')})  {o['failure_reason']}")
    assert g["score"] == 1.0, f"lean fixture failed the budget: {g['failure_reason']}"
    assert o["score"] < 1.0, "an over-built page cleared the budget"


def test_garbage_input_scores_zero() -> None:
    r = run_judge("I could not complete this task.", "case_01")
    assert r["score"] == 0.0 and r["failure_reason"] == "no_html"
    print(f"no-html     score={r['score']} reason={r['failure_reason']}")


if __name__ == "__main__":
    test_fixtures_separate()
    test_anti_default_case()
    test_walker_reaches_later_steps()
    test_generated_payloads_are_harder_than_the_written_ones()
    test_budget_separates_a_working_page_from_an_overbuilt_one()
    test_garbage_input_scores_zero()
    print("\nall passed")
