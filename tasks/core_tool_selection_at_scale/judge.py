"""Per-case judge for core_tool_selection_at_scale.

Deterministic, no LLM-as-judge: score 1.0 iff the solution calls the single
correct tool with every expected argument present and matching an accepted
value, 0.0 otherwise. No partial credit -- picking one tool out of a catalog
has no orderable notion of "how close", so binary is the honest model.

Beyond pass/fail this records WHICH tool was called and whether it was one of
the family's five near-misses. "Wrong" is not the interesting datum; "wrong in
the specific way the family was constructed to provoke" is, and it is what
separates a genuine discrimination failure from a parse error or a refusal.

Anti-shotgun: if the output is a JSON array, only the FIRST element is scored.
A solution cannot list every plausible tool and claim credit for whichever one
happens to be right.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli).
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
    """Parse JSON, tolerating fences and surrounding prose. Never raises --
    malformed output must degrade to a clean miss, not crash the judge."""
    s = strip_fences(s.strip())
    try:
        return json.loads(s)
    except (json.JSONDecodeError, RecursionError, ValueError):
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = s.find(open_c), s.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start:end + 1])
            except (json.JSONDecodeError, RecursionError, ValueError):
                continue
    return None


def extract_call(parsed: Any) -> dict | None:
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else None
    return parsed if isinstance(parsed, dict) else None


def _is_finite_number(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    return isinstance(x, (int, float)) and math.isfinite(x)


def _norm(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x)).strip().lower()


TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")


def _as_time(x: Any) -> tuple[int, int] | None:
    """Extract an hour:minute from a string, if one is present."""
    if not isinstance(x, str):
        return None
    m = TIME_RE.search(x)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _as_seq(x: Any) -> list | None:
    """Normalise a list-ish value into a list of normalised strings.

    Accepts a real list, a delimited string like "Priya, Marco", or a
    stringified list like "['Priya', 'Marco']" -- models answering in plain
    text (rather than through a native tool-call parameter) often serialise
    collections as a repr. Rejecting that would penalise the flat-text
    presentation for a serialisation quirk and quietly inflate the very
    degradation this task is measuring.
    """
    if isinstance(x, list):
        return sorted(_norm(i) for i in x)
    if isinstance(x, str):
        s = x.strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        parts = [p.strip().strip("'\"") for p in re.split(r"[,;]", s)]
        parts = [p for p in parts if p]
        if parts:
            return sorted(_norm(p) for p in parts)
    return None


def _last_segment(x: Any) -> str | None:
    """Final component of a path-like string: '/shared/finance' -> 'finance'."""
    if not isinstance(x, str):
        return None
    s = x.strip().rstrip("/")
    return _norm(s.rsplit("/", 1)[-1]) if s else None


def value_matches(got: Any, accepted: list) -> bool:
    """got matches if it equals ANY accepted value. Tolerant of int/float and
    numeric-string equivalence, case/whitespace for strings, and ordering plus
    list-vs-delimited-string for collection arguments.

    Deliberately generous: this task measures which TOOL gets selected, so an
    answer must not fail over `["Priya","Marco"]` vs `"Priya, Marco"`. The
    arguments are checked to confirm the model actually read the request, not
    to test formatting pedantry.
    """
    for want in accepted:
        if isinstance(want, list):
            got_seq, want_seq = _as_seq(got), _as_seq(want)
            if got_seq is not None and want_seq is not None and got_seq == want_seq:
                return True
            continue

        if _is_finite_number(want):
            if _is_finite_number(got) and math.isclose(float(got), float(want), rel_tol=1e-6, abs_tol=1e-6):
                return True
            if isinstance(got, str):
                cleaned = re.sub(r"[^0-9.\-]", "", got)
                try:
                    if cleaned and math.isclose(float(cleaned), float(want), rel_tol=1e-6, abs_tol=1e-6):
                        return True
                except ValueError:
                    pass
            continue

        if isinstance(want, str):
            if isinstance(got, (str, int, float)) and not isinstance(got, bool):
                if _norm(got) == _norm(want):
                    return True
            # single-element list answering a scalar expectation
            if isinstance(got, list) and len(got) == 1 and _norm(got[0]) == _norm(want):
                return True
            # A clock time expected, a full timestamp supplied. The query says
            # "this morning" and gives no date, so a model choosing the
            # schema's ISO-8601 option has to invent one; the hour and minute
            # are the part it could actually get right, and the part that
            # shows it read the request. Compared exactly -- 09:30 never
            # satisfies 09:00. Date-only expectations (e.g. "2025-03-03")
            # don't match TIME_RE and stay strict.
            want_t = _as_time(want)
            if want_t is not None and _as_time(got) == want_t:
                return True

            # Path-like arguments: compare the final component, so 'Finance',
            # '/Finance' and 'folder/Finance' all agree while 'planning' still
            # does not. Naming the right folder with an invented parent is a
            # phrasing difference, not a selection error.
            if "/" in str(want) or "/" in str(got):
                lw, lg = _last_segment(want), _last_segment(got)
                if lw and lg and lw == lg:
                    return True
    return False


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    near_misses = expected.get("near_miss_names", [])

    parsed = safe_json_loads(stdout)
    if parsed is None:
        return {"score": 0.0, "reason": "output is not parseable JSON", "failure_mode": "unparseable"}

    call = extract_call(parsed)
    if call is None:
        return {"score": 0.0, "reason": "no usable tool-call object found", "failure_mode": "unparseable"}

    name = call.get("name") or call.get("tool_name")
    if not isinstance(name, str):
        return {"score": 0.0, "reason": "missing or non-string tool name", "failure_mode": "unparseable"}

    args = call.get("arguments")
    if args is None:
        args = call.get("args")
    if not isinstance(args, dict):
        return {
            "score": 0.0, "reason": "arguments field missing or not an object",
            "called_tool": name, "failure_mode": "unparseable",
        }

    correct_name = expected["correct_tool_name"]
    if name != correct_name:
        # The distinction that matters: did it fall for one of the five tools
        # built to be plausible, or wander off to unrelated filler?
        mode = "near_miss" if name in near_misses else "unrelated_tool"
        return {
            "score": 0.0,
            "reason": f"wrong tool: called {name!r}, expected {correct_name!r}",
            "called_tool": name,
            "failure_mode": mode,
        }

    arg_results = {}
    all_ok = True
    for arg_name, accepted in expected["expected_args"].items():
        got = args.get(arg_name)
        ok = got is not None and value_matches(got, accepted)
        arg_results[arg_name] = {"got": got, "ok": ok}
        if not ok:
            all_ok = False

    return {
        "score": 1.0 if all_ok else 0.0,
        "reason": "correct tool + arguments" if all_ok else "correct tool, argument mismatch",
        "called_tool": name,
        "failure_mode": None if all_ok else "bad_arguments",
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
        "ambiguity": expected.get("ambiguity"),
        "intent": expected.get("intent"),
        "category": expected.get("category"),
    }

    if exit_code != 0:
        print(json.dumps({**base, "score": 0.0, "reason": f"solution exited {exit_code}",
                          "failure_mode": "solution_error", "agent_output": stdout.strip()[:500]}))
        return

    if not stdout.strip():
        print(json.dumps({**base, "score": 0.0, "reason": "agent produced no output",
                          "failure_mode": "solution_error", "agent_output": ""}))
        return

    metrics = score_case(stdout, expected)
    metrics.update(base)
    metrics["agent_output"] = stdout.strip()[:500]
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
