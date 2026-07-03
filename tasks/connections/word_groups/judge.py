"""Per-case judge for the connections/word_groups task.

The model receives 16 words and must partition them into 4 groups of 4.
score = (gold groups exactly reproduced) / 4, by set-equality of the words
(case/whitespace-insensitive; group order and theme labels do not matter).
solved = all 4 groups correct. Theme labels are surfaced but NOT graded.

I/O contract matches personality/mbti_profile/judge.py: reads TRAPTASK_PAYLOAD.
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
                "format_ok": False, "reason": "output is not valid JSON"}

    if not isinstance(obj, dict) or not isinstance(obj.get("groups"), list):
        return {"score": 0.0, "groups_correct": 0, "solved": False,
                "format_ok": False, "reason": "missing 'groups' list"}

    gold_sets = [frozenset(_norm(w) for w in g["words"]) for g in expected["groups"]]
    n_gold = len(gold_sets)

    model_sets = set()
    themes = []
    for g in obj["groups"]:
        if isinstance(g, dict):
            themes.append(g.get("theme"))
            if isinstance(g.get("words"), list):
                model_sets.add(frozenset(_norm(w) for w in g["words"]))

    correct = sum(1 for gs in gold_sets if gs in model_sets)
    score = correct / n_gold if n_gold else 0.0
    return {
        "score": round(score, 3),
        "groups_correct": correct,
        "solved": correct == n_gold,
        "format_ok": True,
        "themes": themes,
    }


def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])
    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    usage_record: dict[str, Any] = {}
    usage_path = payload["outputs"].get("usage.json")
    if usage_path and Path(usage_path).exists():
        try:
            usage_record = json.loads(Path(usage_path).read_text())
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
