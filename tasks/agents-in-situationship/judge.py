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
