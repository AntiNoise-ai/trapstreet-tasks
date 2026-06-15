"""Importer for a balanced CUAD slice into the trapstreet task format.

Source : CUAD (Contract Understanding Atticus Dataset), The Atticus Project.
         License: CC BY 4.0. Hendrycks et al., "CUAD: An Expert-Annotated NLP
         Dataset for Legal Contract Review", NeurIPS 2021 (arXiv:2103.06268).
Data   : the official SQuAD-format `test.json`, extracted from the CUAD GitHub
         release `data.zip`, fetched at build time and cached under .cache/.

We vendor a fixed, paired slice of the *test* split (never train — train was used
to fine-tune the models being evaluated):

  PRESENT cases  — the contract genuinely contains the clause → gold span(s).
                   Graded by `span_f1`. Catches the LAZINESS failure (a model that
                   confidently says "no clause found" when one is plainly there).

  ABSENT cases   — the contract has no such clause → empty gold.
                   Graded by `no_clause`. Catches the HALLUCINATION failure (a model
                   that fabricates a span). This is the inverse signal and the one
                   that stress-tests "no dead links / no hallucinated answers" claims.

Categories are drawn in PRIORITY order (the subtle, frequently-misread clauses
make the best demos), one present + one absent example each where available.

Run:  python3 build_cases.py                      # default: 20 present + 12 absent
      python3 build_cases.py --present 25 --absent 16
"""
from __future__ import annotations

import argparse
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
DATA_URL = "https://raw.githubusercontent.com/TheAtticusProject/cuad/main/data.zip"
SOURCE_TAG = "CUAD (theatticusproject/cuad, CC BY 4.0)"

# Subtle / frequently-misread clauses first — these are the demo-worthy ones.
PRIORITY = [
    "Anti-Assignment", "Change Of Control", "Most Favored Nation", "Cap On Liability",
    "Uncapped Liability", "Non-Compete", "Exclusivity", "Termination For Convenience",
    "Rofr/Rofo/Rofn", "Revenue/Profit Sharing", "Minimum Commitment", "Audit Rights",
    "Ip Ownership Assignment", "Joint Ip Ownership", "License Grant", "Liquidated Damages",
    "Effective Date", "Agreement Date", "Expiration Date", "Renewal Term", "Governing Law",
    "Insurance", "Warranty Duration", "Covenant Not To Sue", "Third Party Beneficiary",
    "Document Name",
]

CAT_RE = re.compile(r'related to "([^"]+)"')


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def ensure_test_json() -> Path:
    CACHE.mkdir(exist_ok=True)
    test_json = CACHE / "test.json"
    if test_json.exists():
        return test_json
    zip_path = CACHE / "data.zip"
    if not zip_path.exists():
        print(f"downloading {DATA_URL} ...")
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "trapstreet-import"})
        with urllib.request.urlopen(req, timeout=300) as r:
            zip_path.write_bytes(r.read())
    with zipfile.ZipFile(zip_path) as z:
        z.extract("test.json", CACHE)
    return test_json


def category_of(question: str) -> str | None:
    m = CAT_RE.search(question)
    return m.group(1) if m else None


def load_buckets(test_json: Path):
    """cat -> {'present': [(title, ctx, qa)], 'absent': [...]} in file order."""
    data = json.loads(test_json.read_text())["data"]
    buckets: dict[str, dict[str, list]] = {}
    for entry in data:
        title = entry["title"]
        for para in entry["paragraphs"]:
            ctx = para["context"]
            for qa in para["qas"]:
                cat = category_of(qa["question"])
                if not cat:
                    continue
                b = buckets.setdefault(cat, {"present": [], "absent": []})
                key = "present" if qa["answers"] else "absent"
                b[key].append((title, ctx, qa))
    return buckets


def ordered_categories(buckets: dict) -> list[str]:
    seen = [c for c in PRIORITY if c in buckets]
    rest = sorted(c for c in buckets if c not in seen)
    return seen + rest


QUESTION_TEMPLATE = (
    "{context}\n\n"
    "================================================================\n"
    "QUESTION: {question}\n\n"
    "Instructions:\n"
    "- If this contract contains such a clause, quote the EXACT text of the "
    "relevant span(s), verbatim from the contract above.\n"
    "- If this contract contains NO such clause, respond with exactly: NO CLAUSE FOUND\n"
    "- Do not explain your reasoning. Output only the quoted span(s) or "
    '"NO CLAUSE FOUND".\n'
)


def write_case(kind: str, idx: int, cat: str, title: str, ctx: str, qa: dict) -> dict:
    present = bool(qa["answers"])
    cid = f"cuad_{kind}{idx:02d}_{slug(cat)}"
    (HERE / "inputs" / cid).mkdir(parents=True, exist_ok=True)
    (HERE / "expected" / cid).mkdir(parents=True, exist_ok=True)

    (HERE / "inputs" / cid / "question.txt").write_text(
        QUESTION_TEMPLATE.format(context=ctx, question=qa["question"])
    )

    gold_spans = [a["text"] for a in qa["answers"]]
    if present:
        matchers = [{"kind": "span_f1", "gold_spans": gold_spans, "threshold": 0.5}]
    else:
        matchers = [{"kind": "no_clause"}]

    (HERE / "expected" / cid / "answer.json").write_text(json.dumps({
        "id": cid,
        "type": "span_extraction",
        "category": cat,
        "gold_present": present,
        "gold_spans": gold_spans,
        "matchers": matchers,
        "difficulty": "hard" if present else "medium",
        "_contract": title,
        "_source": SOURCE_TAG,
    }, indent=2) + "\n")

    desc = (f"[{cat}] {'present' if present else 'absent'} — "
            f"{title.split('_')[0][:40]}")
    return {"id": cid, "category": cat, "gold_present": present,
            "gold_spans": gold_spans, "description": desc}


def build(n_present: int, n_absent: int) -> tuple[int, int]:
    buckets = load_buckets(ensure_test_json())
    cats = ordered_categories(buckets)

    cases: list[dict] = []
    p = 0
    for cat in cats:
        if p >= n_present:
            break
        present = buckets[cat]["present"]
        if not present:
            continue
        p += 1
        cases.append(write_case("p", p, cat, *present[0]))

    a = 0
    for cat in cats:
        if a >= n_absent:
            break
        absent = buckets[cat]["absent"]
        if not absent:
            continue
        a += 1
        cases.append(write_case("a", a, cat, *absent[0]))

    # traptask.yaml
    lines = ["dirs:", "  inputs: inputs/", "  expected: expected/", "", "cases:"]
    for c in cases:
        tag = "cuad_present" if c["gold_present"] else "cuad_absent"
        lines += [f"- id: {c['id']}",
                  f'  description: "{c["description"]}"',
                  "  tags:",
                  f"  - {slug(c['category'])}",
                  "  - cuad",
                  f"  - {tag}",
                  ""]
    lines += ["judge:", "  cmd: python3 judge.py", "", "grader:", "  cmd: python3 grader.py", ""]
    (HERE / "traptask.yaml").write_text("\n".join(lines))

    (HERE / "gold.cases.json").write_text(json.dumps(
        [{"id": c["id"], "category": c["category"], "gold_present": c["gold_present"],
          "gold_spans": c["gold_spans"]} for c in cases], indent=2) + "\n")

    return p, a


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--present", type=int, default=20)
    ap.add_argument("--absent", type=int, default=12)
    a = ap.parse_args()
    np_, na_ = build(a.present, a.absent)
    print(f"vendored {np_} present + {na_} absent CUAD cases into {HERE}")
