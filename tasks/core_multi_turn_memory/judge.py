"""Per-case judge for the core_multi_turn_memory task.

Grades whether the model correctly recalled information from an earlier
session in a multi-session conversation. Matcher = keywords_all against the
gold answer's content words.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


HEDGE_PHRASES = [
    "i cannot", "i can't", "i am unable", "i'm unable",
    "as an ai", "as a language model",
    "i don't know", "i do not know",
    "i don't have", "i do not have",
    "not able to determine", "unable to determine",
    "i don't recall", "i cannot recall", "i can't recall",
]


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def m_keywords_all(answer: str, spec: dict) -> tuple[bool, str]:
    norm = normalise(answer)
    values = [v.lower() for v in spec["values"]]
    missing = [v for v in values if v not in norm]
    if missing:
        return False, f"missing keywords: {missing}"
    return True, f"all keywords present: {values}"


def m_no_hedge(answer: str, spec: dict) -> tuple[bool, str]:
    norm = answer.lower()
    for p in HEDGE_PHRASES:
        if p in norm:
            return False, f"hedge phrase: {p!r}"
    return True, "no hedge phrases"


MATCHERS = {
    "keywords_all": m_keywords_all,
    "no_hedge": m_no_hedge,
}


def run_matchers(answer: str, matchers: list[dict]) -> tuple[float, list[dict]]:
    results = []
    all_ok = True
    for spec in matchers:
        kind = spec.get("kind")
        fn = MATCHERS.get(kind)
        if fn is None:
            results.append({"kind": kind, "pass": False, "reason": f"unknown: {kind!r}"})
            all_ok = False
            continue
        ok, reason = fn(answer, spec)
        results.append({"kind": kind, "pass": ok, "reason": reason})
        if not ok:
            all_ok = False
    return (1.0 if all_ok else 0.0), results


def extract_agent_answer(stdout: str) -> str:
    stdout = stdout.strip()
    if not stdout:
        return ""
    try:
        obj = json.loads(stdout)
        if isinstance(obj, dict) and "answer" in obj:
            return str(obj["answer"])
    except json.JSONDecodeError:
        pass
    return stdout


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    agent_answer = extract_agent_answer(stdout)

    if exit_code != 0:
        print(json.dumps({
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "id": expected.get("id"),
            "category": expected.get("question_type"),
        }))
        return

    if not agent_answer:
        print(json.dumps({
            "score": 0.0,
            "reason": "agent produced no answer",
            "id": expected.get("id"),
            "category": expected.get("question_type"),
        }))
        return

    matchers = expected.get("matchers", [])
    score, matcher_results = run_matchers(agent_answer, matchers)
    print(json.dumps({
        "score": score,
        "matcher_results": matcher_results,
        "agent_answer_preview": agent_answer[:500],
        "gold_answer": expected.get("gold_answer"),
        "id": expected.get("id"),
        "type": expected.get("type"),
        "category": expected.get("question_type"),
        "difficulty": expected.get("question_type"),
    }))


if __name__ == "__main__":
    main()
