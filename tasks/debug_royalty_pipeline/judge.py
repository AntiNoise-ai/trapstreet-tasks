"""Per-case judge for debug_royalty_pipeline.

Compares the agent's JSON list of edits to the gold edit set. Scoring is
strictly set-based: 1.0 only if the agent's edits, as a SET, exactly match
the gold edits (order-independent). Extra edits count against the agent
(anti-shotgun).

I/O contract: reads TRAPTASK_MANIFEST (trap-cli). See
references/traptask-contract.md for the exact manifest shape.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def parse_agent_edits(stdout: str) -> list | None:
    """Return list of edit dicts, or None if unparseable."""
    s = strip_fences(stdout)
    try:
        parsed = json.loads(s)
    except Exception:
        # Try to find first JSON array in output
        m = re.search(r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]", s, re.DOTALL)
        if not m:
            return None
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            return None
    if not isinstance(parsed, list):
        return None
    return parsed


def normalize_scalar(v):
    """Normalize scalars so 0.8 == "0.8", null == None, etc."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    if isinstance(v, str):
        s = v.strip()
        if s.lower() in ("null", "none", ""):
            return None
        try:
            f = float(s)
            return round(f, 6)
        except ValueError:
            return s
    return v


def normalize_dict(d):
    if not isinstance(d, dict):
        return {}
    return {k: normalize_scalar(v) for k, v in d.items()}


def canonicalize_edit(edit: dict) -> tuple:
    """Convert an edit dict to a canonical, hashable tuple for set comparison."""
    if not isinstance(edit, dict):
        return ("__invalid__",)
    file = edit.get("file", "")
    op = edit.get("op", "")
    if op == "update":
        match = tuple(sorted(normalize_dict(edit.get("match", {})).items()))
        set_ = tuple(sorted(normalize_dict(edit.get("set", {})).items()))
        return ("update", file, match, set_)
    elif op == "insert":
        row = tuple(sorted(normalize_dict(edit.get("row", {})).items()))
        return ("insert", file, row)
    else:
        return ("__unknown_op__", file, op)


def match_is_compatible(agent_match: dict, gold_match: dict) -> bool:
    """Return True if agent's match uniquely identifies the same rows as gold's.

    Accepted when agent's match is a superset of gold's match (every gold
    key/value present in agent's match). Rationale: gold match is the minimal
    identification; agent may over-specify with extra fields for the same row,
    which is functionally equivalent, not gaming.
    """
    if not isinstance(agent_match, dict) or not isinstance(gold_match, dict):
        return False
    for k, v in gold_match.items():
        if k not in agent_match:
            return False
        if normalize_scalar(agent_match[k]) != normalize_scalar(v):
            return False
    return True


def edit_matches_gold(agent_edit: dict, gold_edit: dict) -> bool:
    """Semantic equivalence check that tolerates over-specified `match` fields
    on updates. For inserts, require exact row match."""
    if not isinstance(agent_edit, dict) or not isinstance(gold_edit, dict):
        return False
    if agent_edit.get("file") != gold_edit.get("file"):
        return False
    if agent_edit.get("op") != gold_edit.get("op"):
        return False
    if gold_edit.get("op") == "update":
        if not match_is_compatible(agent_edit.get("match", {}), gold_edit.get("match", {})):
            return False
        agent_set = normalize_dict(agent_edit.get("set", {}))
        gold_set = normalize_dict(gold_edit.get("set", {}))
        return agent_set == gold_set
    if gold_edit.get("op") == "insert":
        return normalize_dict(agent_edit.get("row", {})) == normalize_dict(gold_edit.get("row", {}))
    return False


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    """Compare agent edits vs gold edits. Score 1.0 if sets match exactly."""
    gold_edits = expected.get("gold_edits", [])
    gold_canonical = {canonicalize_edit(e) for e in gold_edits}

    agent_edits = parse_agent_edits(stdout)
    if agent_edits is None:
        return {
            "score": 0.0,
            "reason": "failed to parse agent stdout as JSON list of edits",
            "category": expected.get("category"),
            "difficulty": expected.get("category"),
            "gold_edit_count": len(gold_edits),
            "agent_edit_count": None,
        }

    if not isinstance(agent_edits, list):
        return {
            "score": 0.0,
            "reason": "agent output not a JSON list",
            "category": expected.get("category"),
            "difficulty": expected.get("category"),
        }

    # Match each gold edit against a compatible agent edit (semantic match,
    # tolerates over-specified match dicts on updates). Track which agent
    # edits got used so we can flag extras.
    matched_agent_indices = set()
    missing = []
    for g in gold_edits:
        found = None
        for i, a in enumerate(agent_edits):
            if i in matched_agent_indices:
                continue
            if edit_matches_gold(a, g):
                found = i
                break
        if found is None:
            missing.append(g)
        else:
            matched_agent_indices.add(found)

    extra = [a for i, a in enumerate(agent_edits) if i not in matched_agent_indices]

    if not missing and not extra:
        return {
            "score": 1.0,
            "reason": "all gold edits present, no extras",
            "category": expected.get("category"),
            "difficulty": expected.get("category"),
            "gold_edit_count": len(gold_edits),
            "agent_edit_count": len(agent_edits),
        }

    reason_parts = []
    if missing:
        reason_parts.append(f"missing {len(missing)} gold edit(s): {missing[:3]}")
    if extra:
        reason_parts.append(f"has {len(extra)} extra unnecessary edit(s): {extra[:3]}")
    return {
        "score": 0.0,
        "reason": "; ".join(reason_parts),
        "category": expected.get("category"),
        "difficulty": expected.get("category"),
        "gold_edit_count": len(gold_edits),
        "agent_edit_count": len(agent_edits),
        "missing_count": len(missing),
        "extra_count": len(extra),
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
