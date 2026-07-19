"""Per-case judge for debug_vendor_payout_pipeline.

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
    # Strip <think>...</think> blocks that some models emit
    s = re.sub(r"<think>.*?</think>\s*", "", s, flags=re.DOTALL)
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def parse_agent_edits(stdout: str) -> list | None:
    """Return list of edit dicts, or None if unparseable."""
    s = strip_fences(stdout)
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    # Try to find first well-formed JSON array anywhere in the output.
    # Match balanced brackets by scanning for [ and finding matching ].
    for start in range(len(s)):
        if s[start] != '[':
            continue
        depth = 0
        for end in range(start, len(s)):
            if s[end] == '[':
                depth += 1
            elif s[end] == ']':
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(s[start:end+1])
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        break
    # Fallback: search for JSON array in markdown code block
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", s, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return None


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


def load_input_csvs(inputs_dir: Path) -> dict:
    """Load all *.csv from inputs_dir as list-of-dicts."""
    import csv
    tables = {}
    for path in inputs_dir.glob("*.csv"):
        with path.open() as f:
            tables[path.name] = list(csv.DictReader(f))
    return tables


def apply_edits(tables: dict, edits: list) -> dict:
    """Apply a list of edits to a COPY of tables. Returns new state."""
    import copy
    new_tables = {name: copy.deepcopy(rows) for name, rows in tables.items()}
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        file = edit.get("file")
        op = edit.get("op")
        if file not in new_tables:
            continue
        if op == "update":
            match = edit.get("match", {})
            set_ = edit.get("set", {})
            if not isinstance(match, dict) or not isinstance(set_, dict):
                continue
            for row in new_tables[file]:
                if all(str(row.get(k, "")) == str(v) if v is not None else (row.get(k) in (None, "", "None")) for k, v in match.items()):
                    for sk, sv in set_.items():
                        row[sk] = "" if sv is None else str(sv)
        elif op == "insert":
            row_data = edit.get("row", {})
            if isinstance(row_data, dict):
                new_row = {k: ("" if v is None else str(v)) for k, v in row_data.items()}
                new_tables[file].append(new_row)
    return new_tables


def normalize_row(row: dict) -> tuple:
    """Convert a row dict to a normalized tuple for comparison."""
    items = []
    for k in sorted(row.keys()):
        v = row.get(k, "")
        v = normalize_scalar(v)
        items.append((k, v))
    return tuple(items)


def tables_equal(t1: dict, t2: dict) -> tuple[bool, str]:
    """Compare two table dicts. Returns (equal, diff_description)."""
    if set(t1.keys()) != set(t2.keys()):
        return False, f"file set mismatch: {set(t1.keys()) ^ set(t2.keys())}"
    for fname in t1:
        rows1 = sorted([normalize_row(r) for r in t1[fname]])
        rows2 = sorted([normalize_row(r) for r in t2[fname]])
        if rows1 != rows2:
            only1 = [r for r in rows1 if r not in rows2]
            only2 = [r for r in rows2 if r not in rows1]
            return False, f"{fname} differs: gold-only={only1[:2]}, agent-only={only2[:2]}"
    return True, ""


def write_tables_to_dir(tables: dict, out_dir: Path) -> None:
    """Write tables dict back out as CSVs in out_dir."""
    import csv
    for fname, rows in tables.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        with (out_dir / fname).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for row in rows:
                w.writerow({c: row.get(c, "") for c in cols})


def run_reports(work_dir: Path) -> tuple[str, str]:
    """Run both report scripts in work_dir, return (pub_output, item_output)."""
    import subprocess
    import sys
    pub = subprocess.run(
        [sys.executable, "vendor_statement.py"],
        cwd=work_dir, capture_output=True, text=True, timeout=30,
    )
    item = subprocess.run(
        [sys.executable, "itemised_statement.py"],
        cwd=work_dir, capture_output=True, text=True, timeout=30,
    )
    return pub.stdout, item.stdout


def score_case(stdout: str, expected: dict, inputs_dir: Path = None) -> dict[str, Any]:
    """Report-output-based scoring: apply agent edits and gold edits, then
    RUN both report scripts and compare their stdout. Score 1.0 only if both
    reports produce identical output (semantic equivalence at the report
    layer -- multiple equivalent fix paths all pass)."""
    import shutil
    import tempfile
    gold_edits = expected.get("gold_edits", [])
    agent_edits = parse_agent_edits(stdout)
    if agent_edits is None:
        return {
            "score": 0.0,
            "reason": "failed to parse agent stdout as JSON list of edits",
            "category": expected.get("category"),
            "difficulty": expected.get("category"),
            "gold_edit_count": len(gold_edits),
        }
    if not isinstance(agent_edits, list):
        return {
            "score": 0.0,
            "reason": "agent output not a JSON list",
            "category": expected.get("category"),
        }

    if inputs_dir is None or not inputs_dir.exists():
        return {
            "score": 0.0,
            "reason": "inputs_dir not available for data-aware scoring",
            "category": expected.get("category"),
        }

    initial = load_input_csvs(inputs_dir)

    try:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            gold_dir = td_path / "gold"
            agent_dir = td_path / "agent"

            # Set up gold work dir: copy scripts + modified CSVs
            shutil.copytree(inputs_dir, gold_dir)
            gold_state = apply_edits(initial, gold_edits)
            write_tables_to_dir(gold_state, gold_dir)
            gold_pub, gold_item = run_reports(gold_dir)

            # Set up agent work dir
            shutil.copytree(inputs_dir, agent_dir)
            agent_state = apply_edits(initial, agent_edits)
            write_tables_to_dir(agent_state, agent_dir)
            agent_pub, agent_item = run_reports(agent_dir)

            pub_ok = gold_pub.strip() == agent_pub.strip()
            item_ok = gold_item.strip() == agent_item.strip()

            if pub_ok and item_ok:
                return {
                    "score": 1.0,
                    "reason": "both reports match gold output",
                    "category": expected.get("category"),
                    "difficulty": expected.get("category"),
                    "gold_edit_count": len(gold_edits),
                    "agent_edit_count": len(agent_edits),
                }
            diffs = []
            if not pub_ok:
                diffs.append(f"vendor_statement differs; agent output first 300 chars: {agent_pub[:300]!r}")
            if not item_ok:
                diffs.append(f"itemised_statement differs; agent output first 300 chars: {agent_item[:300]!r}")
            return {
                "score": 0.0,
                "reason": " | ".join(diffs),
                "category": expected.get("category"),
                "difficulty": expected.get("category"),
                "gold_edit_count": len(gold_edits),
                "agent_edit_count": len(agent_edits),
            }
    except Exception as e:
        return {
            "score": 0.0,
            "reason": f"judge crashed while running scripts: {e}",
            "category": expected.get("category"),
        }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())
    inputs_dir = Path(m["inputs_dir"])

    base = {"id": expected.get("id")}

    if exit_code != 0:
        print(json.dumps({**base, "score": 0.0, "reason": f"solution exited {exit_code}",
                           "agent_output": stdout.strip()[:500]}))
        return
    if not stdout.strip():
        print(json.dumps({**base, "score": 0.0, "reason": "agent produced no output",
                           "agent_output": ""}))
        return

    metrics = score_case(stdout, expected, inputs_dir)
    metrics.update(base)
    metrics["agent_output"] = stdout.strip()[:500]
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
