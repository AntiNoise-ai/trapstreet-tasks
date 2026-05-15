"""Per-case judge for the product_matching/sku_disambiguation task.

Reads the agent's stdout (must be a JSON object with `verdict` field) and
strictly checks the verdict against gold. Three-way classification:
  same · variant · different

  - same:     identical product (synonyms, brand-vs-generic, abbreviations)
  - variant:  same product line, different SKU (storage, color, connector, trim, size)
  - different: distinct products (different lines, different products in a family, unrelated)

Score is 1.0 if and only if the verdict matches gold exactly. No partial credit:
a model that says "different" when the answer is "variant" has missed the
subtlety the task exists to expose.

`reasoning` is captured for the report but NOT graded — letting it influence
the score would push us toward LLM-judge land, which this task deliberately avoids.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

VALID_VERDICTS = {"same", "variant", "different"}


def _strip_fences(text: str) -> str:
    """Remove ```json...``` and ```...``` wrappers some LLMs insist on."""
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
    stripped = _strip_fences(stdout)
    if not stripped:
        return None, "empty stdout"
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as e:
        # Last-ditch: try to extract a {"verdict": "..."} substring
        m = re.search(r'\{[^{}]*"verdict"[^{}]*\}', stripped, re.DOTALL)
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


def judge_case(stdout: str, expected: dict) -> dict[str, Any]:
    checks: list[dict] = []

    obj, err = _parse_output(stdout)
    if obj is None:
        checks.append({"check": "json_parse", "pass": False, "reason": err})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "json_parse", "pass": True, "reason": "ok"})

    verdict = obj.get("verdict")
    if verdict is None or not isinstance(verdict, str):
        checks.append({"check": "verdict_present", "pass": False, "reason": "missing or non-string verdict field"})
        return {"score": 0.0, "matcher_results": checks}
    v = verdict.strip().lower()
    checks.append({"check": "verdict_present", "pass": True, "reason": f"got {v!r}"})

    if v not in VALID_VERDICTS:
        checks.append({"check": "verdict_in_vocab", "pass": False,
                       "reason": f"{v!r} not in {sorted(VALID_VERDICTS)}"})
        return {"score": 0.0, "matcher_results": checks}
    checks.append({"check": "verdict_in_vocab", "pass": True, "reason": "ok"})

    gold = expected["verdict"].strip().lower()
    if v != gold:
        checks.append({"check": "verdict_matches_gold", "pass": False,
                       "reason": f"got {v!r}, gold {gold!r}"})
        return {
            "score": 0.0,
            "matcher_results": checks,
            "agent_verdict": v,
            "gold_verdict": gold,
            "agent_reasoning": obj.get("reasoning", ""),
        }
    checks.append({"check": "verdict_matches_gold", "pass": True, "reason": f"{v!r} matches"})

    return {
        "score": 1.0,
        "matcher_results": checks,
        "agent_verdict": v,
        "gold_verdict": gold,
        "agent_reasoning": obj.get("reasoning", ""),
    }


def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    # Pick up usage.json if the solution captured it
    usage_record: dict[str, Any] = {}
    usage_path = payload["outputs"].get("usage.json")
    if usage_path and Path(usage_path).exists():
        try:
            usage_record = json.loads(Path(usage_path).read_text())
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
