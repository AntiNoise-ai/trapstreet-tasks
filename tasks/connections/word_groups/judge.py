"""Per-case judge for the connections/word_groups task.

The model receives 16 words and must partition them into 4 groups of 4.
Only the first 4 groups emitted are scored (anti-shotgun); extras are ignored.
score = (gold groups exactly reproduced among the first 4) / 4, by set-equality
of the words (case/whitespace-insensitive; group order and theme labels do not
matter). solved = well_formed AND all 4 groups correct, where well_formed means
exactly 4 groups of 4 words forming a valid partition of the 16-word universe.
Theme labels are surfaced but NOT graded.

I/O contract matches personality/mbti_profile/judge.py: reads TRAPTASK_MANIFEST.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


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


def _norm(w: Any) -> str:
    return str(w).strip().upper()


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    s = _strip_fences(stdout)
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return {"score": 0.0, "groups_correct": 0, "solved": False,
                "well_formed": False,
                "format_ok": False, "reason": "output is not valid JSON"}

    if not isinstance(obj, dict) or not isinstance(obj.get("groups"), list):
        return {"score": 0.0, "groups_correct": 0, "solved": False,
                "well_formed": False,
                "format_ok": False, "reason": "missing 'groups' list"}

    gold_sets = [frozenset(_norm(w) for w in g["words"]) for g in expected["groups"]]
    n_gold = len(gold_sets)
    gold_universe = set().union(*gold_sets)

    # Themes are collected from ALL groups (ungraded).
    themes = [g.get("theme") for g in obj["groups"] if isinstance(g, dict)]

    # Score only the first n_gold groups (anti-shotgun): extras are ignored.
    scored_groups = obj["groups"][:n_gold]
    model_sets = []
    for g in scored_groups:
        if isinstance(g, dict) and isinstance(g.get("words"), list):
            model_sets.append(frozenset(_norm(w) for w in g["words"]))

    # groups_correct: matches among the first n_gold groups. A gold set is
    # counted at most once even if the model repeats it within the first four.
    matched = set()
    for gs in gold_sets:
        for i, ms in enumerate(model_sets):
            if i not in matched and ms == gs:
                matched.add(i)
                break
    groups_correct = len(matched)

    # well_formed: exactly n_gold groups, each exactly 4 words, together a
    # valid partition of the 16-word universe.
    all_words = [w for ms in model_sets for w in ms]
    well_formed = (
        len(obj["groups"]) == n_gold
        and len(model_sets) == n_gold
        and all(len(ms) == 4 for ms in model_sets)
        and len(all_words) == len(gold_universe)
        and set(all_words) == gold_universe
    )

    score = groups_correct / n_gold if n_gold else 0.0
    return {
        "score": round(score, 3),
        "groups_correct": groups_correct,
        "solved": well_formed and groups_correct == n_gold,
        "well_formed": well_formed,
        "format_ok": True,
        "themes": themes,
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
        print(json.dumps({
            "score": 0.0, "reason": f"solution exited {exit_code}",
            "agent_answer": stdout.strip()[:300],
            "id": expected.get("id"), "category": expected.get("category"),
            "difficulty": expected.get("difficulty"), **usage_record,
        }))
        return

    metrics = score_case(stdout, expected)
    metrics["agent_answer"] = stdout.strip()[:300]
    metrics["id"] = expected.get("id")
    metrics["category"] = expected.get("category")
    metrics["difficulty"] = expected.get("difficulty")
    metrics.update(usage_record)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
