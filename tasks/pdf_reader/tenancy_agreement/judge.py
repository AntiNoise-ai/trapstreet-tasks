"""Per-case judge for the tenancy_agreement task.

Reads the agent's stdout (expected JSON: {"answer": "..."} or just a plain string)
and compares it against expected/{case_id}/answer.json. Substring match,
case-insensitive, whitespace-normalised. Supports `accepted: [...]` for variants.

Outputs a JSON object on stdout — trap stores it as CaseResult.metrics.
Convention: include a numeric `score` (0.0 or 1.0) so --fail-fast works.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_agent_answer(stdout: str) -> str:
    """Agent may emit JSON {"answer": "..."} or plain text. Accept both."""
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
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    agent_answer = extract_agent_answer(stdout)
    targets: list[str] = [t for t in [expected.get("answer"), *expected.get("accepted", [])] if t]

    if exit_code != 0:
        result = {"score": 0.0, "reason": f"agent exited {exit_code}",
                  "agent_answer": agent_answer, "expected": targets}
    elif not targets:
        # Gold answer not filled in yet — score nothing so the case is visible but neutral.
        result = {"score": None, "reason": "no gold answer set",
                  "agent_answer": agent_answer}
    else:
        agent_norm = normalise(agent_answer)
        hit = next((t for t in targets if normalise(t) in agent_norm), None)
        result = {
            "score": 1.0 if hit else 0.0,
            "matched": hit,
            "agent_answer": agent_answer,
            "expected": targets,
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
