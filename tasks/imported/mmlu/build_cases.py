"""Importer for an MMLU slice into the trapstreet task format.

Source : cais/mmlu (MMLU), MIT License — Hendrycks et al., "Measuring Massive
         Multitask Language Understanding". Original repo: hendrycks/test (MIT).
Data   : fetched at build time via the Hugging Face datasets-server rows API.

We vendor a fixed N-item slice sampled at even offsets across the test split so
the subjects are diverse, as deterministic multiple-choice cases graded by a
leading_word matcher on the answer letter (A-D). See ATTRIBUTION.md.

Run:  python3 build_cases.py            # fetch + vendor (needs network)
      python3 build_cases.py --n 25
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = ("https://datasets-server.huggingface.co/rows"
       "?dataset=cais/mmlu&config=all&split=test&offset={off}&length=1")
TOTAL = 14042  # MMLU 'all' test split size
LETTERS = ["A", "B", "C", "D"]


def fetch_row(offset: int) -> dict:
    url = API.format(off=offset)
    req = urllib.request.Request(url, headers={"User-Agent": "trapstreet-import"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["rows"][0]["row"]


def build(n: int) -> int:
    step = max(1, TOTAL // n)
    lines = ["dirs:", "  inputs: inputs/", "  expected: expected/", "", "cases:"]
    gold_cases = []
    count = 0
    for i in range(n):
        row = fetch_row(i * step)
        choices = row["choices"]
        if len(choices) != 4:
            continue
        ans_idx = int(row["answer"])
        letter = LETTERS[ans_idx]
        count += 1
        cid = f"mmlu_{count:03d}_{row['subject']}"
        (HERE / "inputs" / cid).mkdir(parents=True, exist_ok=True)
        (HERE / "expected" / cid).mkdir(parents=True, exist_ok=True)
        opts = "\n".join(f"{LETTERS[j]}) {c}" for j, c in enumerate(choices))
        q = (f"{row['question'].strip()}\n\n{opts}\n\n"
             "Respond with ONLY the letter (A, B, C, or D) of the correct answer.\n")
        (HERE / "inputs" / cid / "question.txt").write_text(q)
        (HERE / "expected" / cid / "answer.json").write_text(json.dumps({
            "id": cid, "answer": letter, "type": "multiple_choice",
            "matchers": [{"kind": "leading_word", "value": letter.lower()}],
            "category": row["subject"], "difficulty": "medium",
            "_source": "MMLU (cais/mmlu, MIT)",
        }, indent=2) + "\n")
        desc = row["question"].strip().replace('"', "'").replace("\n", " ")[:80]
        lines += [f"- id: {cid}", f'  description: "[{row["subject"]}] {desc}..."', "  tags:",
                  f"  - {row['subject']}", "  - mmlu", ""]
        gold_cases.append({"id": cid, "answer": letter, "category": row["subject"]})
    lines += ["judge:", "  cmd: python3 judge.py", "", "grader:", "  cmd: python3 grader.py", ""]
    (HERE / "traptask.yaml").write_text("\n".join(lines))
    (HERE / "gold.cases.json").write_text(json.dumps(gold_cases, indent=2) + "\n")
    return count


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    a = ap.parse_args()
    print(f"vendored {build(a.n)} MMLU cases into {HERE}")
