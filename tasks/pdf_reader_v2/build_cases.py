#!/usr/bin/env python3
"""Validate gold.cases.json, then generate inputs/ and expected/.

inputs/ and expected/ are GENERATED. Never hand-edit them — edit
gold.cases.json and re-run this script.

The validation that matters here is `assert_no_answer_leak()`. This task
exists as a fork of tasks/pdf_reader specifically because three of its cases
had the gold answer sitting in the question text ("e.g. 'Housing Act 1988'"
when the answer was Housing Act 1988), so a model could pass them without
opening the PDF. A prose review missed that for four task revisions. Checking
it mechanically, against the matchers the judge actually scores on, is the
only version of this review that stays true as cases get edited.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
GOLD = HERE / "gold.cases.json"

VALID_MATCHERS = {
    "numeric", "leading_numeric", "currency_amount", "regex_required", "leading_word",
    "keywords_all", "keywords_any", "keywords_any_word", "no_hedge", "min_words",
}

# Matchers that can't be satisfied by echoing the prompt. `leading_word` is a
# yes/no commitment (a coin flip, not a leak); the other two are output-shape
# constraints. Everything else keys on content and IS leakable.
NON_LEAKABLE = {"leading_word", "no_hedge", "min_words"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _numeric_forms(v: float) -> list[str]:
    """Every plausible way `v` could be written in prose."""
    out = set()
    for n in (v, int(v)) if float(v).is_integer() else (v,):
        s = f"{n}"
        out.add(s)
        if float(v).is_integer():
            out.add(f"{int(v):,}")          # 77,400
            out.add(f"{int(v):,}".replace(",", " "))
        else:
            out.add(f"{v:,.2f}")            # 6,421.47
    return [x for x in out if len(x) >= 2]


def _matcher_satisfied_by(m: dict, q: str) -> str | None:
    """If matcher `m` would pass on the question text alone, say how."""
    kind = m["kind"]

    if kind in ("numeric", "leading_numeric", "currency_amount"):
        for form in _numeric_forms(m["value"]):
            if re.search(rf"(?<![\d.]){re.escape(form)}(?![\d.])", q):
                return f"{kind}: value {m['value']} appears in the question as {form!r}"

    elif kind == "regex_required":
        if re.search(m["pattern"], q, re.I):
            return f"regex_required: /{m['pattern']}/ matches the question text"

    elif kind == "keywords_any":
        hit = [v for v in m["values"] if _norm(v) in q]
        if hit:
            return f"keywords_any: question contains {hit!r}"

    elif kind == "keywords_any_word":
        hit = [v for v in m["values"] if re.search(rf"\b{re.escape(_norm(v))}\b", q)]
        if hit:
            return f"keywords_any_word: question contains {hit!r}"

    elif kind == "keywords_all":
        if all(_norm(v) in q for v in m["values"]):
            return f"keywords_all: question contains all of {m['values']!r}"

    return None


def assert_no_answer_leak(case: dict) -> tuple[list[str], list[str]]:
    """Return (fatal, partial) leak descriptions.

    The judge scores a case 1.0 only when EVERY matcher passes, so the
    question is a true leak only when every *content* matcher is already
    satisfied by the question text — at that point echoing the prompt scores
    the case and the PDF is decorative. That's `fatal`.

    A subset being satisfiable is `partial`: worth surfacing (it narrows the
    search for a guesser) but not disqualifying, since at least one matcher
    still forces the model to produce something the prompt didn't supply.
    """
    q = _norm(case["question"])
    content = [m for m in case.get("matchers", []) if m["kind"] not in NON_LEAKABLE]
    if not content:
        return [], []

    hits = [(m, why) for m in content if (why := _matcher_satisfied_by(m, q))]
    reasons = [why for _, why in hits]
    if len(hits) == len(content):
        return reasons, []
    return [], reasons


def validate_case(case: dict, seen: set[str]) -> None:
    for field in ("id", "label", "question", "answer", "type", "matchers", "category", "difficulty"):
        if field not in case:
            raise ValueError(f"{case.get('id', '<no id>')}: missing required field {field!r}")

    cid = case["id"]
    if cid in seen:
        raise ValueError(f"duplicate case id {cid!r}")
    seen.add(cid)

    # Opaque IDs only. The solution can read its own inputs_dir path, so a
    # descriptive id like `pets_allowed` or `governing_act` hands over the
    # topic — and sometimes the answer — for free. Real labels live in
    # expected/, which the solution never sees.
    if not re.fullmatch(r"case_\d{2}", cid):
        raise ValueError(
            f"{cid!r}: case ids must be opaque (case_NN). The id is visible to the "
            f"solution via TRAP_MANIFEST['inputs_dir']; use `label` for the real name."
        )

    if not case["matchers"]:
        raise ValueError(f"{cid}: at least one matcher required")
    for m in case["matchers"]:
        if m.get("kind") not in VALID_MATCHERS:
            raise ValueError(f"{cid}: unknown matcher kind {m.get('kind')!r}")

    if all(m["kind"] in NON_LEAKABLE for m in case["matchers"]) and case["type"] != "boolean":
        raise ValueError(f"{cid}: non-boolean case scored only by shape matchers — nothing checks the content")

    fatal, partial = assert_no_answer_leak(case)
    acked = case.get("_leak_ack")
    if fatal and not acked:
        detail = "\n      ".join(fatal)
        raise ValueError(
            f"{cid} ({case['label']}): EVERY content matcher is satisfied by the question "
            f"text — echoing the prompt scores this case without opening the PDF:\n"
            f"      {detail}\n"
            f"      Fix the question, tighten the matchers, or set \"_leak_ack\" explaining why "
            f"the overlap is unavoidable."
        )
    if fatal and acked:
        print(f"  ! {cid} ({case['label']}): full leak ACKNOWLEDGED — {acked}")
    elif partial:
        for why in partial:
            print(f"  · {cid} ({case['label']}): partial overlap — {why}")


def build() -> None:
    data = json.loads(GOLD.read_text())
    doc = HERE / data["document"]
    if not doc.exists():
        raise SystemExit(
            f"missing source document {doc}\n"
            f"Copy it in from ../pdf_reader/{data['document']} (see README)."
        )

    for d in ("inputs", "expected"):
        shutil.rmtree(HERE / d, ignore_errors=True)

    seen: set[str] = set()
    for case in data["cases"]:
        validate_case(case, seen)

        cid = case["id"]
        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)
        (in_dir / "question.txt").write_text(case["question"].strip() + "\n")
        shutil.copyfile(doc, in_dir / "document.pdf")

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "answer.json").write_text(json.dumps({
            "id": cid,
            "label": case["label"],
            "answer": case["answer"],
            "type": case["type"],
            "matchers": case["matchers"],
            "category": case["category"],
            "difficulty": case["difficulty"],
        }, indent=2) + "\n")

    print(f"built {len(data['cases'])} cases -> inputs/, expected/")


if __name__ == "__main__":
    try:
        build()
    except ValueError as e:
        print(f"gold.cases.json is invalid:\n  {e}", file=sys.stderr)
        raise SystemExit(1)
