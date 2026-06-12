"""Importer for a GSM8K slice into the trapstreet task format.

Source : openai/grade-school-math  (GSM8K), MIT License, (c) 2021 OpenAI
Upstream: https://github.com/openai/grade-school-math
Data   : grade_school_math/data/test.jsonl  (fetched at build time)

We vendor a fixed N-item slice (first N of the test split, for reproducibility)
as deterministic numeric-answer cases. Each case asks for the final number only,
graded by a leading_numeric matcher (reused from pdf_reader). See ATTRIBUTION.md.

Run:  python3 build_cases.py            # fetch + vendor (needs network)
      python3 build_cases.py --n 25     # choose slice size
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"

GOLD_RE = re.compile(r"####\s*(-?[\d,]+(?:\.\d+)?)")


def fetch(n: int) -> list[dict]:
    with urllib.request.urlopen(SRC, timeout=60) as r:
        lines = r.read().decode("utf-8").splitlines()
    out = []
    for line in lines[:n]:
        rec = json.loads(line)
        m = GOLD_RE.search(rec["answer"])
        if not m:
            continue
        gold = m.group(1).replace(",", "")
        out.append({"question": rec["question"], "gold": gold})
    return out


def build(n: int) -> int:
    items = fetch(n)
    lines = ["dirs:", "  inputs: inputs/", "  expected: expected/", "", "cases:"]
    gold_cases = []
    for i, it in enumerate(items, 1):
        cid = f"gsm8k_{i:03d}"
        (HERE / "inputs" / cid).mkdir(parents=True, exist_ok=True)
        (HERE / "expected" / cid).mkdir(parents=True, exist_ok=True)
        q = (it["question"].strip() +
             "\n\nSolve the problem and respond with ONLY the final numeric answer "
             "(digits only — no working, no units, no currency symbol).\n")
        (HERE / "inputs" / cid / "question.txt").write_text(q)
        gold_num = float(it["gold"])
        (HERE / "expected" / cid / "answer.json").write_text(json.dumps({
            "id": cid, "answer": it["gold"], "type": "numeric",
            "matchers": [{"kind": "leading_numeric", "value": gold_num, "tolerance": 0.001}],
            "category": "math_word_problem", "difficulty": "medium",
            "_source": "GSM8K (openai/grade-school-math, MIT)",
        }, indent=2) + "\n")
        desc = it["question"].strip().replace('"', "'").replace("\n", " ")[:90]
        lines += [f"- id: {cid}", f'  description: "{desc}..."', "  tags:",
                  "  - math_word_problem", "  - gsm8k", ""]
        gold_cases.append({"id": cid, "answer": it["gold"], "category": "math_word_problem"})
    lines += ["judge:", "  cmd: python3 judge.py", "", "grader:", "  cmd: python3 grader.py", ""]
    (HERE / "traptask.yaml").write_text("\n".join(lines))
    (HERE / "gold.cases.json").write_text(json.dumps(gold_cases, indent=2) + "\n")
    return len(items)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    a = ap.parse_args()
    print(f"vendored {build(a.n)} GSM8K cases into {HERE}")
