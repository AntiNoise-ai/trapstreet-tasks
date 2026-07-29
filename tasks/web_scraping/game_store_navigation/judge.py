"""Per-case judge for game_store_navigation.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli). See
references/traptask-contract.md for the exact manifest shape.

Number parsing here is adapted from the financebench task in this repo,
including three fixes made there after they were found to misgrade
realistic answers (see tasks/financebench/README.md "First qualifying
number"):
  1. exclude any number that already appears in the question (a restated
     fiscal year there; here, e.g. "Tier 3" in a question about tiers) --
     otherwise the first qualifying number in the answer can be one the
     solver was just echoing back, not the actual figure.
  2. accept either the literal or magnitude-scaled reading of a number with
     a trailing unit word.
  3. only skip a token if its literal (unscaled) value is a confound --
     not if any scaled variant of it happens not to be, which is what
     let a bare "3" collide with a scale suffix in financebench's "3M"
     case; the equivalent risk here is smaller (no ticker-style names) but
     the same guard costs nothing to keep.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

REL_TOL = 0.01

SCALE = [
    ("trillion", 1e12), ("trillions", 1e12), ("tn", 1e12), ("t", 1e12),
    ("billion", 1e9), ("billions", 1e9), ("bn", 1e9), ("b", 1e9),
    ("million", 1e6), ("millions", 1e6), ("mn", 1e6), ("mm", 1e6), ("m", 1e6),
    ("thousand", 1e3), ("thousands", 1e3), ("k", 1e3),
]

NUMBER_RE = re.compile(r"\(?-?[\$€]?\s*[\d,]+(?:\.\d+)?\)?")


def _numbers_in(text: str) -> set[float]:
    """Every distinct number-like value in `text` -- used to compute which
    numbers the question itself already primed (e.g. "Tier 3", "90%")."""
    out: set[float] = set()
    if not text:
        return out
    s = text.strip().lower()
    for m in NUMBER_RE.finditer(s):
        raw, sign = m.group(0), 1
        if raw.startswith("(") and raw.endswith(")"):
            raw, sign = raw[1:-1], -1
        raw = raw.replace("$", "").replace("€", "").replace(",", "").replace(" ", "").strip()
        try:
            out.add(float(raw) * sign)
        except ValueError:
            continue
    return out


def parse_number(text: str) -> float | None:
    """Single-value parse for the gold side -- no scale-vs-restated-unit
    ambiguity to preserve there, gold strings never carry a magnitude word."""
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
    raw = raw.replace("$", "").replace("€", "").replace(",", "").replace(" ", "").strip()
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
    """Numeric interpretation(s) of the first qualifying token in `text`.
    See module docstring for why both a raw and magnitude-scaled candidate
    are returned, and why a token is skipped entirely when its *literal*
    value is a confound."""
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
        raw = raw.replace("$", "").replace("€", "").replace(",", "").replace(" ", "").strip()
        try:
            value = float(raw) * sign
        except ValueError:
            pos = m.end()
            continue
        if is_pct:
            value /= 100.0
        if value in exclude:
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


def score_case(stdout: str, expected: dict, question: str = "") -> dict[str, Any]:
    # expected.get(...) rather than expected[...]: a malformed/incomplete
    # expected dict (or malformed stdout) must degrade to a clean miss, not
    # crash the judge -- see references/scoring-design.md, "Malformed-output
    # robustness".
    gold = expected.get("gold") if isinstance(expected, dict) else None
    if gold is None:
        return {"score": 0.0, "reason": "no gold value to compare against",
                "mechanism": expected.get("mechanism") if isinstance(expected, dict) else None,
                "expected": gold}

    confounds = frozenset(_numbers_in(question))
    p_variants = parse_number_variants(stdout, exclude=confounds)
    g_num = parse_number(gold)

    if not p_variants or g_num is None:
        return {
            "score": 0.0,
            "reason": "no numeric answer found in solution output",
            "mechanism": expected.get("mechanism"),
            "expected": gold,
        }

    match = next((p for p in p_variants if numeric_close(p, g_num)), None)
    if match is not None:
        return {
            "score": 1.0,
            "reason": f"numeric match (pred={match:.6g} gold={g_num:.6g})",
            "mechanism": expected.get("mechanism"),
            "expected": gold,
        }

    shown = min(p_variants, key=lambda v: abs(v - g_num))
    return {
        "score": 0.0,
        "reason": f"numeric mismatch (pred={shown:.6g} gold={g_num:.6g})",
        "mechanism": expected.get("mechanism"),
        "expected": gold,
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])

    stdout = Path(m["run"]["stdout"]).read_text()
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())
    # Deliberately NOT reading inputs_dir/question.txt here: that file also
    # carries shared boilerplate instructions (e.g. example port numbers,
    # an example answer format) which must not leak into the confound set.
    # expected["question"] is the judge-only, boilerplate-free original text.
    question = expected.get("question", "")

    base = {"id": expected.get("id")}

    if exit_code != 0:
        print(json.dumps({**base, "score": 0.0, "reason": f"solution exited {exit_code}",
                           "agent_output": stdout.strip()[:500]}))
        return

    if not stdout.strip():
        print(json.dumps({**base, "score": 0.0, "reason": "agent produced no output",
                           "agent_output": ""}))
        return

    metrics = score_case(stdout, expected, question)
    metrics.update(base)
    metrics["agent_output"] = stdout.strip()[:500]
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
