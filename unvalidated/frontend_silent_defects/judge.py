"""Per-case judge for frontend_silent_defects.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli).

The solution prints one self-contained HTML page to stdout. This judge writes
it to disk, hands it to check/inspect.mjs (real Chromium), and turns the
report into one score.

What decides the score, and what does not
-----------------------------------------
Scored:      behaviour · robustness · responsive · constraints
Diagnostic:  contrast · naming (axe-core)

The split is deliberate and it is the whole design. A contrast or missing-label
failure is fixed by running a checker before returning — one bolt-on step, and
every tool can copy it the week it sees this board. Behaviour and robustness
have no such step: a dropdown that does not close, or a layout that folds on a
240-character plan name, is fixed by building it right. So the a11y families
ride along as public columns (they are worth seeing) but never move `score`.

`expected/<case>/answer.json` names which family decides the case, so one
generated page can be scored from several angles as several cases. A case whose
category is `open` is scored by nothing at all — see OPEN_FAMILIES.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSPECT = HERE / "check" / "inspect.mjs"

SCORED_FAMILIES = {"behaviour", "robustness", "responsive", "constraints"}

# Open briefs. These run everything and are scored by nothing: `score` is null,
# the contract's escape hatch for "a whole case worth observing but not ranking".
# There is no gold that settles whether a landing page is good — inventing one
# would be a number I could not defend. The floor still runs and is reported as
# `floor_passed`; the reading lives in the gallery, and in a human's eye.
OPEN_FAMILIES = {"open"}


def extract_html(stdout: str) -> str | None:
    """Pull the page out of whatever the agent printed around it."""
    s = stdout.strip()
    m = re.search(r"```(?:html)?\s*(.*?)```", s, re.DOTALL | re.IGNORECASE)
    if m:
        s = m.group(1).strip()
    lo = s.lower()
    for opener in ("<!doctype html", "<html"):
        i = lo.find(opener)
        if i != -1:
            return s[i:]
    return s if "<" in s and ">" in s else None


def run_inspector(html: str, spec: dict, out_dir: Path) -> dict:
    with tempfile.TemporaryDirectory() as td:
        page = Path(td) / "page.html"
        page.write_text(html, encoding="utf-8")
        spec_path = Path(td) / "spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        proc = subprocess.run(
            ["node", str(INSPECT), str(page), str(spec_path), str(out_dir)],
            capture_output=True, text=True, timeout=180,
        )
    if proc.returncode != 0:
        return {"loaded": False, "error": f"inspector exited {proc.returncode}: {proc.stderr[-300:]}"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"loaded": False, "error": f"inspector emitted non-JSON: {proc.stdout[:200]}"}


def grade(report: dict, family: str, spec: dict) -> tuple[float, str | None]:
    """1.0 only if every check in the deciding family passed."""
    if not report.get("loaded"):
        return 0.0, report.get("error") or "page did not load"

    fam = report.get("families", {})
    if family == "behaviour":
        checks = fam.get("behaviour") or []
        if not checks:
            return 0.0, "no behaviour assertions ran"
        bad = [c for c in checks if not c["ok"]]
        return (0.0, bad[0]["why"]) if bad else (1.0, None)

    if family == "constraints":
        checks = fam.get("constraints") or []
        if not checks:
            return 0.0, "no constraint checks ran"
        bad = [c for c in checks if not c["ok"]]
        return (0.0, f"{bad[0]['name']}: {bad[0]['why']}") if bad else (1.0, None)

    if family == "robustness":
        checks = fam.get("robustness") or []
        if not checks:
            return 0.0, "no robustness variants ran"
        bad = [c for c in checks if not c["ok"]]
        return (0.0, f"{bad[0]['name']}: {bad[0]['why']}") if bad else (1.0, None)

    if family == "responsive":
        r = fam.get("responsive") or {}
        want = spec.get("responsive") or {}
        width = want.get("width", 375)
        tol = want.get("max_overflow_px", 1)
        if r.get("width") != width:
            return 0.0, f"inspector measured {r.get('width')}px, case wants {width}px"
        over = r.get("overflow", 0)
        if over > tol:
            top = (r.get("culprits") or [{}])[0]
            return 0.0, f"overflows {width}px by {over}px (worst: <{top.get('tag','?')}> {top.get('over','?')}px)"
        return 1.0, None

    return 0.0, f"unknown scored family {family!r}"


def _floor(report: dict, spec: dict) -> tuple[bool, str | None]:
    """The only bar an open brief has to clear: it loads, it does not throw, it
    does not reach off the page, and it survives 375px."""
    if not report.get("loaded"):
        return False, report.get("error") or "page did not load"
    fams = report.get("families", {}) or {}
    if report.get("console_errors"):
        return False, f"threw: {report['console_errors'][0]}"
    bad = [c for c in (fams.get("constraints") or []) if not c["ok"]]
    if bad:
        return False, f"{bad[0]['name']}: {bad[0]['why']}"
    over = (fams.get("responsive") or {}).get("overflow", 0)
    if over > spec.get("responsive", {}).get("max_overflow_px", 1):
        return False, f"overflows 375px by {over}px"
    return True, None


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text(encoding="utf-8", errors="replace")
    meta = json.loads(Path(m["run"]["meta"]).read_text())
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())
    out_dir = Path(m.get("output_dir") or Path(m["run"]["stdout"]).parent / "artifacts")

    base = {"id": expected.get("id"), "category": expected.get("category")}

    if meta.get("exit_code") not in (0, None):
        print(json.dumps({**base, "score": 0.0, "failure_reason": "nonzero_exit", "contract_miss": True,
                          "detail": f"solution exited {meta['exit_code']}"}))
        return

    html = extract_html(stdout)
    if not html:
        print(json.dumps({**base, "score": 0.0, "failure_reason": "no_html", "contract_miss": True,
                          "detail": "stdout contained no HTML document"}))
        return

    family = expected.get("category")
    if family not in SCORED_FAMILIES and family not in OPEN_FAMILIES:
        print(json.dumps({**base, "score": None, "failure_reason": "unscored_family"}))
        return

    report = run_inspector(html, expected.get("spec", {}), out_dir)
    if family in OPEN_FAMILIES:
        floor_ok, floor_why = _floor(report, expected.get("spec", {}))
        score, why = None, None
    else:
        floor_ok, floor_why = None, None
        score, why = grade(report, family, expected.get("spec", {}))

    # The judge panel is deliberately NOT wired in. check/panel.py and its seven
    # anchors are kept as recorded work; they are not called. Run twice over nine
    # pages, the panel failed to reproduce the owner's held-out judgments AND its
    # own anchors — two pages labelled "2" in its prompt came back 3.00 and 2.75.
    # A diagnostic column is published next to real measurements and gets read as
    # information, so an unreliable one is worse than an absent one. See README.

    fams = report.get("families", {}) or {}
    a11y = fams.get("a11y") or {}
    resp = fams.get("responsive") or {}

    # Per-family pass counts. One generation is checked by every family that has
    # a spec, so a probe run reads as a case x family matrix, not one number.
    passed = {}
    for name in ("behaviour", "robustness", "constraints"):
        checks = fams.get(name)
        if checks:
            passed[name] = f"{sum(1 for c in checks if c['ok'])}/{len(checks)}"
    if resp:
        passed["responsive"] = "1/1" if resp.get("overflow", 0) <= 1 else "0/1"

    print(json.dumps({
        **base,
        "score": score,
        "failure_reason": None if score in (1.0, None) else (why or "failed"),
        "floor_passed": floor_ok,
        "floor_failure": floor_why,
        "contract_miss": False,
        "families_passed": passed,
        # diagnostics — public columns, never part of score
        "contrast_violations": a11y.get("contrast_violations"),
        "naming_violations": a11y.get("naming_violations"),
        "overflow_px_375": resp.get("overflow"),
        "console_errors": len(report.get("console_errors") or []),
        "html_bytes": len(html),
        # How many distinct states the walker reached. 1 means the page never
        # advanced — either it is a single screen, or nothing looked like "next".
        "states_captured": len(report.get("screens") or []),
        "artifacts": {
            "screens": [str(out_dir / n)
                        for st in (report.get("screens") or []) for n in st["shots"]],
            "rects": str(out_dir / "rects.json"),
        },
    }))


if __name__ == "__main__":
    main()
