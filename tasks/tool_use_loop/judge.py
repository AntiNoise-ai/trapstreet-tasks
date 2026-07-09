"""Per-case judge for the tool_use_loop task.

Grades whether the agent output a set of tool calls that satisfies the
ground truth. Each ground truth call specifies a function name and a set
of accepted values per arg. The agent's calls must, as a SET, match the
ground truth calls one-to-one.
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
    "i don't have access", "i do not have access",
]


def strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def parse_agent_calls(text: str) -> list:
    """Parse agent output as a JSON array of {"name": ..., "arguments": ...}."""
    s = strip_fences(text)
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError:
        # Try to find a JSON array in the text
        m = re.search(r"\[.*\]", s, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                return []
        else:
            return []
    if not isinstance(parsed, list):
        return []
    calls = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("function") or item.get("function_name")
        args = item.get("arguments") or item.get("parameters") or item.get("args") or {}
        if name:
            calls.append({"name": name, "arguments": args if isinstance(args, dict) else {}})
    return calls


def coerce_scalar(v):
    """Normalize scalars for comparison: int/float unify, str strip."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return v.strip()
    return v


def value_matches(agent_val, accepted_list) -> bool:
    """Check if agent's value matches ANY value in the accepted list.
    accepted_list may contain "" meaning "arg can be omitted OR set to this default"."""
    coerced_agent = coerce_scalar(agent_val)
    for acc in accepted_list:
        # Empty string means "arg optional" — matched at args_match level
        if acc == "" and agent_val in (None, "", []):
            return True
        coerced_acc = coerce_scalar(acc)
        # Direct match
        if coerced_agent == coerced_acc:
            return True
        # List comparison for nested lists
        if isinstance(agent_val, list) and isinstance(acc, list):
            if len(agent_val) == len(acc):
                if all(coerce_scalar(a) == coerce_scalar(b) for a, b in zip(agent_val, acc)):
                    return True
        # Numeric comparison (int vs float)
        try:
            if float(agent_val) == float(acc):
                return True
        except Exception:
            pass
        # Case-insensitive string
        if isinstance(coerced_agent, str) and isinstance(coerced_acc, str):
            if coerced_agent.lower() == coerced_acc.lower():
                return True
    return False


def call_matches_gt(agent_call: dict, gt_call: dict) -> bool:
    """Check if agent_call matches a ground-truth call spec.

    gt_call format: {"func_name": {"arg1": [acc_val1, acc_val2], ...}}
    """
    gt_name = list(gt_call.keys())[0]
    gt_args = gt_call[gt_name]
    if agent_call["name"] != gt_name:
        return False
    for arg, accepted_list in gt_args.items():
        agent_val = agent_call["arguments"].get(arg)
        if agent_val is None and "" in accepted_list:
            continue  # optional arg omitted
        if not value_matches(agent_val, accepted_list):
            return False
    return True


def m_parallel_tool_calls(answer: str, spec: dict) -> tuple[bool, str]:
    ground_truth = spec["ground_truth"]
    agent_calls = parse_agent_calls(answer)
    if not agent_calls:
        return False, "could not parse agent output as JSON array of tool calls"

    if len(agent_calls) != len(ground_truth):
        return False, f"call count mismatch: agent={len(agent_calls)}, expected={len(ground_truth)}"

    # Greedy set match: for each ground truth, find an unmatched agent call
    remaining = list(range(len(agent_calls)))
    matched_pairs = []
    for gt_call in ground_truth:
        found = None
        for idx in remaining:
            if call_matches_gt(agent_calls[idx], gt_call):
                found = idx
                break
        if found is None:
            gt_name = list(gt_call.keys())[0]
            unmatched_agents = [f"{agent_calls[i]['name']}({agent_calls[i]['arguments']})" for i in remaining]
            return False, f"no agent call matches gt {gt_name}({gt_call[gt_name]}); remaining agent calls: {unmatched_agents}"
        matched_pairs.append((found, gt_call))
        remaining.remove(found)

    return True, f"all {len(ground_truth)} calls matched"


def m_no_hedge(answer: str, spec: dict) -> tuple[bool, str]:
    norm = answer.lower()
    for p in HEDGE_PHRASES:
        if p in norm:
            return False, f"hedge: {p!r}"
    return True, "no hedge"


MATCHERS = {
    "parallel_tool_calls": m_parallel_tool_calls,
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
            "category": expected.get("difficulty"),
        }))
        return

    if not agent_answer:
        print(json.dumps({
            "score": 0.0,
            "reason": "agent produced no answer",
            "id": expected.get("id"),
            "category": expected.get("difficulty"),
        }))
        return

    matchers = expected.get("matchers", [])
    score, matcher_results = run_matchers(agent_answer, matchers)
    print(json.dumps({
        "score": score,
        "matcher_results": matcher_results,
        "agent_answer_preview": agent_answer[:500],
        "id": expected.get("id"),
        "type": expected.get("type"),
        "category": expected.get("difficulty"),
        "difficulty": expected.get("difficulty"),
        "num_calls": expected.get("num_calls"),
    }))


if __name__ == "__main__":
    main()
