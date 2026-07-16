"""Per-case judge for the doc_editing task — deterministic content-retention diff.

Inspired by DELEGATE-52 ("LLMs Corrupt Your Documents When You Delegate"): the
agent performs a structure-changing edit (reformat / sort / uniform edit) and
MUST preserve every record and value. The judge re-parses the agent's output
and compares it to the gold record set, computing exact-match plus a
content-retention percentage (the headline "you silently lost X% of the doc"
metric).

answer.json schema:
  {
    "id": "...", "category": "...", "difficulty": "...",
    "match_mode": "multiset" | "ordered" | "dict",
    "numeric_keys": ["amount"],        # compared as floats rounded to 2dp
    "gold": [ {..}, .. ]  or  {..}      # list of records, or a dict
  }

Scoring is strict: score 1.0 only on an EXACT match (no dropped / extra /
altered records). Otherwise 0.0 — but the metrics carry retention_pct,
n_dropped, n_extra, n_altered so the leaderboard can show *how* it failed.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _parse(stdout: str) -> Any:
    return json.loads(_strip_fences(stdout))


def _norm(key: str, val: Any, numeric_keys: set[str]) -> Any:
    if key in numeric_keys:
        try:
            return round(float(str(val).replace(",", "").replace("$", "").strip()), 2)
        except (ValueError, TypeError):
            return f"__NONNUMERIC__{str(val).strip()}"
    return str(val).strip()


def _sig(rec: dict, numeric_keys: set[str]) -> tuple:
    if not isinstance(rec, dict):
        return ("__NOTADICT__", str(rec))
    return tuple(sorted((k, _norm(k, rec.get(k), numeric_keys)) for k in rec))


def _coerce_list(parsed: Any) -> list | None:
    if isinstance(parsed, list):
        return parsed
    # tolerate {"records": [...]} / {"rows": [...]} / single list-valued dict
    if isinstance(parsed, dict):
        lists = [v for v in parsed.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
    return None


def judge_case(stdout: str, expected: dict) -> dict[str, Any]:
    mode = expected["match_mode"]
    numeric_keys = set(expected.get("numeric_keys", []))
    gold = expected["gold"]

    base = {
        "id": expected.get("id"),
        "category": expected.get("category"),
        "difficulty": expected.get("difficulty"),
        "match_mode": mode,
    }

    try:
        parsed = _parse(stdout)
    except json.JSONDecodeError as e:
        return {**base, "score": 0.0, "reason": f"output is not valid JSON: {e}",
                "retention_pct": 0.0}

    # ----- dict mode -----
    if mode == "dict":
        if not isinstance(parsed, dict):
            return {**base, "score": 0.0, "reason": "expected a JSON object", "retention_pct": 0.0}
        gold_keys = set(gold)
        out_keys = set(parsed)
        matched = sum(
            1 for k in gold_keys
            if k in parsed and _norm(k, parsed[k], numeric_keys) == _norm(k, gold[k], numeric_keys)
        )
        dropped = sorted(gold_keys - out_keys)
        extra = sorted(out_keys - gold_keys)
        altered = sorted(
            k for k in gold_keys & out_keys
            if _norm(k, parsed[k], numeric_keys) != _norm(k, gold[k], numeric_keys)
        )
        retention = round(matched / len(gold_keys), 4) if gold_keys else 1.0
        exact = not dropped and not extra and not altered
        return {**base, "score": 1.0 if exact else 0.0,
                "retention_pct": round(retention * 100, 1),
                "n_dropped": len(dropped), "n_extra": len(extra), "n_altered": len(altered),
                "dropped_keys": dropped[:10], "altered_keys": altered[:10],
                "reason": "exact match" if exact else
                          f"{len(dropped)} dropped, {len(extra)} extra, {len(altered)} altered keys"}

    # ----- list modes -----
    out_list = _coerce_list(parsed)
    if out_list is None:
        return {**base, "score": 0.0, "reason": "expected a JSON array of records",
                "retention_pct": 0.0}

    gold_sigs = [_sig(r, numeric_keys) for r in gold]
    out_sigs = [_sig(r, numeric_keys) for r in out_list]
    gold_ctr, out_ctr = Counter(gold_sigs), Counter(out_sigs)
    matched = sum((gold_ctr & out_ctr).values())
    retention = round(matched / len(gold_sigs), 4) if gold_sigs else 1.0
    n_dropped = sum((gold_ctr - out_ctr).values())
    n_extra = sum((out_ctr - gold_ctr).values())

    if mode == "ordered":
        exact = out_sigs == gold_sigs
        reason = "exact ordered match" if exact else (
            "order or content differs "
            f"(matched {matched}/{len(gold_sigs)}, {n_dropped} missing, {n_extra} extra)")
    else:  # multiset
        exact = gold_ctr == out_ctr
        reason = "exact set match" if exact else (
            f"matched {matched}/{len(gold_sigs)}, {n_dropped} dropped/altered, {n_extra} extra")

    return {**base, "score": 1.0 if exact else 0.0,
            "retention_pct": round(retention * 100, 1),
            "n_dropped": n_dropped, "n_extra": n_extra, "reason": reason}


def main() -> None:
    manifest = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(manifest["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(manifest["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(manifest["expected_dir"]) / "answer.json").read_text())

    usage: dict[str, Any] = {}
    up = Path(manifest["outputs_dir"]) / "usage.json"
    if up.exists():
        try:
            usage = json.loads(up.read_text())
        except json.JSONDecodeError:
            usage = {}

    if exit_code != 0:
        print(json.dumps({"score": 0.0, "reason": f"solution exited {exit_code}",
                          "id": expected.get("id"), "category": expected.get("category"),
                          "difficulty": expected.get("difficulty"), **usage}))
        return

    metrics = judge_case(stdout, expected)
    metrics["agent_answer"] = stdout.strip()[:500]
    metrics.update(usage)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
