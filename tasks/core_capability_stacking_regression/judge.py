"""Per-case judge for core_capability_stacking_regression.

Deterministic, no LLM-as-judge. A scenario needs a SET of tool calls, so the
case is scored as a set-retrieval problem:

    completion  = recall    -- how many required calls arrived
    correctness = precision -- how many emitted calls were right
    score       = F1 of the two

Separating completion from correctness is the split the degradation metric is
built on: a stacked catalog can make a workflow fail by dropping a step
(recall falls) or by substituting a plausible neighbour for the right skill
(precision falls), and those are different failures needing different fixes.

Precision is also the anti-shotgun defence, and it is a property of the
scoring rather than a rule about answer shape: emitting every plausible skill
to catch the right one collapses the score by construction. There is no cap on
answer length, no positional rule, and no required phrasing -- five successive
rules of that kind in another task each rejected an answer that was entirely
correct.

Failure reasons separate four mechanisms that all look like "score went down":
substituting a confusable neighbour (`near_miss`), doing the job through a
redundant but organisationally wrong backend (`wrong_backend`), obeying an
installed skill's standing guidance the request never asked for
(`instruction_bleed`), and volunteering an extra call unprompted --
`unsolicited_addition` when the surplus skill was newly installed,
`over_eager` when it was in the base set all along and therefore present in
both arms. They need different fixes, and only the first is semantic confusion
at selection time.

Order is not scored. Argument matching is deliberately generous and is reused
verbatim from core_tool_selection_at_scale, where it already absorbed three
corrections found by real runs (a clock time expected against a full ISO-8601
timestamp, a stringified list, and path-like arguments compared on their final
component).

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

# A model may name the argument bag any of these; rejecting a correct call over
# the key it arrived under would measure serialisation, not skill selection.
ARG_KEYS = ("arguments", "args", "parameters", "params", "input")


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
    for open_c, close_c in (("[", "]"), ("{", "}")):
        start, end = s.find(open_c), s.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start:end + 1])
            except (json.JSONDecodeError, RecursionError, ValueError):
                continue
    return None


def extract_calls(parsed: Any) -> list[dict]:
    """Normalise into a list of call dicts. A lone dict is accepted as a
    one-call answer; non-dict entries in the list are ignored rather than
    assumed to have the right shape."""
    if isinstance(parsed, dict):
        for key in ("calls", "tool_calls", "actions"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
        else:
            parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    return [c for c in parsed if isinstance(c, dict) and isinstance(c.get("name"), str)]


def call_args(call: dict) -> dict:
    for key in ARG_KEYS:
        val = call.get(key)
        if isinstance(val, dict):
            return val
    return {}


def _is_finite_number(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    return isinstance(x, (int, float)) and math.isfinite(x)


def _norm(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x)).strip().lower()


TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")


def _as_time(x: Any) -> tuple[int, int] | None:
    if not isinstance(x, str):
        return None
    m = TIME_RE.search(x)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _as_seq(x: Any) -> list | None:
    """Normalise a list-ish value into a sorted list of normalised strings.
    Accepts a real list, a delimited string, or a stringified list repr."""
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
    """got matches if it equals ANY accepted value, tolerating int/float and
    numeric-string equivalence, case/whitespace, list ordering, and
    list-vs-delimited-string."""
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
            if isinstance(got, list) and len(got) == 1 and _norm(got[0]) == _norm(want):
                return True
            want_t = _as_time(want)
            if want_t is not None and _as_time(got) == want_t:
                return True
            if "/" in str(want) or "/" in str(got):
                lw, lg = _last_segment(want), _last_segment(got)
                if lw and lg and lw == lg:
                    return True
    return False


def call_satisfies(call: dict, required: dict) -> bool:
    if call.get("name") != required["name"]:
        return False
    got = call_args(call)
    return all(
        arg in got and value_matches(got[arg], accepted)
        for arg, accepted in required["expected_args"].items()
    )


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    required = expected.get("required_calls") or []
    added = set(expected.get("added_names") or [])
    base = set(expected.get("base_names") or [])
    bleed = set(expected.get("bleed_names") or [])
    bleed_strength = expected.get("bleed_strength") or {}
    backend = set(expected.get("backend_names") or [])
    shared: dict[str, Any] = {
        "scenario": expected.get("scenario"),
        "difficulty": expected.get("difficulty"),
        "stack_level": expected.get("stack_level"),
        "overlap_class": expected.get("overlap_class"),
        "n_skills": expected.get("n_skills"),
        "n_competitors": expected.get("n_competitors"),
        "n_required": len(required),
    }

    if not required:
        # Defensive only -- build_cases.py refuses to render a scenario with
        # fewer than two required calls, so this cannot fire on a built case.
        # It exists so a malformed answer.json degrades to a legible verdict
        # rather than a judge crash, which reads as broken infrastructure
        # rather than as the authoring mistake it actually is.
        return {**shared, "score": 0.0, "completion": 0.0, "correctness": 0.0,
                "failure_reason": "no_gold",
                "reason": "expected/answer.json carries no required_calls"}

    parsed = safe_json_loads(stdout)
    calls = extract_calls(parsed)
    if not calls:
        return {**shared, "score": 0.0, "completion": 0.0, "correctness": 0.0,
                "failure_reason": "unparseable",
                "reason": "no tool call could be read from the output"}

    emitted_names = [c["name"] for c in calls]

    # Each emitted call may satisfy at most one required call. Required names
    # are unique within a scenario (build_cases.py asserts it), so first-match
    # is exact rather than a greedy approximation.
    unused = list(range(len(calls)))
    matched, missing = [], []
    for req in required:
        hit = next((i for i in unused if call_satisfies(calls[i], req)), None)
        if hit is None:
            missing.append(req["name"])
        else:
            unused.remove(hit)
            matched.append(req["name"])

    n_matched = len(matched)
    completion = n_matched / len(required)
    correctness = n_matched / len(calls)
    score = (2 * completion * correctness / (completion + correctness)) if n_matched else 0.0

    extra = [emitted_names[i] for i in unused]
    if score == 1.0:
        failure_reason = None
    elif completion == 1.0 and extra and all(n in bleed for n in extra):
        # The job was done correctly and the ONLY surplus calls are skills whose
        # own published guidance told the agent to fire them. This is
        # interference at the instruction level rather than the selection level
        # -- "installing a skill broke my agent" -- and it is a mechanism the
        # first version of this task could not express at all. It is separated
        # from unsolicited_addition because the cause differs: here the model
        # followed an installed skill's standing advice over the user's actual
        # request, rather than volunteering on its own initiative.
        failure_reason = "instruction_bleed"
    elif completion == 1.0 and extra and all(n in added for n in extra):
        # Every required call arrived AND every surplus call is a newly
        # installed skill: the model did the job and then volunteered more,
        # rather than mistaking one skill for another. This must be kept
        # separate from `near_miss`, because it is a different mechanism with
        # a nasty property -- the surplus skill exists ONLY in the high-overlap
        # arm, so a model that helpfully shares the copy it correctly made
        # takes a precision hit that is impossible in the low arm. That is a
        # discordant pair produced by eagerness, not by confusion, and a run
        # that leans on it must not be narrated as "the workflow broke".
        failure_reason = "unsolicited_addition"
    elif any(n in backend for n in extra):
        # A redundant backend that genuinely performs the action, ruled out only
        # by the house rules. Nothing in its own description is wrong, so this
        # is not a semantic confusion -- it is the job done through the wrong
        # system, which is a large share of what practitioners report.
        failure_reason = "wrong_backend"
    elif any(n in added for n in extra):
        failure_reason = "near_miss"
    elif any(n not in base and n not in added for n in extra):
        failure_reason = "unrelated_tool"
    elif any(n in {r["name"] for r in required} for n in extra):
        failure_reason = "bad_arguments"
    elif completion == 1.0 and extra:
        # Every required call arrived and the surplus is base skills, present in
        # both arms. Arm-neutral over-eagerness: real, worth counting, but it
        # cannot produce the arm difference that instruction_bleed does.
        failure_reason = "over_eager"
    else:
        failure_reason = "incomplete"

    return {
        **shared,
        "score": round(score, 4),
        "completion": round(completion, 4),
        "correctness": round(correctness, 4),
        "failure_reason": failure_reason,
        "n_emitted": len(calls),
        "bled_strengths": sorted({bleed_strength[n] for n in extra if n in bleed_strength}),
        "matched_calls": matched,
        "missing_calls": missing,
        "extra_calls": extra,
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    shared = {
        "scenario": expected.get("scenario"),
        "difficulty": expected.get("difficulty"),
        "stack_level": expected.get("stack_level"),
        "overlap_class": expected.get("overlap_class"),
    }
    if exit_code != 0:
        print(json.dumps({**shared, "score": 0.0, "completion": 0.0, "correctness": 0.0,
                          "failure_reason": "solution_error",
                          "reason": f"solution exited {exit_code}"}))
        return
    if not stdout.strip():
        print(json.dumps({**shared, "score": 0.0, "completion": 0.0, "correctness": 0.0,
                          "failure_reason": "solution_error",
                          "reason": "agent produced no output"}))
        return

    print(json.dumps(score_case(stdout, expected)))


if __name__ == "__main__":
    main()
