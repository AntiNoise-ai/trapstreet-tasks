"""Per-case judge for codebase_graph_qa.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli). See
references/traptask-contract.md for the exact manifest shape.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_DECODER = json.JSONDecoder()
MAX_STDOUT_CHARS = 50_000  # bound scan cost on pathological/huge malformed output


def _iter_json_objects(text: str):
    """Yield every JSON object parseable starting at each '{' in `text`,
    using json.JSONDecoder.raw_decode (a real parser, not brace-counting --
    correctly skips '{' characters that appear inside string literals)."""
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _end = _DECODER.raw_decode(text, idx)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def _extract_json_object(text: str) -> dict:
    """Find a JSON object in `text` that has an 'answer' key. Tolerates a
    solution wrapping its JSON in prose, reasoning, or a markdown code
    fence -- a naive "first { to last }" substring breaks the instant any
    brace appears in prose before the real JSON, which is near-universal
    when a model narrates before answering. Never executes/evals anything,
    only json.loads via the standard library's own decoder."""
    text = text.strip()[:MAX_STDOUT_CHARS]
    candidates = list(_iter_json_objects(text))
    if not candidates:
        raise ValueError("no JSON object found in output")
    for obj in candidates:
        if "answer" in obj:
            return obj
    return candidates[-1]


def _normalize(item: Any) -> str | None:
    """Canonicalize one predicted/expected identifier for comparison.
    Returns None if `item` isn't a usable string (caller should skip it,
    not crash -- see scoring-design.md's malformed-output-robustness
    section)."""
    if not isinstance(item, str):
        return None
    s = item.strip().replace("\\", "/")
    if not s:
        return None
    for prefix in ("./repo/", "repo/", "./"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    return s.casefold()


MAX_PREDICTED_CONSIDERED = 200  # generous soft cap; see scoring-design.md anti-shotgun note


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    """Set-comparison scoring: parse the solution's {"answer": [...]} list,
    normalize each identifier, and score by F1 against the expected set.

    F1 (not a raw hit/miss) is the anti-shotgun mechanism here: listing
    every plausible identifier tanks precision, so shotgunning is
    self-punishing without needing a separate MAX_FINDINGS cap the way a
    single-best-guess task would. See references/scoring-design.md.
    """
    try:
        parsed = _extract_json_object(stdout)
    except ValueError as e:
        return {"score": 0.0, "reason": f"invalid JSON output: {e}"}

    if not isinstance(parsed, dict) or "answer" not in parsed:
        return {"score": 0.0, "reason": "output JSON missing top-level 'answer' key"}

    raw_answer = parsed["answer"]
    if not isinstance(raw_answer, list):
        return {"score": 0.0, "reason": "'answer' field is not a JSON list"}

    expected_set = {_normalize(x) for x in expected.get("answer", [])}
    expected_set.discard(None)

    predicted_set: set[str] = set()
    for item in raw_answer[:MAX_PREDICTED_CONSIDERED]:
        norm = _normalize(item)
        if norm is not None:
            predicted_set.add(norm)

    if not predicted_set:
        return {
            "score": 0.0,
            "reason": "'answer' list was empty or contained no usable string entries",
            "expected_count": len(expected_set),
        }

    matched = predicted_set & expected_set
    missing = expected_set - predicted_set
    extra = predicted_set - expected_set

    precision = len(matched) / len(predicted_set) if predicted_set else 0.0
    recall = len(matched) / len(expected_set) if expected_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "score": f1,
        "precision": precision,
        "recall": recall,
        "category": expected.get("category"),
        "expected_count": len(expected_set),
        "predicted_count": len(predicted_set),
        "missing": sorted(missing)[:20],
        "extra": sorted(extra)[:20],
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    base = {"id": expected.get("id")}

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
