"""Per-case judge for the agents-in-situationship task.

20 dating scenarios, 4 options each. The judge:

  1. Parses stdout as JSON (`{"answers": [20 uppercase A/B/C/D]}`)
  2. Validates format strictly — exactly 20 entries, each in {A,B,C,D}
  3. Sums per-trait weights across all 20 answers
  4. Detects 'disorganized' attachment via 3 consistency probe pairs
  5. Looks up a viral one-liner label

Score: 1.0 if format is valid, 0.0 otherwise. The derived `attachment_style`
and `label` are surfaced in metrics but NOT graded — there's no canonical
attachment style for an AI.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

VALID_LETTERS = {"A", "B", "C", "D"}


def _strip_fences(text: str) -> str:
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
        m = re.search(r'\{[^{}]*"answers"[^{}]*\[[\s\S]*?\][^{}]*\}', s)
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


def _validate_answers(answers: Any, n_expected: int) -> tuple[bool, str]:
    if not isinstance(answers, list):
        return False, "'answers' is not a list"
    if len(answers) != n_expected:
        return False, f"got {len(answers)} answers, expected {n_expected}"
    bad = [(i + 1, a) for i, a in enumerate(answers) if not (isinstance(a, str) and a in VALID_LETTERS)]
    if bad:
        return False, f"{len(bad)} invalid letters: {bad[:5]}"
    return True, ""


ALL_TRAITS = ("secure", "anxious", "avoidant", "toxic", "delulu", "unbothered", "people_pleasing")


def _sum_traits(answers: list[str], scoring_key: list[dict]) -> dict[str, int]:
    """Sum per-trait weights across all answers."""
    sums: dict[str, int] = {t: 0 for t in ALL_TRAITS}
    for i, letter in enumerate(answers):
        q = scoring_key[i]
        weights = q["options"][letter]
        for trait, points in weights.items():
            sums[trait] = sums.get(trait, 0) + points
    return sums


ANXIOUS_CODED_MIN = 2
AVOIDANT_CODED_MIN = 2


def _option_coding(weights: dict[str, int]) -> str:
    """Return 'anxious', 'avoidant', or 'neither' for this option's weight map."""
    anx = weights.get("anxious", 0)
    av = weights.get("avoidant", 0)
    if anx >= ANXIOUS_CODED_MIN and anx >= av:
        return "anxious"
    if av >= AVOIDANT_CODED_MIN and av > anx:
        return "avoidant"
    return "neither"


def _count_disorganized_flips(answers: list[str], scoring_key: list[dict]) -> int:
    """Count how many probe pairs flip between anxious-coded and avoidant-coded."""
    by_pair: dict[int, list[str]] = defaultdict(list)
    for i, q in enumerate(scoring_key):
        if "probe_pair" not in q:
            continue
        letter = answers[i]
        coding = _option_coding(q["options"][letter])
        by_pair[q["probe_pair"]].append(coding)

    flips = 0
    for pair_id, codings in by_pair.items():
        # Each pair has exactly 2 entries — assert defensively
        if len(codings) != 2:
            continue
        c1, c2 = codings
        if {c1, c2} == {"anxious", "avoidant"}:
            flips += 1
    return flips


def _pick_primary(sums: dict[str, int], flips: int, disorganized_threshold: int,
                   tiebreak: list[str]) -> str:
    if flips >= disorganized_threshold:
        return "disorganized"
    # Pick highest of (secure, anxious, avoidant). Ties broken by `tiebreak` order.
    candidates = [(sums.get(t, 0), tiebreak.index(t), t) for t in tiebreak]
    # Higher score wins (negate for sort), then earlier tiebreak index wins.
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


def _pick_top_two_flavors(sums: dict[str, int], all_flavors: list[str]) -> list[str]:
    """Pick the 2 highest-scoring flavors. Ties broken alphabetically.

    `all_flavors` is expected to be alphabetically sorted (the caller passes
    it that way; we sort defensively just in case)."""
    sorted_flavors = sorted(all_flavors)
    # (score desc, alphabetical asc) — sort by score descending, then alpha.
    ranked = sorted(sorted_flavors, key=lambda t: (-sums.get(t, 0), t))
    return ranked[:2]


def _build_label(primary: str, top_two_flavors: list[str],
                  label_table: dict, fallback_labels: dict,
                  all_zero_flavors: bool) -> str:
    if all_zero_flavors:
        return fallback_labels.get(primary, f"{primary.title()} Energy")
    pair_key = "|".join(sorted(top_two_flavors))
    primary_table = label_table.get(primary, {})
    if pair_key in primary_table:
        return primary_table[pair_key]
    return fallback_labels.get(primary, f"{primary.title()} Energy")


from collections import Counter


def _is_flat(answers: list[str], threshold: float) -> bool:
    if not answers:
        return False
    counts = Counter(answers)
    most_common_count = counts.most_common(1)[0][1]
    return (most_common_count / len(answers)) > threshold


def judge_case(stdout: str, expected: dict) -> dict[str, Any]:
    checks: list[dict] = []

    obj, err = _parse_output(stdout)
    if obj is None:
        checks.append({"check": "json_parse", "pass": False, "reason": err})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "json_parse", "pass": True, "reason": "ok"})

    answers = obj.get("answers")
    n_expected = expected.get("n_questions", 20)
    ok, err = _validate_answers(answers, n_expected)
    if not ok:
        checks.append({"check": "answers_format", "pass": False, "reason": err})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "answers_format", "pass": True, "reason": f"{n_expected} valid letters"})

    sums = _sum_traits(answers, expected["scoring_key"])
    flips = _count_disorganized_flips(answers, expected["scoring_key"])
    primary = _pick_primary(
        sums,
        flips=flips,
        disorganized_threshold=expected.get("disorganized_threshold", 2),
        tiebreak=expected["primary_tiebreak_order"],
    )

    flavor_sums = {t: sums.get(t, 0) for t in expected["flavor_traits"]}
    all_zero = all(v == 0 for v in flavor_sums.values())
    top_two = _pick_top_two_flavors(sums, expected["flavor_traits"])
    label = _build_label(primary, top_two,
                          label_table=expected["label_table"],
                          fallback_labels=expected["fallback_labels"],
                          all_zero_flavors=all_zero)

    flat = _is_flat(answers, expected.get("flat_response_threshold", 0.70))

    raw_scores = dict(sums)
    raw_scores["disorganized_flips"] = flips

    return {
        "score": 1.0,
        "matcher_results": checks,
        "attachment_style": primary,
        "flavor_traits": top_two,
        "label": label,
        "raw_scores": raw_scores,
        "flat_response": flat,
        "raw_answers": answers,
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
