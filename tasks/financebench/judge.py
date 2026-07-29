#!/usr/bin/env python3
"""FinanceBench per-case judge — runs once per case in trap's judge protocol.

Reads:
  - the agent's captured stdout (the model's answer to this case's question)
  - the case's gold answer from expected/answer.json

Compares with 1% relative tolerance for numerics; falls back to exact / substring
string match. Adapted from the original `grade.py` in the trapstreet-eval-demo
skill (https://github.com/AntiNoise-ai/trapstreet-eval-demo).

Outputs a JSON object to stdout that trap stores as the case's `metrics`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REL_TOL = 0.01

# Numeric-magnitude suffix table — handles "1.2 billion", "$1.2B", "12K", etc.
SCALE = [
    ("trillion", 1e12), ("trillions", 1e12), ("tn", 1e12), ("t", 1e12),
    ("billion", 1e9),  ("billions", 1e9),  ("bn", 1e9),  ("b", 1e9),
    ("million", 1e6),  ("millions", 1e6),  ("mn", 1e6),  ("mm", 1e6), ("m", 1e6),
    ("thousand", 1e3), ("thousands", 1e3), ("k", 1e3),
]

NUMBER_RE = re.compile(r"\(?-?\$?\s*[\d,]+(?:\.\d+)?\)?")


def _numbers_in(text: str) -> set[float]:
    """Return every distinct number-like value that appears anywhere in `text`.

    Used to compute the set of numbers already primed by the question itself
    (e.g. the fiscal year(s) it names, or a formula constant like 365) so the
    solver's answer isn't matched against a value it merely echoed back.
    """
    out: set[float] = set()
    if not text:
        return out
    s = text.strip().lower()
    for m in NUMBER_RE.finditer(s):
        raw, sign = m.group(0), 1
        if raw.startswith("(") and raw.endswith(")"):
            raw, sign = raw[1:-1], -1
        raw = raw.replace("$", "").replace(",", "").replace(" ", "").strip()
        try:
            out.add(float(raw) * sign)
        except ValueError:
            continue
    return out


def parse_number(text: str) -> float | None:
    """Extract the first number-like token from `text`. Handles $, commas,
    accounting parentheses for negatives, % suffix, and magnitude suffixes.
    Returns None if no number found. Used for the gold side, where there's
    no ambiguity to preserve (gold strings never carry a magnitude word)."""
    if not text:
        return None
    s = text.strip().lower()
    is_pct = "%" in s or " percent" in s
    m = NUMBER_RE.search(s)
    if not m:
        return None
    raw, sign = m.group(0), 1
    if raw.startswith("(") and raw.endswith(")"):
        raw, sign = raw[1:-1], -1
    raw = raw.replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        value = float(raw) * sign
    except ValueError:
        return None
    tail = s[m.end():].lstrip()
    for unit, mult in SCALE:
        if re.match(rf"\b{unit}\b", tail):
            value *= mult
            break
    if is_pct:
        value /= 100.0
    return value


def parse_number_variants(text: str, exclude: frozenset[float] = frozenset()) -> set[float]:
    """Return the numeric interpretation(s) of the first *qualifying* token in
    `text` — the first one whose candidate values don't fall entirely in
    `exclude`.

    Normally a single value. If the token has a trailing magnitude word
    ("million", "billion", ...), returns BOTH the literal value and the value
    scaled by that word, because whether the word rescales the figure or
    merely restates a unit already baked into the gold answer (e.g. the
    question asks "in USD millions" and gold is a bare, already-in-millions
    number) isn't knowable from the token alone — a solver answering
    "$5,466 million" to such a question is restating the unit, not giving a
    raw dollar figure, and should still match a gold of "5466".

    `exclude` skips tokens that just restate a number from the question itself
    (most commonly the fiscal year, e.g. "For FY2018, ... were $5,466 million")
    — without it, the first number found would be the year, not the figure.
    """
    if not text:
        return set()
    s = text.strip().lower()
    is_pct = "%" in s or " percent" in s
    pos = 0
    while True:
        m = NUMBER_RE.search(s, pos)
        if not m:
            return set()
        raw, sign = m.group(0), 1
        if raw.startswith("(") and raw.endswith(")"):
            raw, sign = raw[1:-1], -1
        raw = raw.replace("$", "").replace(",", "").replace(" ", "").strip()
        try:
            value = float(raw) * sign
        except ValueError:
            pos = m.end()
            continue
        if is_pct:
            value /= 100.0
        if value in exclude:
            # The literal token itself is one already primed by the question
            # (a restated year, or — e.g. "3M" the company — a bare digit that
            # a magnitude suffix would otherwise misread as "3 million").
            pos = m.end()
            continue
        variants = {value}
        tail = s[m.end():].lstrip()
        for unit, mult in SCALE:
            if re.match(rf"\b{unit}\b", tail):
                variants.add(value * mult)
                break
        return variants


def numeric_close(a: float, b: float) -> bool:
    if a == b:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 1e-9
    return abs(a - b) / max(abs(a), abs(b)) <= REL_TOL


def normalize_string(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower()).strip(".!?,;:")


def score_one(pred: str, gold: str, question: str = "") -> tuple[float, str]:
    """Return (score in {0.0, 1.0}, human-readable reason)."""
    if not pred.strip():
        return 0.0, "empty prediction"

    confounds = frozenset(_numbers_in(question))
    p_variants = parse_number_variants(pred, exclude=confounds)
    g_num = parse_number(gold)
    if p_variants and g_num is not None:
        match = next((p for p in p_variants if numeric_close(p, g_num)), None)
        if match is not None:
            return 1.0, f"numeric match (pred={match:.6g} gold={g_num:.6g})"
        shown = min(p_variants, key=lambda v: abs(v - g_num))
        return 0.0, f"numeric mismatch (pred={shown:.6g} gold={g_num:.6g})"

    if normalize_string(pred) == normalize_string(gold):
        return 1.0, "string exact match"
    if len(gold) <= 40 and normalize_string(gold) in normalize_string(pred):
        return 1.0, "substring match"
    return 0.0, f"string mismatch (pred={pred[:80]!r} gold={gold[:80]!r})"


def main() -> int:
    manifest: dict[str, Any] = json.loads(os.environ["TRAPTASK_MANIFEST"])

    # Solver writes its answer to stdout; trap captures it at run.stdout.
    pred_path = Path(manifest["run"]["stdout"])
    pred = pred_path.read_text() if pred_path.exists() else ""

    gold_path = Path(manifest["expected_dir"]) / "answer.json"
    gold_obj = json.loads(gold_path.read_text())
    gold = gold_obj["gold"]

    question_path = Path(manifest["inputs_dir"]) / "question.txt"
    question = question_path.read_text() if question_path.exists() else ""

    s, reason = score_one(pred, gold, question)
    print(json.dumps({
        "score": s,
        "correct": s == 1.0,
        # Truncate at 500 chars so we don't store entire LLM monologues.
        "agent_answer": pred.strip()[:500],
        "expected_answer": gold,
        "reason": reason,
        "company": gold_obj.get("company"),
        "doc": gold_obj.get("doc"),
        "financebench_id": gold_obj.get("financebench_id"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
