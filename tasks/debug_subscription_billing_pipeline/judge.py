"""Per-case judge for debug_subscription_billing_pipeline.

Report-output-based scoring: apply the agent's edits and the gold edits to
SEPARATE copies of the input tables, RUN all four report scripts against
each, and compare stdout. Score 1.0 only if all four reports produce
identical output -- multiple equivalent fix paths all pass, since scoring
never inspects edit structure, only the resulting report output.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli). See
references/traptask-contract.md for the exact manifest shape.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

REPORT_SCRIPTS = ["billing_summary.py", "invoice_detail.py",
                   "finance_ledger.py", "customer_statement.py"]

MAX_EDITS_SCORED = 30  # anti-shotgun: edits beyond this are dropped before applying


def strip_fences(s: str) -> str:
    s = s.strip()
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
                        parsed = json.loads(s[start:end + 1])
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        break
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", s, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return None


def load_input_csvs(inputs_dir: Path) -> dict:
    import csv
    tables = {}
    for path in inputs_dir.glob("*.csv"):
        with path.open() as f:
            tables[path.name] = list(csv.DictReader(f))
    return tables


def apply_edits(tables: dict, edits: list) -> dict:
    """Apply a list of edits to a COPY of tables. Returns new state.
    Malformed entries (non-dict, unknown file, missing keys) are skipped,
    not raised -- an agent emitting garbage should score 0 via output
    mismatch, not crash the judge."""
    import copy
    new_tables = {name: copy.deepcopy(rows) for name, rows in tables.items()}
    for edit in edits[:MAX_EDITS_SCORED]:
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
                if all(
                    str(row.get(k, "")) == str(v) if v is not None else (row.get(k) in (None, "", "None"))
                    for k, v in match.items()
                ):
                    for sk, sv in set_.items():
                        row[sk] = "" if sv is None else str(sv)
        elif op == "insert":
            row_data = edit.get("row", {})
            if isinstance(row_data, dict):
                new_row = {k: ("" if v is None else str(v)) for k, v in row_data.items()}
                new_tables[file].append(new_row)
    return new_tables


def write_tables_to_dir(tables: dict, out_dir: Path) -> None:
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


def run_reports(work_dir: Path) -> dict:
    import subprocess
    import sys
    out = {}
    for script in REPORT_SCRIPTS:
        try:
            r = subprocess.run(
                [sys.executable, script],
                cwd=work_dir, capture_output=True, text=True, timeout=30,
            )
            out[script] = r.stdout
        except Exception as e:
            out[script] = f"__JUDGE_EXEC_ERROR__: {e}"
    return out


def score_case(stdout: str, expected: dict, inputs_dir: Path = None) -> dict[str, Any]:
    import shutil
    import tempfile

    gold_edits = expected.get("gold_edits", [])
    agent_edits = parse_agent_edits(stdout)
    if agent_edits is None:
        return {
            "score": 0.0,
            "reason": "failed to parse agent stdout as JSON list of edits",
            "category": expected.get("category"),
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

            shutil.copytree(inputs_dir, gold_dir)
            gold_state = apply_edits(initial, gold_edits)
            write_tables_to_dir(gold_state, gold_dir)
            gold_out = run_reports(gold_dir)

            shutil.copytree(inputs_dir, agent_dir)
            agent_state = apply_edits(initial, agent_edits)
            write_tables_to_dir(agent_state, agent_dir)
            agent_out = run_reports(agent_dir)

            mismatches = []
            for script in REPORT_SCRIPTS:
                if gold_out[script].strip() != agent_out[script].strip():
                    mismatches.append(script)

            if not mismatches:
                return {
                    "score": 1.0,
                    "reason": "all four reports match gold output",
                    "category": expected.get("category"),
                    "gold_edit_count": len(gold_edits),
                    "agent_edit_count": len(agent_edits),
                }
            diffs = [
                f"{script} differs; agent output first 300 chars: {agent_out[script][:300]!r}"
                for script in mismatches
            ]
            return {
                "score": 0.0,
                "reason": " | ".join(diffs),
                "category": expected.get("category"),
                "mismatched_reports": mismatches,
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
