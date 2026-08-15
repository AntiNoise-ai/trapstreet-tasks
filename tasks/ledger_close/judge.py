"""Per-case judge for ledger_close.

I/O contract: reads TRAPTASK_MANIFEST (trap-cli).

Scoring is binary and fully deterministic (no LLM judge). The answer is a
machine-generated number or record id, never a sentence, so there is no
phrasing to argue about -- either the value came back or it did not.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

VOUCHER_RE = re.compile(r"\bAR-2026-\d{4}(?:-A)?\b")
# Money as it may plausibly be written back: 12345.67, 12,345.67, $12,345.67
MONEY_RE = re.compile(r"(?<![\w.])\$?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?![\w.])|(?<![\w.])\$?\d+(?:\.\d{1,2})?(?![\w.])")
STRIP = " \t\r\n\"'`*.,:;!?()[]{}"


SENTINEL_RE = re.compile(r"^\s*ANSWER:\s*(.+?)\s*$", re.MULTILINE)


def last_value_line(stdout: str) -> str:
    """The value on the `ANSWER:` line -- the last one if several are printed.

    Position-based extraction ("the last non-empty line is the answer") was
    tried first and produced a false negative on the very first calibration
    run: a harness printed the correct figure at the TOP of its reply, wrote a
    summary underneath, and scored 0.0 while stating -- accurately, from its
    own point of view -- that it had complied. Three other tasks in this repo
    have lost correct answers the same way. A sentinel costs the solution one
    line and removes the whole class.
    """
    hits = SENTINEL_RE.findall(stdout)
    if hits:
        return hits[-1].strip(STRIP), "sentinel"
    lines = [ln.strip(STRIP) for ln in stdout.splitlines()]
    lines = [ln for ln in lines if ln]
    return (lines[-1] if lines else ""), "fallback"


def normalise_money(text: str) -> str | None:
    """'$12,345.67' -> '12345.67'. None if it is not a money-shaped token."""
    t = text.replace("$", "").replace(",", "").replace("USD", "").strip()
    try:
        return f"{float(t):.2f}"
    except ValueError:
        return None


def candidates(stdout: str, kind: str) -> set[str]:
    """Every token in the output that could plausibly be an answer of this
    kind. Used to reject shotgun answers -- printing every figure in the
    ledger must not count as remembering the one that mattered."""
    if kind == "voucher":
        return set(VOUCHER_RE.findall(stdout))
    out = set()
    for tok in MONEY_RE.findall(stdout):
        n = normalise_money(tok)
        if n is not None:
            out.add(n)
    return out


def score_case(stdout: str, expected: dict) -> dict[str, Any]:
    """1.0 iff the remembered value came back.

    Primary path: the last non-empty line IS the value (what the case
    README asks for).

    Fallback: the value appears somewhere in the output AND it is the only
    candidate of its kind present. This forgives an explanatory preamble --
    a real behaviour of agent solutions -- without letting a solution list
    many values and collect credit for containing the right one.
    """
    answer = expected["answer"]
    kind = expected.get("answer_kind", "money")
    category = expected.get("question_kind")

    tail, extraction = last_value_line(stdout)
    tail_norm = tail if kind == "voucher" else (normalise_money(tail) or tail)
    if tail.upper() == "UNKNOWN":
        return {
            "score": 0.0,
            "reason": "solution reported UNKNOWN",
            "category": category,
            "reported": "UNKNOWN",
        }

    if tail_norm.lower() == answer.lower():
        return {"score": 1.0, "reason": "exact match on final line", "category": category,
                "reported": tail, "extraction": extraction}

    found = candidates(stdout, kind)
    if answer in found and len(found) == 1:
        return {
            "score": 1.0,
            "reason": "value present and unambiguous (preamble tolerated)",
            "category": category,
            "reported": answer,
            "extraction": extraction,
        }

    if answer in found:
        return {
            "score": 0.0,
            "reason": f"value present but {len(found)} candidates in output -- shotgun not credited",
            "category": category,
            "reported": tail,
            "n_candidates": len(found),
        }

    return {
        "score": 0.0,
        "reason": "value absent from output",
        "category": category,
        "reported": tail,
        "extraction": extraction,
        "n_candidates": len(found),
    }


def main() -> None:
    m = json.loads(os.environ["TRAPTASK_MANIFEST"])
    stdout = Path(m["run"]["stdout"]).read_text(errors="replace")
    exit_code = json.loads(Path(m["run"]["meta"]).read_text())["exit_code"]
    expected = json.loads((Path(m["expected_dir"]) / "answer.json").read_text())

    if exit_code != 0:
        result = {"score": 0.0, "reason": f"solution exited {exit_code}",
                  "category": expected.get("question_kind")}
    elif not stdout.strip():
        result = {"score": 0.0, "reason": "empty stdout",
                  "category": expected.get("question_kind")}
    else:
        result = score_case(stdout, expected)

    result["id"] = expected["id"]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
