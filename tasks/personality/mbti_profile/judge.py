"""Per-case judge for the personality/mbti_profile task.

The model takes a 32-question Likert MBTI questionnaire. The judge:

  1. Validates format strictly — must be JSON `{"responses": [32 ints 1..5]}`
  2. If valid, computes the MBTI 4-letter type + per-axis percentages
  3. Computes an acquiescence-bias flag (>80% agreement on reverse-coded pairs
     indicates the model is just saying yes to everything; the type is unreliable)

Score: 1.0 if format is valid. 0.0 if not. The derived `mbti_type` and
`percentages` are SURFACED IN METRICS so the leaderboard can show them, but
they are NOT graded — there's no canonical MBTI for an AI.

Reasoning behind format-only grading: the whole point of this task is to
PROFILE each model and compare across the leaderboard. Grading on a canonical
type would assume one exists, which it doesn't. The comparison is the value;
the judge just keeps the comparison apples-to-apples.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def _strip_fences(text: str) -> str:
    """Some LLMs wrap JSON in ```json...```. Strip it."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_output(stdout: str) -> tuple[dict | None, str]:
    s = _strip_fences(stdout)
    if not s:
        return None, "empty stdout"
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        # Last-ditch: find first {...} substring containing "responses"
        m = re.search(r'\{[^{}]*"responses"[^{}]*\[[\s\S]*?\][^{}]*\}', s)
        if m:
            try:
                obj = json.loads(m.group(0))
            except json.JSONDecodeError:
                return None, f"could not parse JSON: {e}"
        else:
            return None, f"could not parse JSON: {e}"
    if not isinstance(obj, dict):
        return None, "top-level output must be a JSON object"
    return obj, ""


def derive_mbti(responses: list[int], scoring_key: list[dict], letters_by_axis: dict[str, list[str]]) -> dict:
    """Sum per-axis contributions. For each question:
      - if response==3: contribution=0 (neutral)
      - if direction==<positive letter of axis>: contribution = response - 3
      - else (negative direction): contribution = 3 - response
    Sum across all 8 questions per axis → range [-16, +16].
    Positive → first letter of axis (E/S/T/J); negative or zero → second (I/N/F/P).
    Percentage of first letter = (sum + 16) / 32 * 100."""
    sums: dict[str, int] = {}
    counts: dict[str, int] = {}
    for q in scoring_key:
        n = q["n"]
        axis = q["axis"]
        direction = q["direction"]
        first_letter = letters_by_axis[axis][0]   # e.g. "E"
        r = responses[n - 1]
        contribution = (r - 3) if direction == first_letter else (3 - r)
        sums[axis] = sums.get(axis, 0) + contribution
        counts[axis] = counts.get(axis, 0) + 1

    type_letters: list[str] = []
    percentages: dict[str, float] = {}
    for axis in ("E_I", "S_N", "T_F", "J_P"):
        max_abs = counts.get(axis, 8) * 2   # each q contributes -2..+2
        s = sums.get(axis, 0)
        # First letter = positive direction; second = negative or zero
        if s > 0:
            type_letters.append(letters_by_axis[axis][0])
        elif s < 0:
            type_letters.append(letters_by_axis[axis][1])
        else:
            # Exact tie — by convention, take the second (more introverted/I-side)
            type_letters.append(letters_by_axis[axis][1])
        # Percentage in favour of FIRST letter
        pct_first = round((s + max_abs) / (2 * max_abs) * 100, 1)
        percentages[axis] = {letters_by_axis[axis][0]: pct_first,
                             letters_by_axis[axis][1]: round(100 - pct_first, 1)}

    return {"mbti_type": "".join(type_letters), "percentages": percentages}


def acquiescence_score(responses: list[int]) -> dict:
    """Flag bias: if model agrees (≥4) with both positive AND its reverse-coded
    pair, that's contradictory. Count contradictions per axis."""
    # Mostly informational. Returns simple stats.
    n = len(responses)
    mean = sum(responses) / n if n else 0
    very_high = sum(1 for r in responses if r >= 4) / n if n else 0
    very_low = sum(1 for r in responses if r <= 2) / n if n else 0
    return {
        "mean_response": round(mean, 2),
        "pct_agree": round(very_high * 100, 1),       # % of 4s and 5s
        "pct_disagree": round(very_low * 100, 1),     # % of 1s and 2s
        "acquiescence_suspected": very_high > 0.80,   # agrees with >80% of items
        "nay_saying_suspected": very_low > 0.80,
    }


def judge_case(stdout: str, expected: dict) -> dict[str, Any]:
    checks: list[dict] = []

    obj, err = _parse_output(stdout)
    if obj is None:
        checks.append({"check": "json_parse", "pass": False, "reason": err})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "json_parse", "pass": True, "reason": "ok"})

    responses = obj.get("responses")
    if not isinstance(responses, list):
        checks.append({"check": "responses_list", "pass": False, "reason": "field 'responses' missing or not a list"})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "responses_list", "pass": True, "reason": "ok"})

    n_expected = expected.get("n_questions", 32)
    if len(responses) != n_expected:
        checks.append({"check": "responses_count", "pass": False,
                       "reason": f"got {len(responses)} responses, expected {n_expected}"})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "responses_count", "pass": True, "reason": f"{n_expected} ok"})

    # All integers 1..5
    invalid: list[tuple[int, Any]] = []
    coerced: list[int] = []
    for i, r in enumerate(responses):
        if isinstance(r, bool):  # bools are ints in Python — explicitly reject
            invalid.append((i + 1, r))
            continue
        if isinstance(r, int) and 1 <= r <= 5:
            coerced.append(r)
        else:
            invalid.append((i + 1, r))
    if invalid:
        checks.append({"check": "responses_in_range", "pass": False,
                       "reason": f"{len(invalid)} invalid: {invalid[:5]}..."})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "responses_in_range", "pass": True, "reason": "all 1..5"})

    # All good — derive MBTI
    derived = derive_mbti(coerced, expected["scoring_key"], expected["letters"])
    bias = acquiescence_score(coerced)

    return {
        "score": 1.0,
        "matcher_results": checks,
        "mbti_type": derived["mbti_type"],
        "percentages": derived["percentages"],
        "bias_stats": bias,
        "raw_responses": coerced,
    }


def main() -> None:
    manifest = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(manifest["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(manifest["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(manifest["expected_dir"]) / "answer.json").read_text())

    usage_record: dict[str, Any] = {}
    usage_path = Path(manifest["outputs_dir"]) / "usage.json"
    if usage_path.exists():
        try:
            usage_record = json.loads(usage_path.read_text())
        except json.JSONDecodeError:
            pass

    if exit_code != 0:
        out = {
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "agent_answer": stdout.strip()[:300],
            "id": expected.get("id"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
            **usage_record,
        }
        print(json.dumps(out))
        return

    metrics = judge_case(stdout, expected)
    metrics["agent_answer"] = stdout.strip()[:300]
    metrics["id"] = expected.get("id")
    metrics["category"] = expected.get("category")
    metrics["difficulty"] = expected.get("difficulty")
    metrics.update(usage_record)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
