"""Per-case judge for core_tool_selection_under_load.

Deterministic, no LLM-as-judge: score 1.0 iff the solution calls the single
correct tool with all expected arguments present and matching an accepted
value, 0.0 otherwise. No partial credit -- there's no orderable notion of
"progress" for picking one tool out of a catalog, so binary is the right
call per scoring-design.md.

Anti-shotgun: if the solution's output is a JSON array (multiple tool
calls), only the FIRST element is scored. A solution cannot call every
plausible tool "just in case" and get credit for whichever one is right.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli). See
references/traptask-contract.md for the exact manifest shape.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def strip_fences(s: str) -> str:
    return FENCE_RE.sub("", s).strip()


def safe_json_loads(s: str) -> Any:
    """Parse JSON, tolerating markdown fences and surrounding prose. Returns
    None (never raises) on anything that isn't parseable -- malformed output
    must degrade to a clean miss, not crash the judge."""
    s = strip_fences(s.strip())
    try:
        return json.loads(s)
    except (json.JSONDecodeError, RecursionError, ValueError):
        pass
    # Last resort: find the first {...} or [...] span and try that.
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = s.find(open_c)
        end = s.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start:end + 1])
            except (json.JSONDecodeError, RecursionError, ValueError):
                continue
    return None


def extract_call(parsed: Any) -> dict | None:
    """Anti-shotgun: if parsed is a list, only the first element counts.
    Returns a dict with the tool call, or None if the shape is unusable."""
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _is_finite_number(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return math.isfinite(x)
    return False


def _normalise_str(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def value_matches(got: Any, accepted: list) -> bool:
    """got matches if it equals ANY accepted value, tolerant of
    int/float/numeric-string equivalence and case/whitespace for strings."""
    for want in accepted:
        if _is_finite_number(want) and _is_finite_number(got):
            if math.isclose(float(got), float(want), rel_tol=1e-6, abs_tol=1e-6):
                return True
            continue
        if _is_finite_number(want) and isinstance(got, str):
            # numeric target, string-shaped answer e.g. "84.50" / "$84.50"
            cleaned = re.sub(r"[^0-9.\-]", "", got)
            try:
                if cleaned and math.isclose(float(cleaned), float(want), rel_tol=1e-6, abs_tol=1e-6):
                    return True
            except ValueError:
                pass
            continue
        if isinstance(want, str) and isinstance(got, (str, int, float)) and not isinstance(got, bool):
            if _normalise_str(got) == _normalise_str(want):
                return True
    return False


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    """Compare `stdout` (the solution's raw stdout) against `expected` (the
    parsed contents of expected/<id>/answer.json)."""
    parsed = safe_json_loads(stdout)
    if parsed is None:
        return {"score": 0.0, "reason": "output is not parseable JSON"}

    call = extract_call(parsed)
    if call is None:
        return {"score": 0.0, "reason": "no usable tool-call object found in output"}

    name = call.get("name") or call.get("tool_name")
    if not isinstance(name, str):
        return {"score": 0.0, "reason": "missing or non-string tool name"}

    args = call.get("arguments")
    if args is None:
        args = call.get("args")
    if not isinstance(args, dict):
        return {"score": 0.0, "reason": "arguments field missing or not an object", "called_tool": name}

    correct_name = expected["correct_tool_name"]
    if name != correct_name:
        return {
            "score": 0.0,
            "reason": f"wrong tool: called {name!r}, expected {correct_name!r}",
            "called_tool": name,
        }

    expected_args: dict[str, list] = expected["expected_args"]
    arg_results = {}
    all_ok = True
    for arg_name, accepted in expected_args.items():
        got = args.get(arg_name)
        ok = got is not None and value_matches(got, accepted)
        arg_results[arg_name] = {"got": got, "ok": ok}
        if not ok:
            all_ok = False

    return {
        "score": 1.0 if all_ok else 0.0,
        "reason": "correct tool + arguments" if all_ok else "correct tool, argument mismatch",
        "called_tool": name,
        "arg_results": arg_results,
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    base = {
        "id": expected.get("id"),
        "n_tools": expected.get("n_tools"),
        "position": expected.get("position"),
        "category": expected.get("category"),
    }

    if exit_code != 0:
        print(json.dumps({**base, "score": 0.0, "reason": f"solution exited {exit_code}",
                           "agent_output": stdout.strip()[:500]}))
        return

    if not stdout.strip():
        print(json.dumps({**base, "score": 0.0, "reason": "agent produced no output",
                           "agent_output": ""}))
        return

    metrics = score_case(stdout, expected)
    metrics.update(base)
    metrics["agent_output"] = stdout.strip()[:500]
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
